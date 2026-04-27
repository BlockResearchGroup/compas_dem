from typing import Optional

from compas.data import Data
from compas.geometry import Vector
from compas_cgal.measure import mesh_volume

from compas_dem.interactions import ContactProperties
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
    >>> from compas_dem.problem import BoundaryConditions
    >>> model = BlockModel()
    >>> bc = BoundaryConditions(gravity=True)
    >>> problem = Problem(model)
    >>> problem.apply_bc(bc)
    >>> result = problem.solve(solver="LMGC90")
    """

    def __init__(self, model: BlockModel, name: Optional[str] = None) -> None:
        super().__init__(name=name)
        self.model = model
        self._bcs: list[BoundaryConditions] = []

        # Build index → block lookup, kept in sync with model
        self._blocks: dict[int, object] = {block.graphnode: block for block in model.elements()}

        # Resolved nodal loads: block_index → {"force": Vector, "moment": Vector, "loading_type": str}
        self._centroidal_loads: dict[int, dict] = {idx: {"force": Vector(0, 0, 0), "moment": Vector(0, 0, 0), "loading_type": "ramp"} for idx in self._blocks}

        # Resolved nodal displacements: block_index → {"translation": list, "rotation": list}
        self._centroidal_displacements: dict[int, dict] = {}

        # Global contact properties — applied to all interfaces unless overridden
        self._contact_properties: list[ContactProperties] = []

    # =============================================================================
    # Boundary conditions
    # =============================================================================

    def apply_bc(self, bc: BoundaryConditions) -> None:
        """Apply a boundary condition set — forces and displacement BCs together.

        Forces are resolved immediately to (force, moment) pairs at block centroids.
        Displacement BCs are stored per-block as (translation, rotation) pairs.

        Parameters
        ----------
        bc : :class:`BoundaryConditions`
            The boundary condition set to apply.
        """
        self._bcs.append(bc)

        for idx, block in self._blocks.items():
            if block.material:
                density = block.material.density
            else:
                Warning(f"Block {block.graphnode} material density not specified, defaulting to 2400.0 kg/m3.")
                density = 2400.0
            volume = mesh_volume(block.modelgeometry.to_vertices_and_faces(True))
            block.mass = volume * density

        # Gravity
        if bc.gravity:
            g_vec = Vector(0, 0, -bc.g)
            for idx, block in self._blocks.items():
                self._centroidal_loads[idx]["force"] += g_vec * block.mass

        # Body forces
        for acc in bc.body_forces:
            a_vec = Vector(*acc)
            for idx, block in self._blocks.items():
                self._centroidal_loads[idx]["force"] += a_vec * block.mass

        # Point loads
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
            self._centroidal_loads[idx]["force"] += force
            self._centroidal_loads[idx]["moment"] += moment
            self._centroidal_loads[idx]["loading_type"] = entry["loading_type"]

        # Surface loads
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
            self._centroidal_loads[idx]["force"] += force
            self._centroidal_loads[idx]["moment"] += moment

        # Displacement BCs
        for entry in bc.displacements:
            idx = entry["block_index"]
            if idx not in self._centroidal_displacements:
                self._centroidal_displacements[idx] = {"translation": None, "rotation": None}
            if entry["translation"] is not None:
                self._centroidal_displacements[idx]["translation"] = entry["translation"]
            if entry["rotation"] is not None:
                self._centroidal_displacements[idx]["rotation"] = entry["rotation"]

    @property
    def bcs(self) -> list[BoundaryConditions]:
        return self._bcs

    @property
    def centroidal_loads(self) -> dict[int, dict]:
        """Resolved (force, moment) pairs at each block centroid."""
        return self._centroidal_loads

    @property
    def centroidal_displacements(self) -> dict[int, dict]:
        """Prescribed (translation, rotation) pairs per block index."""
        return self._centroidal_displacements

    # =============================================================================
    # Contact properties
    # =============================================================================

    def add_contact(self, contact_properties: ContactProperties) -> None:
        """Add a global contact property set applied to all interfaces.

        Multiple sets can be added; solvers use the last one added unless
        per-interface overrides are supported.

        Parameters
        ----------
        contact_properties : :class:`~compas_dem.interactions.ContactProperties`
            The contact and joint model to apply globally.
        """
        self._contact_properties.append(contact_properties)

    @property
    def contact_properties(self) -> list[ContactProperties]:
        """Global contact property sets, in order of addition."""
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

        raise ValueError(f"Solver '{solver}' is not recognised. Available: 'LMGC90'.")

    # =============================================================================
    # Serialization
    # =============================================================================

    @property
    def __data__(self) -> dict:
        return {
            "name": self.name,
            "model": self.model,
            "bcs": self._bcs,
            "centroidal_loads": {
                idx: {
                    "force": list(entry["force"]),
                    "moment": list(entry["moment"]),
                }
                for idx, entry in self._centroidal_loads.items()
            },
            "centroidal_displacements": self._centroidal_displacements,
            "contact_properties": self._contact_properties,
        }
