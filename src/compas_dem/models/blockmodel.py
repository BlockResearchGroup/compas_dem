from typing import Generator
from typing import Iterator
from typing import Type

from compas.datastructures import Mesh
from compas.geometry import Box
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import Polyhedron
from compas.geometry import bestfit_frame_numpy
from compas.itertools import pairwise
from compas_cgal.meshing import project_mesh_on_mesh
from compas_cgal.meshing import trimesh_dual
from compas_cgal.meshing import trimesh_remesh
from compas_libigl.intersections import intersection_ray_mesh
from compas_libigl.mapping import map_pattern_to_mesh
from compas_model.interactions import Contact
from compas_model.models import Model

from compas_dem.elements import Block
from compas_dem.interactions import FrictionContact
from compas_dem.templates import BarrelVaultTemplate
from compas_dem.templates import Template


def project_mesh_to_target(mesh: Mesh, target: Mesh):
    V, F = target.to_vertices_and_faces()
    for vertex in mesh.vertices():
        point = mesh.vertex_point(vertex)
        normal = mesh.vertex_normal(vertex)
        x = intersection_ray_mesh((point, normal), (V, F))
        if not len(x):
            x = intersection_ray_mesh((point, normal * -1), (V, F))
        if len(x):
            d = x[0][3]
            mesh.vertex_attributes(vertex, "xyz", point + normal * d)


def pattern_inverse_height_thickness(pattern: Mesh, tmin=None, tmax=None):
    x: list[float] = pattern.vertices_attribute(name="x")  # type: ignore
    xmin = min(x)
    xmax = max(x)
    dx = xmax - xmin

    y: list[float] = pattern.vertices_attribute(name="y")  # type: ignore
    ymin = min(y)
    ymax = max(y)
    dy = ymax - ymin

    d = (dx**2 + dy**2) ** 0.5

    tmin = tmin or 3 * d / 1000
    tmax = tmax or 50 * d / 1000

    pattern.update_default_vertex_attributes(thickness=0)
    zvalues: list[float] = pattern.vertices_attribute(name="z")  # type: ignore
    zmin = min(zvalues)
    zmax = max(zvalues)

    for vertex in pattern.vertices():
        point = pattern.vertex_point(vertex)
        z = (point.z - zmin) / (zmax - zmin)
        thickness = (1 - z) * (tmax - tmin) + tmin
        pattern.vertex_attribute(vertex, name="thickness", value=thickness)


def pattern_idos(pattern: Mesh) -> Mesh:
    idos: Mesh = pattern.copy()
    for vertex in idos.vertices():
        point = pattern.vertex_point(vertex)
        normal = pattern.vertex_normal(vertex)
        thickness = pattern.vertex_attribute(vertex, name="thickness")
        idos.vertex_attributes(vertex, names="xyz", values=point - normal * (0.5 * thickness))  # type: ignore
    return idos


def pattern_face_block(pattern: Mesh, idos: Mesh, face: int) -> Mesh:
    vertices = pattern.face_vertices(face)
    normals = [pattern.vertex_normal(vertex) for vertex in vertices]
    thickness = pattern.vertices_attribute("thickness", keys=vertices)
    bottom = idos.vertices_points(vertices)
    top = [point + vector * t for point, vector, t in zip(bottom, normals, thickness)]  # type: ignore
    frame = Frame(*bestfit_frame_numpy(top))
    plane = Plane.from_frame(frame)
    flattop = []
    for a, b in zip(bottom, top):
        b = plane.intersection_with_line(Line(a, b))
        flattop.append(b)
    sides = []
    for (a, b), (aa, bb) in zip(pairwise(bottom + bottom[:1]), pairwise(flattop + flattop[:1])):
        sides.append([a, b, bb, aa])
    polygons = [bottom[::-1], flattop] + sides
    block: Mesh = Mesh.from_polygons(polygons)
    return block


