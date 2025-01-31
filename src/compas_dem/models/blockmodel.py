from typing import Generator

from compas.datastructures import Mesh
from compas.geometry import Box
from compas.geometry import Frame
from compas.geometry import Polyhedron
from compas.geometry import Transformation
from compas_model.models import Model

from compas_dem.elements.block import BlockElement
from compas_dem.interactions import FrictionContact
from compas_dem.templates import BarrelVaultTemplate
from compas_dem.templates import Template


class BlockModel(Model):
    """Variation of COMPAS Model specifically designed for working with Discrete Element Models in the context of masonry construction."""

    def __init__(self, name=None):
        super().__init__(name)

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
            element = BlockElement.from_box(box)
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
            element = BlockElement.from_polyhedron(polyhedron)
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
            origin = mesh.face_polygon(5).frame.point
            frame = Frame(origin, mesh.vertex_point(0) - mesh.vertex_point(2), mesh.vertex_point(4) - mesh.vertex_point(2))
            xform = Transformation.from_frame_to_frame(frame, Frame.worldXY())
            mesh_xy: Mesh = mesh.transformed(xform)
            block: BlockElement = BlockElement.from_mesh(mesh_xy)
            block.is_support = mesh_xy.attributes["is_support"]
            block.transformation = xform.inverted()
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
        block = BlockElement.from_mesh(mesh)
        block.is_support = False
        self.add_element(block)
        return block.graphnode

    def add_support_from_mesh(self, mesh: Mesh) -> int:
        block = BlockElement.from_mesh(mesh)
        block.is_support = True
        self.add_element(block)
        return block.graphnode

    # =============================================================================
    # Collisions
    # =============================================================================

    def collisions(self) -> Generator:
        """"""
        raise NotImplementedError

    def compute_collisions(self):
        """"""
        raise NotImplementedError

    # =============================================================================
    # Contacts
    # =============================================================================

    def contacts(self) -> Generator[FrictionContact, None, None]:
        """Iterate over the contact interactions of this model.

        Yields
        ------
        :class:`Contact`

        """
        for edge in self.graph.edges():
            contacts = self.graph.edge_attribute(edge, name="contacts")
            if contacts:
                for contact in contacts:
                    yield contact

    def compute_contacts(self, tolerance=1e-6, minimum_area=1e-2) -> None:
        """Compute the contacts between the block elements of this model.

        Parameters
        ----------
        tolerance : float, optional
            The distance tolerance.
        minimum_area : float, optional
            The minimum contact size.

        Returns
        -------
        None

        """
        element: BlockElement

        for element in self.elements():
            u = element.graphnode
            nnbrs = self.bvh.nearest_neighbors(element)
            for nbr in nnbrs:
                v = nbr.graphnode
                if not self.graph.has_edge((u, v), directed=False):
                    contacts = element.contacts(nbr, tolerance=tolerance, minimum_area=minimum_area)
                    # this is a hack
                    contacts = [FrictionContact(size=contact.size, points=contact.points, frame=contact.frame) for contact in contacts]
                    if contacts:
                        self.graph.add_edge(u, v, contacts=contacts)

    # =============================================================================
    # Blocks & Supports
    # =============================================================================

    def supports(self) -> Generator[BlockElement, None, None]:
        """Iterate over the support blocks of this model.

        Yields
        ------
        :class:`BlockElement`

        """
        element: BlockElement
        for element in self.elements():
            if element.is_support:
                yield element

    def blocks(self) -> Generator[BlockElement, None, None]:
        """Iterate over the regular blocks of this model.

        Yields
        ------
        :class:`BlockElement`

        """
        element: BlockElement
        for element in self.elements():
            if not element.is_support:
                yield element
