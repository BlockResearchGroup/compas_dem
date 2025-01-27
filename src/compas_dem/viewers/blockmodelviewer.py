from compas.colors import Color
from compas.datastructures import Mesh
from compas.geometry import Line
from compas_viewer import Viewer
from compas_viewer.components.lineedit import LineEdit
from compas_viewer.scene import GroupObject

from compas_dem.elements import BlockElement
from compas_dem.elements import BlockMesh
from compas_dem.models import BlockModel


def scale_compression(widget, value):
    viewer = BlockModelViewer()
    viewer.scale_compression = value
    if viewer.compressionforces:
        for obj, line in zip(viewer.compressionforces.descendants, viewer._compressionforces):
            point = line.midpoint
            vector = line.vector * 0.5 * value
            obj.geometry.start = point - vector
            obj.geometry.end = point + vector
            obj.init()  # it is annoying that this is necessary
    viewer.renderer.update()


def scale_resultant(widget, value):
    viewer = BlockModelViewer()
    viewer.scale_resultant = value
    if viewer.resultantforces:
        for obj, line in zip(viewer.resultantforces.descendants, viewer._resultants):
            point = line.midpoint
            vector = line.vector * 0.5 * value
            obj.geometry.start = point - vector
            obj.geometry.end = point + vector
            obj.init()  # it is annoying that this is necessary
    viewer.renderer.update()


class BlockModelViewer(Viewer):
    def __init__(self, blockmodel, **kwargs):
        super().__init__(**kwargs)

        self.model: BlockModel = blockmodel

        self._compressionforces: list[Line] = None
        self._resultants: list[Line] = None

        self.supports: GroupObject = None
        self.blocks: GroupObject = None
        self.interfaces: GroupObject = None
        self.compressionforces: GroupObject = None
        self.tensionforces: GroupObject = None
        self.frictionforces: GroupObject = None
        self.resultantforces: GroupObject = None

        self.scale_compression = 1.0
        self.scale_tension = 1.0
        self.scale_friction = 1.0
        self.scale_resultant = 1.0

        self.color_block: Color = Color(0.9, 0.9, 0.9)
        self.color_support: Color = Color.red()
        self.color_interface: Color = Color.cyan()

        self.show_blockfaces: bool = True
        self.show_interfaces: bool = False
        self.show_contactforces: bool = False

        self.ui.sidedock.show = True

        self.ui.sidedock.add(LineEdit(str(self.scale_compression), "Scale Compression", action=scale_compression))
        self.ui.sidedock.add(LineEdit(str(self.scale_resultant), "Scale Resultants", action=scale_resultant))

    # =============================================================================
    # Show overwrite
    # =============================================================================

    def show(self):
        self.init_blockmodel()
        super().show()

    # =============================================================================
    # Model init
    # =============================================================================

    def init_blockmodel(self):
        self.init_blocks()
        self.init_interfaces()
        self.init_forces()

    # =============================================================================
    # Blocks init
    # =============================================================================

    def init_blocks(self):
        supports: list[BlockMesh] = []
        blocks: list[BlockMesh] = []

        for element in self.model.elements():
            element: BlockElement
            if element.is_support:
                supports.append((element.modelgeometry, {"name": f"Support_{len(supports)}"}))
            else:
                blocks.append((element.modelgeometry, {"name": f"Block_{len(blocks)}"}))

        self.supports = self.scene.add(
            supports,
            name="Supports",
            show_points=False,
            show_faces=True,
            facecolor=self.color_support,
            linecolor=self.color_support.contrast,
        )
        self.blocks = self.scene.add(
            blocks,
            name="Blocks",
            show_points=False,
            show_faces=True,
            facecolor=self.color_block,
            linecolor=self.color_block.contrast,
        )

    # =============================================================================
    # Interfaces init
    # =============================================================================

    def init_interfaces(self):
        interfaces: list[Mesh] = []

        for contact in self.model.contacts():
            interfaces.append(contact.polygon.to_mesh())

        self.interfaces = self.scene.add(
            interfaces,
            name="Interfaces",
            show_points=False,
            facecolor=self.color_interface,
            linecolor=self.color_interface.contrast,
        )

    # =============================================================================
    # Forces init
    # =============================================================================

    def init_forces(self):
        compressionforces: list[Line] = []
        tensionforces: list[Line] = []
        frictionforces: list[Line] = []
        resultantforces: list[Line] = []

        for contact in self.model.contacts():
            compressionforces += contact.compressionforces
            tensionforces += contact.tensionforces
            frictionforces += contact.frictionforces
            resultantforces += contact.resultantforce

        # keep a copy of the original forces
        self._compressionforces = [line.copy() for line in compressionforces]
        self._resultants = [line.copy() for line in resultantforces]

        # apply scale if relevant

        if self.scale_compression != 1.0:
            for line in compressionforces:
                if line.length:
                    line.start = line.midpoint - line.vector * 0.5 * self.scale_compression
                    line.end = line.midpoint + line.vector * 0.5 * self.scale_compression

        if self.scale_tension != 1.0:
            for line in tensionforces:
                if line.length:
                    line.start = line.midpoint - line.vector * 0.5 * self.scale_tension
                    line.end = line.midpoint + line.vector * 0.5 * self.scale_tension

        if self.scale_friction != 1.0:
            for line in frictionforces:
                if line.length:
                    line.start = line.midpoint - line.vector * 0.5 * self.scale_friction
                    line.end = line.midpoint + line.vector * 0.5 * self.scale_friction

        if self.scale_resultant != 1.0:
            for line in resultantforces:
                if line.length:
                    line.start = line.midpoint - line.vector * 0.5 * self.scale_resultant
                    line.end = line.midpoint + line.vector * 0.5 * self.scale_resultant

        # create groups

        self.compressionforces = self.scene.add(
            compressionforces,
            name="Compression",
            linewidth=3,
            linecolor=Color.blue(),
            show_points=False,
        )
        self.tensionforces = self.scene.add(
            tensionforces,
            name="Tension",
            linewidth=5,
            linecolor=Color.red(),
            show_points=False,
        )
        self.frictionforces = self.scene.add(
            frictionforces,
            name="Friction",
            linewidth=3,
            linecolor=Color.cyan(),
            show_points=False,
        )
        self.resultantforces = self.scene.add(
            resultantforces,
            name="Resultants",
            linewidth=5,
            linecolor=Color.green(),
            show_points=False,
        )
