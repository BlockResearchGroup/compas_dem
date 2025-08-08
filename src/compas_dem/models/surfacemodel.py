from typing import Generator
from typing import Iterator
from typing import Optional
from typing import Type
from typing import TYPE_CHECKING

from compas.datastructures import Mesh

from compas_model.models import Model

from compas_dem.templates import Template
from compas_tna.diagrams import FormDiagram
from compas_dem.models.blockmodel import BlockModel, pattern_inverse_height_thickness
from compas_libigl.mapping import TESSAGON_TYPES
from compas_cgal.meshing import trimesh_dual
from compas_libigl.intersections import intersection_ray_mesh
from compas.geometry import Vector

def interpolate_middle_mesh(intrados: Mesh, extrados: Mesh) -> Mesh:
    """Interpolate a middle mesh between the intrados and extrados meshes. Assumes that the meshes are aligned and have the same number of vertices.

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
    middle = intrados.copy(cls=Mesh)
    thk_list = []
    for key in intrados.vertices():
        _, _, zi = intrados.vertex_coordinates(key)  # type: ignore
        _, _, ze = extrados.vertex_coordinates(key) # type: ignore
        middle.vertex_attribute(key, 'z', (zi + ze) / 2)
        middle.vertex_attribute(key, 'thickness', ze - zi)

    return middle

def offset_from_middle(middle: Mesh, fixed_xy: bool = True) -> tuple:
    """
    Offset a middle surface mesh to obtain extrados and intrados meshes using thickness attributes.

    Parameters
    ----------
    middle : Mesh
        The middle surface mesh with thickness attributes per vertex.
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
    extrados = middle.copy(cls=Mesh)
    intrados = middle.copy(cls=Mesh)

    for key in middle.vertices():
        x, y, z = middle.vertex_coordinates(key)  # type: ignore
        nx, ny, nz = middle.vertex_normal(key)
        
        # Get thickness for this specific vertex
        thickness = middle.vertex_attribute(key, 'thickness')
        if thickness is None:
            thickness = 0.5
        half_thick = 0.5 * thickness

        if fixed_xy:
            # Prevent division by zero for horizontal normals
            if abs(nz) < 1e-8:
                raise ValueError(f"Normal at vertex {key} is (almost) horizontal: {nx, ny, nz}")
            dz = half_thick / nz
            extrados_z = z + dz
            intrados_z = z - dz
            # print('z, dz, intrados_z, extrados_z', z, dz, intrados_z, extrados_z)

            extrados.vertex_attribute(key, 'z', extrados_z)
            intrados.vertex_attribute(key, 'z', intrados_z)

            print('changed extrados z', extrados.vertex_attribute(key, 'z'))
            print('changed intrados z', intrados.vertex_attribute(key, 'z'))
        else:
            # Full normal offset
            extrados.vertex_attributes(key, 'xyz', [
                x + half_thick * nx,
                y + half_thick * ny,
                z + half_thick * nz
            ])
            intrados.vertex_attributes(key, 'xyz', [
                x - half_thick * nx,
                y - half_thick * ny,
                z - half_thick * nz
            ])
    return intrados, extrados


def project_mesh_to_target_vertical(mesh: Mesh, target: Mesh):
    """Project a mesh vertically (in Z direction) onto a target mesh.
    
    Parameters
    ----------
    mesh : Mesh
        The mesh to be projected.
    target : Mesh
        The target mesh to project onto.
        
    Returns
    -------
    None
        The mesh is modified in place.
    """
    # Get target mesh vertices for simple vertical projection
    target_vertices = list(target.vertices())
    target_points = [target.vertex_point(v) for v in target_vertices]
    
    for vertex in mesh.vertices():
        point = mesh.vertex_point(vertex)
        
        # Find the closest target vertex in XY plane
        min_distance = float('inf')
        closest_z = point.z
        
        for target_point in target_points:
            # Calculate XY distance (ignore Z)
            xy_distance = ((point.x - target_point.x) ** 2 + (point.y - target_point.y) ** 2) ** 0.5
            
            if xy_distance < min_distance:
                min_distance = xy_distance
                closest_z = target_point.z
        
        # Update vertex to closest Z value
        new_point = point.copy()
        new_point.z = closest_z
        mesh.vertex_attributes(vertex, "xyz", new_point)


