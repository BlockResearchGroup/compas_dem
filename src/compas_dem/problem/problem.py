from typing import Optional

import compas.geometry as cg
from compas.data import Data
from compas.geometry import Vector
from compas_cgal.measure import mesh_volume

from compas_dem.interactions import ContactProperties
from compas_dem.interactions import JointModel
from compas_dem.interactions import MohrCoulomb
from compas_dem.models import BlockModel
from compas_dem.problem.boundary_conditions import BoundaryConditions


class Problem(Data):
    """Defines a structural problem over a block model.

    Parameters
    ----------
    model : :class:`compas_dem.models.BlockModel`
        The discrete element model.
    name : str, optional
        Name of the problem.

    Examples
    --------
    >>> from compas_dem.models import BlockModel
    >>> model = BlockModel()
    >>> problem = Problem(model)
    >>> problem.add_gravity()
    >>> problem.add_support(block_index=0)
    >>> result = problem.solve(solver="LMGC90")  # doctest: +SKIP
    """

    def __init__(self, model: BlockModel, name: Optional[str] = None) -> None:
        super().__init__(name=name)
        self.model = model
        self._boundary_conditions = BoundaryConditions()
        self._blocks: dict[int, object] = {block.graphnode: block for block in model.elements()}
        self._contact_properties = ContactProperties()

        for block in self._blocks.values():
            if block.material:
                density = block.material.density
            else:
                Warning(f"Block {block.graphnode} material density not specified, defaulting to 2400.0 kg/m3.")
                density = 2400.0
            volume = mesh_volume(block.modelgeometry.to_vertices_and_faces(True))
            block.mass = volume * density

    # ============================================================================
    # Pre-visualization utilities
    # ===========================================================================
    def inspect_model(self, show_indices: bool = True) -> None:
        from compas_viewer.scene import Tag
        from compas_viewer.viewer import Viewer

        viewer = Viewer()
        for element in self.model.elements():
            block_ = viewer.scene.add_group(name=f"Block {element.graphnode}")
            if show_indices:
                tag = Tag(str(element.graphnode), element.point)
                block_.add(tag)
            block_.add(element.modelgeometry, opacity=0.2, name=f"Block {element.graphnode}")
        viewer.show()

        raise ChildProcessError("Model inspection complete. Please refer to the viewer and console for block indices when adding boundary conditions.")

    def add_gravity(self, g: float = 9.81) -> None:
        """Apply self-weight to all blocks using material density.

        Parameters
        ----------
        g : float, optional
            Gravitational acceleration in [m/s²]. Default 9.81.
        """
        self._boundary_conditions.add_gravity(g)

    def add_global_body_force(self, ax: float, ay: float, az: float) -> None:
        """Add a global body acceleration applied to all blocks.

        The resultant force on each block is F = [ax, ay, az] * density * volume.

        Parameters
        ----------
        ax, ay, az : float
            Acceleration components in [m/s²].
        """
        self._boundary_conditions.add_global_body_force(ax, ay, az)

    def add_point_load(
        self,
        block_index: int,
        force: list[float],
        moment: Optional[list[float]] = None,
        point: Optional[list[float]] = None,
        loading_type: str = "ramp",
    ) -> None:
        """Add a concentrated force to a specific block.

        Parameters
        ----------
        block_index : int
            Graph node index of the target block.
        force : list[float]
            Force vector [fx, fy, fz].
        moment : list[float], optional
            Moment vector [mx, my, mz] applied at the centroid.
            Cannot be combined with `point`.
        point : list[float], optional
            Application point [x, y, z]. The equivalent moment at the block
            centroid is resolved automatically.
            Cannot be combined with `moment`.
        loading_type : str, optional
            ``"ramp"`` (default) or ``"instantaneous"``.
        """
        self._boundary_conditions.add_point_load(block_index, force, moment, point, loading_type)

    def add_surface_load(
        self,
        block_index: int,
        polygon: cg.Polygon,
        magnitude: float,
        direction: Optional[list[float]] = None,
    ) -> None:
        """Add a distributed pressure load over a polygon on a block face.

        Parameters
        ----------
        block_index : int
            Graph node index of the target block.
        polygon : :class:`compas.geometry.Polygon`
            The loaded face polygon picked from the block surface.
        magnitude : float
            Pressure magnitude.
        direction : list[float], optional
            Unit vector [dx, dy, dz]. Defaults to the polygon outward normal.
        """
        self._boundary_conditions.add_surface_load(block_index, polygon, magnitude, direction)

    def add_displacement(
        self,
        block_index: int,
        dx: Optional[float] = None,
        dy: Optional[float] = None,
        dz: Optional[float] = None,
    ) -> None:
        """Prescribe a translational displacement on a block, per component.

        Parameters
        ----------
        block_index : int
            Node index of the target block.
        dx, dy, dz : float, optional
        """
        self._boundary_conditions.add_displacement(block_index, dx=dx, dy=dy, dz=dz)

    def add_rotation(self, block_index: int, rotation: list[float]) -> None:
        """Prescribe a rotation on a block about its centroid.

        Parameters
        ----------
        block_index : int
            Node index of the target block.
        rotation : list[float]
            Rotation vector [rx, ry, rz] in [rad].
        """
        self._boundary_conditions.add_rotation(block_index, rotation)

    def add_support(self, block_index: int) -> None:
        """Fix a block — zero translation and zero rotation.

        Parameters
        ----------
        block_index : int
            Node index of the block to fix.
        """
        self._boundary_conditions.add_support(block_index)

    def add_supports_from_model(self) -> None:
        """Fix all blocks whose ``is_support`` flag is ``True`` in the block model."""
        for block in self._blocks.values():
            if getattr(block, "is_support", False):
                self.add_support(block.graphnode)

    def add_bc(self, bc: BoundaryConditions) -> None:
        """Merge a pre-built boundary condition set into this problem.

        Parameters
        ----------
        bc : :class:`BoundaryConditions`
            A boundary condition set to absorb.
        """
        if bc.gravity:
            self.add_gravity(bc.g)
        for acc in bc.body_forces:
            self.add_global_body_force(*acc)
        for entry in bc.point_loads:
            self.add_point_load(**entry)
        for entry in bc.surface_loads:
            self.add_surface_load(**entry)
        for entry in bc.displacements:
            self._boundary_conditions._displacements.append(entry)

    @property
    def boundary_conditions(self) -> BoundaryConditions:
        """The boundary condition data attached to this problem."""
        return self._boundary_conditions

    # =============================================================================
    # Resolved loads and displacements (computed lazily from boundary_conditions)
    # =============================================================================

    @property
    def centroidal_loads(self) -> dict[int, dict]:
        """Resolved (force, moment) pairs at each block centroid."""
        bc = self._boundary_conditions
        loads = {idx: {"force": Vector(0, 0, 0), "moment": Vector(0, 0, 0), "loading_type": "ramp"} for idx in self._blocks}

        if bc.gravity:
            g_vec = Vector(0, 0, -bc.g)
            for idx, block in self._blocks.items():
                loads[idx]["force"] += g_vec * block.mass

        for acc in bc.body_forces:
            a_vec = Vector(*acc)
            for idx, block in self._blocks.items():
                loads[idx]["force"] += a_vec * block.mass

        for entry in bc.point_loads:
            idx = entry["block_index"]
            force = Vector(*entry["force"])
            if entry["point"] is not None:
                r = Vector(*entry["point"]) - self._blocks[idx].point
                moment = Vector(*r.cross(force))
            elif entry["moment"] is not None:
                moment = Vector(*entry["moment"])
            else:
                moment = Vector(0, 0, 0)
            loads[idx]["force"] += force
            loads[idx]["moment"] += moment
            loads[idx]["loading_type"] = entry["loading_type"]

        for entry in bc.surface_loads:
            idx = entry["block_index"]
            polygon = entry["polygon"]
            magnitude = entry["magnitude"]
            area = polygon.area
            barycenter = polygon.centroid
            direction = Vector(*entry["direction"]) if entry["direction"] is not None else Vector(*polygon.normal)
            force = direction * (magnitude * area)
            r = barycenter - self._blocks[idx].point
            moment = Vector(*r.cross(force))
            loads[idx]["force"] += force
            loads[idx]["moment"] += moment

        return loads

    @property
    def centroidal_displacements(self) -> dict[int, dict]:
        """Prescribed (translation, rotation) pairs per block index."""
        displacements = {}
        for entry in self._boundary_conditions.displacements:
            idx = entry["block_index"]
            if idx not in displacements:
                displacements[idx] = {"translation": [None, None, None], "rotation": [None, None, None]}
            if entry["translation"] is not None:
                for j, v in enumerate(entry["translation"]):
                    if v is not None:
                        displacements[idx]["translation"][j] = v
            if entry["rotation"] is not None:
                for j, v in enumerate(entry["rotation"]):
                    if v is not None:
                        displacements[idx]["rotation"][j] = v
        return displacements

    # =============================================================================
    # Contact properties
    # =============================================================================

    _CONTACT_MODELS: dict[str, type] = {
        "MohrCoulomb": MohrCoulomb,
    }

    def add_contact_model(self, model: str, **kwargs) -> None:
        """Set the contact model by name.

        Parameters
        ----------
        model : str
            Contact model type. Supported:
            - ``"MohrCoulomb"`` - takes phi (deg) or mu, cohesion c
        **kwargs
            Parameters forwarded to the contact model constructor.

        Raises
        ------
        ValueError
            If the model name is not recognised.
        """
        if model not in self._CONTACT_MODELS:
            raise ValueError(f"Contact model '{model}' is not recognised. Available: {list(self._CONTACT_MODELS)}.")
        self._contact_properties.contact_model = self._CONTACT_MODELS[model](**kwargs)

    def add_joint_model(self, kn: float, kt: float, tc: Optional[float] = None) -> None:
        """Set the joint stiffness model.

        Parameters
        ----------
        kn : float
            Normal stiffness [N/m].
        kt : float
            Tangential stiffness [N/m].
        tc : float, optional
            Tension cut-off [Pa].
        """
        self._contact_properties.joint_model = JointModel(kn=kn, kt=kt, tc=tc)

    @property
    def contact_properties(self) -> ContactProperties:
        """The contact properties attached to this problem."""
        return self._contact_properties

    # =============================================================================
    # Solve
    # =============================================================================

    def solve(self, solver: str, **kwargs):
        """Solve the problem using the named solver.

        Parameters
        ----------
        solver : str
            Name of the solver. Supported: ``"LMGC90"``, ``"CRA"`` (pending).
        **kwargs
            Passed through to the solver function.

        Returns
        -------
        Solver-specific result object.

        Raises
        ------
        ValueError
            If the solver name is not recognised.
        """
        name = solver.upper()

        if name == "LMGC90":
            from compas_dem.analysis.lmgc90 import lmgc90_solve

            return lmgc90_solve(self, **kwargs)

        if name == "CRA":
            from compas_dem.analysis.cra import cra_solve

            return cra_solve(self, **kwargs)

        raise ValueError(f"Solver '{solver}' is not recognised. Available: 'LMGC90', 'CRA'.")

    # =============================================================================
    # Serialization
    # =============================================================================

    @property
    def __data__(self) -> dict:
        return {
            "name": self.name,
            "model": self.model,
            "boundary_conditions": self._boundary_conditions,
            "contact_properties": self._contact_properties,
        }
