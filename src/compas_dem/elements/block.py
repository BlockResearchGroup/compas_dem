from typing import Optional

from compas.datastructures import Mesh
from compas.geometry import Box
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Polyhedron
from compas.geometry import Polyline
from compas.geometry import Transformation
from compas.geometry import boolean_difference_mesh_mesh
from compas.geometry import boolean_intersection_mesh_mesh
from compas.geometry import boolean_union_mesh_mesh
from compas.geometry import convex_hull_numpy
from compas.geometry import oriented_bounding_box_numpy

# from compas.geometry import trimesh_slice
from compas_model.elements import Element
from compas_model.elements import Feature


class BlockMesh(Mesh):
    """Extension of default mesh with API similar to Brep."""

    @property
    def aabb(self) -> Box:
        points = self.vertices_attributes("xyz")
        return Box.from_points(points)

    @property
    def convex_hull(self) -> Mesh:
        points = self.vertices_attributes("xyz")
        vertices, faces = convex_hull_numpy(points)
        vertices = [points[index] for index in vertices]
        return Mesh.from_vertices_and_faces(vertices, faces)

    @property
    def obb(self) -> Box:
        points = self.vertices_points(self.vertices())
        return Box.from_bounding_box(oriented_bounding_box_numpy(points))

    def boolean_difference(self, *others: "BlockMesh") -> "BlockMesh":
        """Return the boolean difference of this mesh and one or more other meshes.

        Parameters
        ----------
        others : :class:`BlockMesh` | list[:class:`BlockMesh`]
            One or more meshes to subtract.

        Returns
        -------
        :class:`BlockMesh`

        """
        A = self.to_vertices_and_faces()
        if not isinstance(others, list):
            others = [others]
        for mesh in others:
            B = mesh.to_vertices_and_faces()
            A = boolean_difference_mesh_mesh(A, B)
        return type(self).from_vertices_and_faces(*A)

    def boolean_intersection(self, *others: "BlockMesh") -> "BlockMesh":
        """Return the boolean intersection between this mesh and one or more other meshes.

        Parameters
        ----------
        others : :class:`BlockMesh` | list[:class:`BlockMesh`]
            One or more intersection meshes.

        Returns
        -------
        :class:`BlockMesh`

        """
        A = self.to_vertices_and_faces()
        if not isinstance(others, list):
            others = [others]
        for mesh in others:
            B = mesh.to_vertices_and_faces()
            A = boolean_intersection_mesh_mesh(A, B)
        return type(self).from_vertices_and_faces(*A)

    def boolean_union(self, *others: "BlockMesh") -> "BlockMesh":
        """Return the boolean union of this mesh and one or more other meshes.

        Parameters
        ----------
        others : :class:`BlockMesh` | list[:class:`BlockMesh`]
            One or more meshes to add.

        Returns
        -------
        :class:`BlockMesh`

        """
        A = self.to_vertices_and_faces()
        if not isinstance(others, list):
            others = [others]
        for mesh in others:
            B = mesh.to_vertices_and_faces()
            A = boolean_union_mesh_mesh(A, B)
        return type(self).from_vertices_and_faces(*A)

    def slice(self, plane: Plane) -> list["Polyline"]:
        pass

    def split(self, plane: Plane) -> list["BlockMesh"]:
        pass

    def trim(self, plane: Plane) -> None:
        pass


# A block could have features like notches,
# but we will work on it when we need it...
# A notch could be a cylinder defined in the frame of a face.
# The frame of a face should be defined in coorination with the global frame of the block.
# during interface detection the features could/should be ignored.
class BlockFeature(Feature):
    pass


class BlockElement(Element):
    """Class representing block elements.

    Parameters
    ----------
    shape : :class:`compas.datastructures.Mesh`
        The base shape of the block.
    features : list[:class:`BlockFeature`], optional
        Additional block features.
    is_support : bool, optional
        Flag indicating that the block is a support.
    frame : :class:`compas.geometry.Frame`, optional
        The coordinate frame of the block.
    name : str, optional
        The name of the element.

    Attributes
    ----------
    shape : :class:`compas.datastructures.Mesh`
        The base shape of the block.
    features : list[:class:`BlockFeature`]
        A list of additional block features.
    is_support : bool
        Flag indicating that the block is a support.

    """

    elementgeometry: BlockMesh
    modelgeometry: BlockMesh

    @property
    def __data__(self) -> dict:
        data = super().__data__
        data["shape"] = self.shape
        data["features"] = self.features
        data["is_support"] = self.is_support
        return data

    def __init__(
        self,
        shape: BlockMesh,
        features: Optional[list[BlockFeature]] = None,
        is_support: bool = False,
        transformation: Optional[Transformation] = None,
        name: Optional[str] = None,
    ) -> None:
        super().__init__(transformation=transformation, features=features, name=name)

        self.shape = shape
        self.is_support = is_support

    # =============================================================================
    # Constructors
    # =============================================================================

    @classmethod
    def from_box(cls, box: Box) -> "BlockElement":
        """Construct a block element from a box.

        Parameters
        ----------
        box : :class:`compas.geometry.Box`
            A box.

        Returns
        -------
        :class:`BlockElement`

        """
        return cls(shape=BlockMesh.from_shape(box))

    @classmethod
    def from_polyhedron(cls, polyhedron: Polyhedron) -> "BlockElement":
        """Construct a block element from a polyhedron.

        Parameters
        ----------
        polyhedron : :class:`compas.geometry.Polyhedron`
            A box.

        Returns
        -------
        :class:`BlockElement`

        """
        return cls(shape=BlockMesh.from_shape(polyhedron))

    @classmethod
    def from_mesh(cls, mesh: Mesh) -> "BlockElement":
        """Construct a block element from a mesh.

        Parameters
        ----------
        mesh : :class:`compas.datastructures.Mesh`
            A mesh.

        Returns
        -------
        :class:`BlockElement`

        """
        return cls(shape=mesh.copy(cls=BlockMesh))

    # =============================================================================
    # Implementations of abstract methods
    # =============================================================================

    def compute_elementgeometry(self) -> BlockMesh:
        geometry = self.shape
        self._geometry = geometry
        return geometry

    def compute_aabb(self, inflate=None) -> Box:
        box = self.modelgeometry.aabb
        if inflate and inflate != 1.0:
            box.xsize += inflate
            box.ysize += inflate
            box.zsize += inflate
        self._aabb = box
        return box

    def compute_obb(self, inflate=None) -> Box:
        box = self.modelgeometry.obb
        if inflate and inflate != 1.0:
            box.xsize += inflate
            box.ysize += inflate
            box.zsize += inflate
        self._obb = box
        return box

    def compute_collision_mesh(self) -> Mesh:
        mesh = self.modelgeometry.convex_hull
        self._collision_mesh = mesh
        return mesh

    def compute_point(self) -> Point:
        return Point(*self.modelgeometry.centroid())