class SurfaceModel(Model):
    """Variation of COMPAS Model specifically designed for working with Intrados and Extrados surfaces for masonry construction."""

    intrados: Mesh
    extrados: Mesh
    middle: Mesh
    fill: Mesh
    formdiagram: FormDiagram
    template: Template

    def __init__(self, name=None):
        super().__init__(name)

        self._thickness = 0.5
        self._rho = 20.0
        self._area = 0.0
        self._volume = 0.0
        self._total_selfweight = 0.0


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
        else: 
            model.middle = interpolate_middle_mesh(intrados, extrados)
        
        return model

    @classmethod
    def from_formdiagram(cls, formdiagram: FormDiagram, thickness: Optional[float] = None) -> "SurfaceModel":
        """Construct a model from a FormDiagram with specified thickness.

        Parameters
        ----------
        formdiagram : FormDiagram
            The form diagram to create the surface model from.
        thickness : float, optional
            The thickness of the model. If None, uses thickness values stored in formdiagram vertices.

        Returns
        -------
        :class:`SurfaceModel`

        """
        model = cls()
            
        model.formdiagram = formdiagram
        model.middle = formdiagram.copy(cls=Mesh)

        if thickness is not None:
            model.thickness = thickness
            # Using setter will update the formdiagram and middle mesh attributes. 
        
        # Create intrados and extrados using thickness from middle mesh
        intrados, extrados = offset_from_middle(model.middle)
        model.intrados = intrados
        model.extrados = extrados

        # Todo: Check the meaning of the funicular trajectory
        ze = model.extrados.vertices_attribute('z')
        zi = model.intrados.vertices_attribute('z')
        max_ze, min_ze = max(ze), min(ze)
        max_zi, min_zi = max(zi), min(zi)
        print(f"Max z: {max_ze}, Min z: {min_ze}")
        print(f"Max z: {max_zi}, Min z: {min_zi}")
        
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

        model = cls.from_meshes(*template.intrados_and_extrados())
        model.template = template
        model.thickness = template.thk
        return model

    @classmethod
    def from_blockmodel(cls):
        raise NotImplementedError
    

    # =============================================================================
    # Interoperability
    # =============================================================================

    def to_blocks(self, option="Dual", option2="Hex", base_mesh=None, **kwargs) -> BlockModel:

        if base_mesh is None:
            mesh = self.formdiagram.copy(cls=Mesh)
        else:
            mesh = base_mesh

        if option == "Dual":
            blockmodel = BlockModel.from_dual(mesh)

        elif option == "MeshPattern":

            if option2 not in TESSAGON_TYPES:
                raise NotImplementedError
            
            blockmodel = BlockModel.from_meshpattern(mesh, option2)
        else:
            raise NotImplementedError(f"Option {option} is not implemented for SurfaceModel.to_blocks()")

        return blockmodel
    
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

    @property
    def thickness(self) -> float:
        """Get the average thickness of the model.
        
        Returns
        -------
        float
            The average thickness of the model.
        """
        if hasattr(self, 'formdiagram') and self.formdiagram is not None:
            has_thickness = all(self.formdiagram.vertex_attribute(vertex, 'thickness') is not None 
                           for vertex in self.formdiagram.vertices())
            # Return average thickness from form diagram vertices
            if has_thickness:
                thicknesses = [self.formdiagram.vertex_attribute(key, 'thickness') 
                            for key in self.formdiagram.vertices()]
                return sum(thicknesses) / len(thicknesses)
            else:
                return self._thickness
        return self._thickness

    @thickness.setter
    def thickness(self, value: float) -> None:
        """Set a uniform thickness for all vertices of the model.
        
        Parameters
        -------
        value : float
            The thickness value to set for all vertices.
        """
        self._thickness = value
        # Update all vertices in form diagram if it exists
        if hasattr(self, 'formdiagram') and self.formdiagram is not None:
            for key in self.formdiagram.vertices():
                self.formdiagram.vertex_attribute(key, 'thickness', value)
        
        # Sync thickness to middle mesh if it exists
        if hasattr(self, 'middle') and self.middle is not None:
            for key in self.middle.vertices():
                self.middle.vertex_attribute(key, 'thickness', value)

    @property
    def rho(self) -> float:
        """Get the density of the model.
        
        Returns
        -------
        float
            The density of the model in kg/m³.
        """
        return self._rho

    @rho.setter
    def rho(self, value: float) -> None:
        """Set the density of the model.
        
        Parameters
        -------
        value : float
            The density value to set in kg/m³.
        """
        self._rho = value

    def set_vertex_thickness(self, vertex_key: int, thickness: float) -> None:
        """Set the thickness for a specific vertex in the form diagram.
        
        Parameters
        -------
        vertex_key : int
            The vertex key to set thickness for.
        thickness : float
            The thickness value to set.
        """
        if hasattr(self, 'formdiagram') and self.formdiagram is not None:
            self.formdiagram.vertex_attribute(vertex_key, 'thickness', thickness)
            
            # Also update the middle mesh if it exists
            if hasattr(self, 'middle') and self.middle is not None:
                self.middle.vertex_attribute(vertex_key, 'thickness', thickness)
        else:
            raise ValueError("FormDiagram is not set. Cannot set vertex thickness.")

    def get_vertex_thickness(self, vertex_key: int) -> float:
        """Get the thickness for a specific vertex in the form diagram.
        
        Parameters
        -------
        vertex_key : int
            The vertex key to get thickness for.
            
        Returns
        -------
        float
            The thickness value for the vertex.
        """
        if hasattr(self, 'formdiagram') and self.formdiagram is not None:
            return self.formdiagram.vertex_attribute(vertex_key, 'thickness')
        return self._thickness


    def set_variable_thickness(self, tmin: float = None, tmax: float = None) -> None:
        """Set variable thickness based on inverse height using the pattern_inverse_height_thickness function.
        
        This method applies thickness variation based on the height of vertices in the form diagram,
        where higher vertices get thinner thickness and lower vertices get thicker thickness.
        
        Parameters
        -------
        tmin : float, optional
            Minimum thickness. If None, will be calculated as 3/1000 of the diagonal of the xy bounding box.
        tmax : float, optional
            Maximum thickness. If None, will be calculated as 50/1000 of the diagonal of the xy bounding box.
        """
        if hasattr(self, 'formdiagram') and self.formdiagram is not None:
            # Apply the pattern_inverse_height_thickness function to the form diagram
            pattern_inverse_height_thickness(self.formdiagram, tmin=tmin, tmax=tmax)
            
            # Sync the thickness values to the middle mesh
            self.sync_thickness_to_middle()
        else:
            raise ValueError("FormDiagram is not set. Cannot set inverse height thickness.")

    def sync_thickness_to_middle(self) -> None:
        """Synchronize thickness attributes from formdiagram to middle mesh.
        
        This method ensures that the middle mesh has the same thickness values
        as the formdiagram vertices.
        """
        if hasattr(self, 'formdiagram') and self.formdiagram is not None and hasattr(self, 'middle') and self.middle is not None:
            for vertex in self.middle.vertices():
                thickness_value = self.formdiagram.vertex_attribute(vertex, 'thickness')
                if thickness_value is None:
                    thickness_value = self._thickness
                self.middle.vertex_attribute(vertex, 'thickness', thickness_value)
        else:
            raise ValueError("Both FormDiagram and middle mesh must be set to sync thickness.")

    def compute_volume(self) -> float:
        """Compute and returns the volume of the structure based on the area and thickness in the data.

        Returns
        -------
        float
            The total volume of the structure.

        """
        if self.middle is None:
            if self.intrados is not None and self.extrados is not None:
                self.middle = interpolate_middle_mesh(self.intrados, self.extrados)
            else:
                raise ValueError("Middle mesh is not available and cannot be interpolated.")
        
        middle = self.middle
        total_volume = 0.0

        print('test')
        
        # Use variable thickness from middle mesh vertices
        for vertex in middle.vertices():
            thickness = middle.vertex_attribute(vertex, 'thickness')
            if thickness is None:
                thickness = self._thickness
            vertex_area = middle.vertex_area(vertex)  # should be projected area
            vertex_volume = thickness * vertex_area
            total_volume += vertex_volume

        return total_volume

    def compute_selfweight(self) -> float:
        """Compute and returns the total selfweight of the structure based on the area and thickness in the data.

        Returns
        -------
        float
            The total selfweight of the structure.

        """
        if self.middle is None:
            if self.intrados is not None and self.extrados is not None:
                self.middle = interpolate_middle_mesh(self.intrados, self.extrados)
            else:
                raise ValueError("Middle mesh is not available and cannot be interpolated.")

        middle = self.middle
        rho = self.rho
        total_selfweight = 0.0
        
        # Use variable thickness from middle mesh vertices
        for vertex in middle.vertices():
            thickness = middle.vertex_attribute(vertex, 'thickness')
            if thickness is None:
                thickness = self._thickness
            vertex_area = middle.vertex_area(vertex)
            vertex_volume = thickness * vertex_area
            vertex_weight = vertex_volume * rho
            total_selfweight += vertex_weight

        return total_selfweight


    # =============================================================================
    # Routines / Loads
    # =============================================================================

    def apply_selfweight(self, normalize=True) -> None:
        """Apply selfweight to the nodes of the form diagram based on the middle surface and local thicknesses.

        Parameters
        ----------
        normalize : bool, optional
            Whether or not normalize the selfweight to match the computed total selfweight, by default True

        Returns
        -------
        None
            The FormDiagram is modified in place

        """
        # Step 1: Check that formdiagram and middle mesh are present
        if self.formdiagram is None:
            raise ValueError("FormDiagram is not set. Please set the formdiagram before applying selfweight.")
        
        if self.middle is None:
            raise ValueError("Middle mesh is not set. Please set the middle mesh before applying selfweight.")

        # Step 2: Compute the selfweight of the shell
        total_selfweight = self.compute_selfweight()
        print(f"Total computed selfweight: {total_selfweight}")

        # Step 3: Copy the form diagram and project it onto the middle mesh vertically
        form_ = self.formdiagram.copy()
        
        # Project form diagram vertically onto the middle mesh
        project_mesh_to_target_vertical(form_, self.middle)

        # Step 4: Handle thickness property - placeholder for different cases
        # Case 1: Form diagram already has thickness property
        has_thickness = all(form_.vertex_attribute(vertex, 'thickness') is not None 
                           for vertex in form_.vertices())
        
        if not has_thickness:
            thickness = self.thickness
            for vertex in form_.vertices():
                form_.vertex_attribute(vertex, 'thickness', thickness)

        # Step 5: Compute and lump selfweight at vertices
        total_pz = 0.0
        for vertex in form_.vertices():
            # Get vertex area and thickness
            vertex_area = form_.vertex_area(vertex)
            thickness = form_.vertex_attribute(vertex, 'thickness')
            
            # Compute selfweight contribution (negative for downward direction)
            pz = -vertex_area * thickness * self.rho
            
            # Store in form diagram
            form_.vertex_attribute(vertex, 'pz', pz)
            total_pz += abs(pz)  # Sum absolute values for normalization

        # Step 6: Scale to match total selfweight if normalize=True
        if normalize and total_pz > 0:
            scale_factor = total_selfweight / total_pz
            print(f"Scaling selfweight by factor: {scale_factor}")
            
            for vertex in form_.vertices():
                pz = form_.vertex_attribute(vertex, 'pz')
                form_.vertex_attribute(vertex, 'pz', pz * scale_factor)

        # Copy the computed loads back to the original form diagram
        for vertex in self.formdiagram.vertices():
            if vertex in form_.vertices():
                pz = form_.vertex_attribute(vertex, 'pz')
                self.formdiagram.vertex_attribute(vertex, 'pz', pz)
            else:
                self.formdiagram.vertex_attribute(vertex, 'pz', 0.0)

        print(f"Selfweight applied to form diagram. Total load: {sum(abs(self.formdiagram.vertex_attribute(vertex, 'pz')) for vertex in self.formdiagram.vertices())}")


    # =============================================================================
    # Routines / Bounds
    # =============================================================================

    def apply_envelope(self) -> None:
        """Apply envelope to the form diagram based on the intrados and extrados surfaces.
        
        This method projects the form diagram onto both intrados and extrados surfaces
        and assigns the heights to 'ub' (upper bound) and 'lb' (lower bound) properties.
        
        Returns
        -------
        None
            The FormDiagram is modified in place.
        """
        # Step 1: Check that formdiagram, intrados and extrados are present
        if self.formdiagram is None:
            raise ValueError("FormDiagram is not set. Please set the formdiagram before applying envelope.")
        
        if self.intrados is None or self.extrados is None:
            raise ValueError("Intra/Extrados not set. Please set them before applying envelope.")

        # Step 2: Copy the form diagram for projection
        form_ub = self.formdiagram.copy()  # For upper bound (extrados)
        form_lb = self.formdiagram.copy()  # For lower bound (intrados)
        
        # Step 3: Project form diagram onto extrados (upper bound)
        project_mesh_to_target_vertical(form_ub, self.extrados)
        
        # Step 4: Project form diagram onto intrados (lower bound)
        v, f = self.intrados.to_vertices_and_faces()
        fresh_intrados = Mesh.from_vertices_and_faces(v, f)
        project_mesh_to_target_vertical(form_lb, self.intrados)
        
        # Step 5: Collect heights and assign to form diagram
        for vertex in self.formdiagram.vertices():
            if vertex in form_ub.vertices() and vertex in form_lb.vertices():
                # Get z coordinates from projected meshes
                _, _, z_ub = form_ub.vertex_coordinates(vertex)
                _, _, z_lb = form_lb.vertex_coordinates(vertex)
                
                # Assign to form diagram
                self.formdiagram.vertex_attribute(vertex, 'ub', z_ub)
                self.formdiagram.vertex_attribute(vertex, 'lb', z_lb)
            else:
                print(f"Warning: Vertex {vertex} not found in projected meshes")
                # Set default values if vertex not found
                self.formdiagram.vertex_attribute(vertex, 'ub', 0.0)
                self.formdiagram.vertex_attribute(vertex, 'lb', 0.0)
        
        # Step 6: Print summary
        ub_values = [self.formdiagram.vertex_attribute(vertex, 'ub') for vertex in self.formdiagram.vertices()]
        lb_values = [self.formdiagram.vertex_attribute(vertex, 'lb') for vertex in self.formdiagram.vertices()]
        
        print(f"Envelope applied to form diagram.")
        print(f"Upper bound range: {min(ub_values):.3f} to {max(ub_values):.3f}")
        print(f"Lower bound range: {min(lb_values):.3f} to {max(lb_values):.3f}")