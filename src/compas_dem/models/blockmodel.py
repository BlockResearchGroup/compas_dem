from typing import Generator
from typing import Iterator
from typing import Type

from compas.datastructures import Mesh
from compas.geometry import Box
from compas.geometry import Polyhedron
from compas_model.interactions import Contact
from compas_model.models import Model

from compas_dem.elements import Block
from compas_dem.interactions import FrictionContact
from compas_dem.templates import BarrelVaultTemplate
from compas_dem.templates import Template


class BlockModel(Model):
    """Variation of COMPAS Model specifically designed for working with Discrete Element Models in the context of masonry construction."""

    def __init__(self, name=None):
        super().__init__(name)

    def elements(self) -> Iterator[Block]:
        return super().elements()  # type: ignore

    def contacts(self) -> Generator[FrictionContact, None, None]:
        return super().contacts()  # type: ignore

    # =============================================================================
    # Factory methods
    # =============================================================================

    @classmethod
    def from_boxes(cls, boxes: list[Box]) -> "BlockModel":
        """Construct a model from a collection of boxes.

        Parameters
        ----------
        boxes : list[:class:`compas.geometry.Box`]
            A collection of boxes.

        Returns
        -------
        :class:`BlockModel`

        """
        model = cls()
        for box in boxes:
            element = Block.from_box(box)
            model.add_element(element)
        return model

    @classmethod
    def from_polyhedrons(cls, polyhedrons: list[Polyhedron]) -> "BlockModel":
        """Construct a model from a collection of polyhedrons.

        Parameters
        ----------
        polyhedrons : list[:class:`compas.geometry.Polyhedron`]
            A collection of polyhedrons.

        Returns
        -------
        :class:`BlockModel`

        """
        model = cls()
        for polyhedron in polyhedrons:
            element = Block.from_polyhedron(polyhedron)
            model.add_element(element)
        return model

    @classmethod
    def from_polysurfaces(cls, guids):
        """Construct a model from Rhino polysurfaces.

        Parameters
        ----------
        guids : list[str]
            A list of GUIDs identifying the poly-surfaces representing the blocks of the model.

        Returns
        -------
        :class:`BlockModel`

        """
        raise NotImplementedError

    @classmethod
    def from_rhinomeshes(cls, guids):
        """Construct a model from Rhino meshes.

        Parameters
        ----------
        guids : list[str]
            A list of GUIDs identifying the meshes representing the blocks of the model.

        Returns
        -------
        :class:`BlockModel`

        """
        raise NotImplementedError

    @classmethod
    def from_stack(cls):
        raise NotImplementedError

    @classmethod
    def from_wall(cls):
        raise NotImplementedError

    @classmethod
    def from_template(cls, template: Template) -> "BlockModel":
        """Construct a block model from a template.

        Parameters
        ----------
        template : :class:`Template`
            The model template.

        Returns
        -------
        :class:`BlockModel`

        """
        return cls.from_boxes(template.blocks())

    # @classmethod
    # def from_arch(cls):
    #     raise NotImplementedError

    @classmethod
    def from_barrelvault(cls, template: BarrelVaultTemplate):
        """"""
        model = cls()
        for mesh in template.blocks():
            # origin = mesh.face_polygon(5).frame.point
            # frame = Frame(origin, mesh.vertex_point(0) - mesh.vertex_point(2), mesh.vertex_point(4) - mesh.vertex_point(2))
            # xform = Transformation.from_frame_to_frame(frame, Frame.worldXY())
            # mesh_xy: Mesh = mesh.transformed(xform)
            block: Block = Block.from_mesh(mesh)
            # block.is_support = mesh_xy.attributes["is_support"]
            # block.transformation = xform.inverted()
            model.add_element(block)
        return model

    # @classmethod
    # def from_crossvault(cls):
    #     raise NotImplementedError

    # @classmethod
    # def from_fanvault(cls):
    #     raise NotImplementedError

    # @classmethod
    # def from_pavilionvault(cls):
    #     raise NotImplementedError

    @classmethod
    def from_meshpattern(cls):
        raise NotImplementedError

    @classmethod
    def from_nurbssurface(cls):
        raise NotImplementedError

    # =============================================================================
    # Builders
    # =============================================================================

    def add_block_from_mesh(self, mesh: Mesh) -> int:
        block = Block.from_mesh(mesh)
        block.is_support = False
        self.add_element(block)
        return block.graphnode

    def add_support_from_mesh(self, mesh: Mesh) -> int:
        block = Block.from_mesh(mesh)
        block.is_support = True
        self.add_element(block)
        return block.graphnode

    # =============================================================================
    # Blocks & Supports
    # =============================================================================

    def supports(self) -> Generator[Block, None, None]:
        """Iterate over the support blocks of this model.

        Yields
        ------
        :class:`Block`

        """
        for element in self.elements():
            if element.is_support:
                yield element

    def blocks(self) -> Generator[Block, None, None]:
        """Iterate over the regular blocks of this model.

        Yields
        ------
        :class:`Block`

        """
        for element in self.elements():
            if not element.is_support:
                yield element

    # =============================================================================
    # Contacts
    # =============================================================================

    def compute_contacts(
        self,
        tolerance=0.000001,
        minimum_area=0.01,
        contacttype: Type[Contact] = FrictionContact,
    ) -> None:
        return super().compute_contacts(tolerance, minimum_area, contacttype)
