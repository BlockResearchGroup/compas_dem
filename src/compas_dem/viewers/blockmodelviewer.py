import numpy as np
from compas.colors import Color
from compas.datastructures import Mesh
from compas_viewer import Viewer
from compas_viewer.components.lineedit import LineEdit
from compas_viewer.scene import BufferGeometry
from compas_viewer.scene import GroupObject

from compas_dem.elements import BlockElement
from compas_dem.elements import BlockMesh
from compas_dem.models import BlockModel


class BlockModelViewer(Viewer):
    """Viewer customised for visualising block models.

    Parameters
    ----------
    blockmodel : :class:`BlockModel`
        The block model.

    Attributes
    ----------
    model
    supports
    blocks
    interfaces
    color_block
    color_support
    color_interfaces
    show_blockfaces
    compression_data
    compression_buffer
    compression_object
    compression_scale
    compression_color
    tension_data
    tension_buffer
    tension_object
    tension_scale
    tension_color
    friction_data
    friction_buffer
    friction_object
    friction_scale
    friction_color
    resultant_data
    resultant_buffer
    resultant_object
    resultant_scale
    resultant_color

    """

    def __init__(self, blockmodel, **kwargs):
        super().__init__(**kwargs)

        self.model: BlockModel = blockmodel

        self.supports: GroupObject = None
        self.blocks: GroupObject = None
        self.interfaces: GroupObject = None

        self.color_block: Color = Color(0.9, 0.9, 0.9)
        self.color_support: Color = Color.red().lightened(75)
        self.color_interface: Color = Color.cyan().lightened(90)

        self.show_blockfaces: bool = True

        self.compression_data = None
        self.compression_buffer: BufferGeometry = None
        self.compression_object = None
        self.compression_scale = 1.0
        self.compression_color = Color.blue()

        self.tension_data = None
        self.tension_buffer: BufferGeometry = None
        self.tension_object = None
        self.tension_scale = 1.0
        self.tension_color = Color.red()

        self.friction_data = None
        self.friction_buffer: BufferGeometry = None
        self.friction_object = None
        self.friction_scale = 1.0
        self.friction_color = Color.orange()

        self.resultant_data = None
        self.resultant_buffer: BufferGeometry = None
        self.resultant_object = None
        self.resultant_scale = 1.0
        self.resultant_color = Color.green().darkened(50)

        self.ui.sidedock.show = True

        self.ui.sidedock.add(LineEdit(str(self.compression_scale), "Scale Compression", action=self.scale_compression))
        self.ui.sidedock.add(LineEdit(str(self.tension_scale), "Scale Tension", action=self.scale_tension))
        self.ui.sidedock.add(LineEdit(str(self.friction_scale), "Scale Friction", action=self.scale_friction))
        self.ui.sidedock.add(LineEdit(str(self.resultant_scale), "Scale Resultants", action=self.scale_resultant))

    # =============================================================================
    # Show overwrite
    # =============================================================================

    def show(self):
        """Customised version of the show method that initializes the block model before launching the viewer."""
        self.init_blockmodel()
        super().show()

    # =============================================================================
    # Model init
    # =============================================================================

    def init_blockmodel(self):
        """Initialise the block model components."""
        self.init_blocks()
        self.init_interfaces()
        self.init_compression()
        self.init_tension()
        self.init_friction()
        self.init_resultant()

    # =============================================================================
    # Blocks init
    # =============================================================================

    def init_blocks(self):
        """Initialise the blocks."""
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
            linewidth=2,
        )
        self.blocks = self.scene.add(
            blocks,
            name="Blocks",
            show_points=False,
            show_faces=False,
            facecolor=self.color_block,
            linecolor=self.color_block.contrast,
            linewidth=2,
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
    # Compression
    # =============================================================================

    def init_compression(self):
        compression_data = [d for contact in self.model.contacts() for d in contact.compressiondata]
        if not compression_data:
            return

        self.compression_data = np.array(compression_data)

        start = self.compression_data[:, 0:3]
        direction = self.compression_data[:, 3:6]
        value = self.compression_data[:, 6:7]

        lines = np.vstack(
            (
                np.hstack((start, start + direction * value)),
                np.hstack((start, start - direction * value)),
            ),
        )
        colors = np.array(self.compression_color.rgba * lines.shape[0] * 4)

        self.compression_buffer = BufferGeometry(lines=lines, linecolor=colors)
        self.compression_object = self.scene.add(self.compression_buffer, name="Compression", linewidth=3)

    def update_compression(self, scale):
        if not self.compression_buffer:
            return

        start = self.compression_data[:, 0:3]
        direction = self.compression_data[:, 3:6]
        value = self.compression_data[:, 6:7]

        self.compression_scale = scale

        self.compression_buffer.lines[: start.shape[0], 3:] = start + direction * value * scale
        self.compression_buffer.lines[start.shape[0] :, 3:] = start - direction * value * scale

        self.compression_object.init()

    def scale_compression(self, widget, value):
        self.update_compression(value)
        self.renderer.update()

    # =============================================================================
    # Tension
    # =============================================================================

    def init_tension(self):
        tension_data = [d for contact in self.model.contacts() for d in contact.tensiondata]
        if not tension_data:
            return

        self.tension_data = np.array(tension_data)

        start = self.tension_data[:, 0:3]
        direction = self.tension_data[:, 3:6]
        value = self.tension_data[:, 6:7]

        lines = np.vstack(
            (
                np.hstack((start, start + direction * value)),
                np.hstack((start, start - direction * value)),
            ),
        )
        colors = np.array(self.tension_color.rgba * lines.shape[0] * 4)

        self.tension_buffer = BufferGeometry(lines=lines, linecolor=colors)
        self.tension_object = self.scene.add(self.tension_buffer, name="Tension", linewidth=3)

    def update_tension(self, scale):
        if not self.tension_buffer:
            return

        start = self.tension_data[:, 0:3]
        direction = self.tension_data[:, 3:6]
        value = self.tension_data[:, 6:7]

        self.tension_scale = scale

        self.tension_buffer.lines[: start.shape[0], 3:] = start + direction * value * scale
        self.tension_buffer.lines[start.shape[0] :, 3:] = start - direction * value * scale

        self.tension_object.init()

    def scale_tension(self, widget, value):
        self.update_tension(value)
        self.renderer.update()

    # =============================================================================
    # Friction
    # =============================================================================

    def init_friction(self):
        friction_data = [d for contact in self.model.contacts() for d in contact.frictiondata]
        if not friction_data:
            return

        self.friction_data = np.array(friction_data)

        start = self.friction_data[:, 0:3]
        u_direction = self.friction_data[:, 3:6]
        v_direction = self.friction_data[:, 6:9]
        u_value = self.friction_data[:, 9:10]
        v_value = self.friction_data[:, 10:11]

        lines = np.vstack(
            (
                np.hstack((start, start + u_direction * u_value)),
                np.hstack((start, start + v_direction * v_value)),
            ),
        )
        colors = np.array(self.friction_color.rgba * lines.shape[0] * 4)

        self.friction_buffer = BufferGeometry(lines=lines, linecolor=colors)
        self.friction_object = self.scene.add(self.friction_buffer, name="Friction", linewidth=3)

    def update_friction(self, scale):
        if not self.friction_buffer:
            return

        start = self.friction_data[:, 0:3]
        u_direction = self.friction_data[:, 3:6]
        v_direction = self.friction_data[:, 6:9]
        u_value = self.friction_data[:, 9:10]
        v_value = self.friction_data[:, 10:11]

        self.friction_scale = scale

        self.friction_buffer.lines[: start.shape[0], 3:] = start + u_direction * u_value * scale
        self.friction_buffer.lines[start.shape[0] :, 3:] = start + v_direction * v_value * scale

        self.friction_object.init()

    def scale_friction(self, widget, value):
        self.update_friction(value)
        self.renderer.update()

    # =============================================================================
    # Resultant
    # =============================================================================

    def init_resultant(self):
        resultant_data = [contact.resultantdata for contact in self.model.contacts()]
        if not resultant_data:
            return
        if not all(d for d in resultant_data):
            return

        self.resultant_data = np.array(resultant_data)

        start = self.resultant_data[:, 0:3]
        direction = self.resultant_data[:, 3:6]
        value = self.resultant_data[:, 6:7]

        lines = np.vstack(
            (
                np.hstack((start, start + direction * value)),
                np.hstack((start, start - direction * value)),
            ),
        )
        colors = np.array(self.resultant_color.rgba * lines.shape[0] * 4)

        self.resultant_buffer = BufferGeometry(lines=lines, linecolor=colors)
        self.resultant_object = self.scene.add(self.resultant_buffer, name="Resultant", linewidth=5)

    def update_resultant(self, scale):
        if not self.resultant_buffer:
            return

        start = self.resultant_data[:, 0:3]
        direction = self.resultant_data[:, 3:6]
        value = self.resultant_data[:, 6:7]

        self.resultant_scale = scale

        self.resultant_buffer.lines[: start.shape[0], 3:] = start + direction * value * scale
        self.resultant_buffer.lines[start.shape[0] :, 3:] = start - direction * value * scale

        self.resultant_object.init()

    def scale_resultant(self, widget, value):
        self.update_resultant(value)
        self.renderer.update()
