from typing import Optional

from compas.datastructures import Mesh
from compas.geometry import Box
from compas.geometry import Point
from compas.geometry import Transformation
from compas_model.elements import Element


class Interface(Element):
    """Class representing interface elements.

    Parameters
    ----------
    shape : :class:`compas.datastructures.Mesh`
        The base shape of the block.
    frame : :class:`compas.geometry.Frame`, optional
        The coordinate frame of the block.
    name : str, optional
        The name of the element.

    Attributes
    ----------
    shape : :class:`compas.datastructures.Mesh`
        The base shape of the block.

    """

    _geometry: Mesh

    @property
    def __data__(self) -> dict:
        data = super().__data__
        data["geometry"] = self._geometry
        return data

    def __init__(
        self,
        geometry: Mesh,
        transformation: Optional[Transformation] = None,
        name: Optional[str] = None,
    ) -> None:
        super().__init__(geometry=geometry, transformation=transformation, name=name)

    # =============================================================================
    # Implementations of abstract methods
    # =============================================================================

    def compute_elementgeometry(self, include_features: bool = False) -> Mesh:
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
