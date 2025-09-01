from typing import Optional

from compas.datastructures import Mesh
from compas.geometry import Box
from compas.geometry import Point
from compas.geometry import Polyhedron
from compas.geometry import Transformation
from compas_model.elements import Element
from compas_model.elements import Feature

# A block could have features like notches,
# but we will work on it when we need it...
# A notch could be a cylinder defined in the frame of a face.
# The frame of a face should be defined in coorination with the global frame of the block.
# during interface detection the features could/should be ignored.


class BlockFeature(Feature):
    pass


class Block(Element):
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

    _geometry: Mesh

    elementgeometry: Mesh  # type: ignore
    modelgeometry: Mesh  # type: ignore

    @property
    def __data__(self) -> dict:
        data = super().__data__
        data["geometry"] = self._geometry
        data["is_support"] = self.is_support
        return data

    def __init__(
        self,
        geometry: Mesh,
        features: Optional[list[BlockFeature]] = None,
        transformation: Optional[Transformation] = None,
        name: Optional[str] = None,
        is_support: bool = False,
    ) -> None:
        super().__init__(geometry=geometry, transformation=transformation, features=features, name=name)

        self.is_support = is_support

    # =============================================================================
    # Constructors
    # =============================================================================

    @classmethod
    def from_box(cls, box: Box, **kwargs) -> "Block":
        """Construct a block element from a box.

        Parameters
        ----------
        box : :class:`compas.geometry.Box`
            A box.

        Returns
        -------
        :class:`Block`

        """
        return cls(geometry=Mesh.from_shape(box), **kwargs)

    @classmethod
    def from_polyhedron(cls, polyhedron: Polyhedron, **kwargs) -> "Block":
        """Construct a block element from a polyhedron.

        Parameters
        ----------
        polyhedron : :class:`compas.geometry.Polyhedron`
            A box.

        Returns
        -------
        :class:`Block`

        """
        return cls(geometry=Mesh.from_polyhedron(polyhedron), **kwargs)

    @classmethod
    def from_mesh(cls, mesh: Mesh, **kwargs) -> "Block":
        """Construct a block element from a mesh.

        Parameters
        ----------
        mesh : :class:`compas.datastructures.Mesh`
            A mesh.

        Returns
        -------
        :class:`Block`

        """
        return cls(geometry=mesh.copy(cls=Mesh), **kwargs)

    # =============================================================================
    # Implementations of abstract methods
    # =============================================================================

    def compute_elementgeometry(self, include_features: bool = False) -> Mesh:
        """Compute the element geometry of the block element.

        Note that the block element is not parametric
        Therefor, this simply returns the mesh geometry that was provided as input when creating the element object.

        Returns
        -------
        :class:`Mesh`

        """
        return self._geometry

    def compute_aabb(self, inflate: float = 1.0) -> Box:
        box: Box = self.modelgeometry.aabb()
        if inflate != 1.0:
            box.xsize *= inflate
            box.ysize *= inflate
            box.zsize *= inflate
        self._aabb = box
        return box

    def compute_obb(self, inflate: float = 1.0) -> Box:
        box: Box = self.modelgeometry.obb()
        if inflate != 1.0:
            box.xsize *= inflate
            box.ysize *= inflate
            box.zsize *= inflate
        self._obb = box
        return box

    def compute_point(self) -> Point:
        return Point(*self.modelgeometry.centroid())