def pattern_blocks(pattern: Mesh, idos: Mesh) -> dict[int, Mesh]:
    face_block: dict[int, Mesh] = {}
    face: int
    for face in pattern.faces():  # type: ignore
        face_block[face] = pattern_face_block(pattern, idos, face)
    return face_block


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
    def from_polysurfaces(cls, guids) -> "BlockModel":
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
    def from_rhinomeshes(cls, guids) -> "BlockModel":
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

    # =============================================================================
    # Templates
    # =============================================================================

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

    @classmethod
    def from_stack(cls) -> "BlockModel":
        raise NotImplementedError

    @classmethod
    def from_wall(cls) -> "BlockModel":
        raise NotImplementedError

    @classmethod
    def from_arch(cls):
        raise NotImplementedError

    @classmethod
    def from_barrelvault(cls, template: BarrelVaultTemplate) -> "BlockModel":
        """"""
        model = cls()
        for mesh in template.blocks():
            block: Block = Block.from_mesh(mesh)
            block.is_support = mesh.attributes["is_support"]
            model.add_element(block)
        return model

    @classmethod
    def from_crossvault(cls) -> "BlockModel":
        raise NotImplementedError

    @classmethod
    def from_fanvault(cls) -> "BlockModel":
        raise NotImplementedError

    @classmethod
    def from_pavilionvault(cls) -> "BlockModel":
        raise NotImplementedError

    # =============================================================================
    # Patterns
    # =============================================================================

    @classmethod
    def from_triangulation_dual(cls, mesh: Mesh, lengthfactor: float = 1.0, tmin=None, tmax=None) -> "BlockModel":
        """Construct a Block Model from the dual of an isotropically remeshed triangulation of the input mesh.

        Parameters
        ----------
        mesh : :class:`Mesh`
            The input mesh.
        lengthfactor : float, optional
            Multiplication factor to for the average length of the mesh to compute the target edge length of the remeshed triangulation.
        tmin : float, optional
            Minimum thickness of the blocks.
            If none is provided, the minimum thickness will be 3/1000 of the diagonal of the xy bounding box of the input mesh.
        tmax : float, optional
            Maximum thickness of the blocks.
            If none is provided, the maximum thickness will be 50/1000 of the diagonal of the xy bounding box of the input mesh.

        Returns
        -------
        :class:`BlockModel`

        """
        temp: Mesh = mesh.copy()
        temp.quads_to_triangles()
        M = temp.to_vertices_and_faces()

        V1, F1, V2, F2 = trimesh_dual(M, length_factor=lengthfactor, number_of_iterations=100)  # type: ignore
        dual = Mesh.from_vertices_and_faces(V2, F2)
        dual.unify_cycles()

        pattern_inverse_height_thickness(dual, tmin=tmin, tmax=tmax)
        idos = pattern_idos(dual)
        face_block: dict[int, Mesh] = pattern_blocks(dual, idos)

        face: int
        face_node: dict[int, int] = {}

        model = cls()
        for face, block in face_block.items():
            node = model.add_block_from_mesh(block)
            face_node[face] = node

        for face in dual.faces():  # type: ignore
            u = face_node[face]
            nbrs = dual.face_neighbors(face)
            for nbr in nbrs:
                v = face_node[nbr]
                model.graph.add_edge(u, v)

        return model

    @classmethod
    def from_meshpattern(cls, mesh: Mesh, patternname: str, tmin=None, tmax=None, **kwargs) -> "BlockModel":
        """Construct a Block Model from the dual of an isotropically remeshed triangulation of the input mesh.

        Parameters
        ----------
        mesh : :class:`Mesh`
            The input mesh.
        patternname : str
            The name of the tessagon pattern.
        tmin : float, optional
            Minimum thickness of the blocks.
            If none is provided, the minimum thickness will be 3/1000 of the diagonal of the xy bounding box of the input mesh.
        tmax : float, optional
            Maximum thickness of the blocks.
            If none is provided, the maximum thickness will be 50/1000 of the diagonal of the xy bounding box of the input mesh.

        Returns
        -------
        :class:`BlockModel`

        """
        average_length = sum(mesh.edge_length(edge) for edge in mesh.edges()) / mesh.number_of_edges()
        target_edge_length = 0.5 * average_length
        temp: Mesh = mesh.copy()
        temp.quads_to_triangles()
        M = temp.to_vertices_and_faces()
        V, F = trimesh_remesh(M, target_edge_length=target_edge_length, number_of_iterations=100)  # type: ignore
        trimesh = Mesh.from_vertices_and_faces(V, F)  # type: ignore
        pattern = map_pattern_to_mesh(patternname, trimesh, **kwargs)
        pattern.unify_cycles()
        project_mesh_on_mesh(pattern, trimesh)  # type: ignore
        pattern_inverse_height_thickness(pattern, tmin=tmin, tmax=tmax)
        idos = pattern_idos(pattern)
        face_block: dict[int, Mesh] = pattern_blocks(pattern, idos)

        face: int
        face_node: dict[int, int] = {}

        model = cls()
        for face, block in face_block.items():
            node = model.add_block_from_mesh(block)
            face_node[face] = node

        for face in pattern.faces():  # type: ignore
            u = face_node[face]
            nbrs = pattern.face_neighbors(face)
            for nbr in nbrs:
                v = face_node[nbr]
                model.graph.add_edge(u, v)

        return model

    @classmethod
    def from_nurbssurface(cls) -> "BlockModel":
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
