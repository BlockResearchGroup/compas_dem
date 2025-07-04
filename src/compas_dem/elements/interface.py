from typing import Optional
from typing import Union

from compas.datastructures import Mesh
from compas.geometry import Box
from compas.geometry import Brep
from compas.geometry import Frame
from compas.geometry import Transformation
from compas_model.elements import Element


class Interface(Element):
    """Class representing interface elements.

    Parameters
    ----------
    shape : :class:`compas.datastructures.Mesh` or :class:`compas.geometry.Brep`
        The base shape of the interface.
    frame : :class:`compas.geometry.Frame`, optional
        The coordinate frame of the interface.
    name : str, optional
        The name of the element.

    Attributes
    ----------
    shape : :class:`compas.datastructures.Mesh` or :class:`compas.geometry.Brep`
        The base shape of the interface.

    """

    _geometry: Union[Mesh, Brep]

    @property
    def __data__(self) -> dict:
        data = super().__data__
        data["geometry"] = self._geometry
        return data

    def __init__(
        self,
        geometry: Union[Mesh, Brep],
        transformation: Optional[Transformation] = None,
        name: Optional[str] = "Interface",
    ) -> None:
        super().__init__(geometry=geometry, transformation=transformation, name=name)

    def compute_elementgeometry(self, include_features: bool = False) -> Mesh:
        return self._geometry

    @classmethod
    def from_box_mesh(cls, frame: Frame, xsize: float, ysize: float, zsize: float) -> "Interface":
        box = Box(xsize, ysize, zsize, frame)
        return cls(box.to_mesh())

    @classmethod
    def from_box_brep(cls, frame: Frame, xsize: float, ysize: float, zsize: float) -> "Interface":
        box = Box(xsize, ysize, zsize, frame)
        return cls(Brep.from_box(box))
