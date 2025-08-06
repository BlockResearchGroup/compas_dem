from typing import Generator
from typing import Iterator
from typing import Optional
from typing import Type
from typing import TYPE_CHECKING

from compas.datastructures import Mesh

from compas_model.models import Model

from compas_dem.elements import Block
from compas_dem.interactions import FrictionContact
from compas_dem.templates import BarrelVaultTemplate
from compas_dem.templates import Template
from compas_tna.diagrams import FormDiagram


def interpolate_middle_mesh(intrados: Mesh, extrados: Mesh) -> Mesh:
    """Interpolate a middle mesh between the intrados and extrados meshes.

    Parameters
    ----------
    intrados : :class:`Mesh`
        The intrados surface mesh.
    extrados : :class:`Mesh`
        The extrados surface mesh.

    Returns
    -------
    :class:`Mesh`
        The interpolated middle mesh.

    """
    return NotImplementedError

def offset_from_middle(middle: "Mesh", thickness: float, fixed_xy: bool = True) -> tuple:
    """
    Offset a middle surface mesh to obtain extrados and intrados meshes.

    Parameters
    ----------
    middle : Mesh
        The middle surface mesh.
    thickness : float
        The total thickness; extrados and intrados will be offset by +/- thickness/2.
    fixed_xy : bool, optional
        If True, extrados/intrados will have the same XY as the middle mesh,
        and only Z will be offset (with normal correction).
        If False, full 3D normal offset is used.

    Returns
    -------
    intrados : Mesh
        Offset mesh (intrados).
    extrados : Mesh
        Offset mesh (extrados).
    """
    # extrados = middle.copy()
    # intrados = middle.copy()
    v, f = middle.to_vertices_and_faces()
    extrados = Mesh.from_vertices_and_faces(v, f)
    intrados = Mesh.from_vertices_and_faces(v, f)

    half_thick = 0.5 * thickness

    for key in middle.vertices():
        x, y, z = middle.vertex_coordinates(key)  # type: ignore
        nx, ny, nz = middle.vertex_normal(key)

        if fixed_xy:
            # Prevent division by zero for horizontal normals
            if abs(nz) < 1e-8:
                raise ValueError(f"Normal at vertex {key} is (almost) horizontal: {nx, ny, nz}")
            dz = half_thick / nz
            extrados_z = z + dz
            intrados_z = z - dz
            print(f"Offsetting vertex {key}: ({x}, {y}, {z}) -> ({x}, {y}, {extrados_z}), ({x}, {y}, {intrados_z})")
            extrados.vertex_attribute(key, 'z', extrados_z)
            intrados.vertex_attribute(key, 'z', intrados_z)
        else:
            # Full normal offset
            extrados.vertex_coordinates(key, [
                x + half_thick * nx,
                y + half_thick * ny,
                z + half_thick * nz
            ])
            intrados.vertex_coordinates(key, [
                x - half_thick * nx,
                y - half_thick * ny,
                z - half_thick * nz
            ])
    return intrados, extrados


class SurfaceModel(Model):
    """Variation of COMPAS Model specifically designed for working with Intrados and Extrados surfaces for masonry construction."""

    intrados: Mesh
    extrados: Mesh
    middle: Mesh
    fill: Mesh
    formdiagram: FormDiagram

    def __init__(self, name=None):
        super().__init__(name)

        self._area = 0.0
        self._volume = 0.0
        self._total_selfweight = 0.0

        self.formdiagram = None  # type: Optional[FormDiagram]


    # =============================================================================
    # Factory methods
    # =============================================================================

    @classmethod
    def from_polysurfaces(cls, guid_intrados: str, guid_extrados: str, guid_middle : Optional[str] = None) -> "SurfaceModel":
        """Construct a model from Rhino polysurfaces representing intrados and extrados surfaces.

        Parameters
        ----------
        guids : list[str]
            A list of GUIDs identifying the poly-surfaces representing the blocks of the model.

        Returns
        -------
        :class:`SurfaceModel`

        """
        raise NotImplementedError

    @classmethod
    def from_rhinomeshes(cls, guid_intrados: str, guid_extrados: str, middle : Optional[str] = None) -> "SurfaceModel":
        """Construct a model from Rhino meshes.

        Parameters
        ----------
        guids : list[str]
            A list of GUIDs identifying the meshes representing the blocks of the model.

        Returns
        -------
        :class:`SurfaceModel`

        """
        raise NotImplementedError

    @classmethod
    def from_meshes(cls, intrados: Mesh, extrados: Mesh, middle : Optional[Mesh] = None) -> "SurfaceModel":
        """Construct a model from Rhino meshes.

        Parameters
        ----------
        intrados : Mesh
            The intrados surface mesh of the model.
        extrados : Mesh
            The extrados surface mesh of the model.
        middle : Mesh, optional
            The middle surface mesh of the model.

        Returns
        -------
        :class:`SurfaceModel`

        """
        model = cls()
        model.intrados = intrados
        model.extrados = extrados
        if middle is not None:
            model.middle = middle
        # else: 
        #     interpolate_middle_mesh(intrados, extrados)
        
        return model

    @classmethod
    def from_formdiagram(cls, formdiagram: Mesh, thickness: Optional[float] = None) -> "SurfaceModel":
        """Construct a model from Rhino meshes.

        Parameters
        ----------
        intrados : Mesh
            The intrados surface mesh of the model.
        extrados : Mesh
            The extrados surface mesh of the model.
        middle : Mesh, optional
            The middle surface mesh of the model.

        Returns
        -------
        :class:`SurfaceModel`

        """
        model = cls()
        model.formdiagram = formdiagram
        if thickness is not None:
            v, f = formdiagram.to_vertices_and_faces()
            model.middle = Mesh.from_vertices_and_faces(v, f)             
            # model.middle = formdiagram.copy(cls=Mesh)

            intrados, extrados = offset_from_middle(model.middle, thickness)
            model.intrados = intrados
            model.extrados = extrados
        return model

    @classmethod
    def from_pointcloud(cls, pointcloud) -> "SurfaceModel":
        """Construct a surface model from pointclouds.
        """
        return NotImplementedError


    # =============================================================================
    # Templates
    # =============================================================================

    @classmethod
    def from_template(cls, template: Template) -> "SurfaceModel":
        """Construct a block model from a template.

        Parameters
        ----------
        template : :class:`Template`
            The model template.

        Returns
        -------
        :class:`BlockModel`

        """
        return cls.from_meshes(*template.intrados_and_extrados())

    @classmethod
    def from_blockmodel(cls):
        raise NotImplementedError
    
    # =============================================================================
    # Properties
    # =============================================================================

    @property
    def area(self):
        if not self._area:
            self._area = self.middle.area()
        return self._area

    @property
    def volume(self):
        if not self._volume:
            self._volume = self.compute_volume()
        return self._volume

    @property
    def total_selfweight(self):
        if not self._total_selfweight:
            self._total_selfweight = self.compute_selfweight()
        return self._total_selfweight
