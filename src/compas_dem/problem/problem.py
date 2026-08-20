from typing import Optional
from typing import Union

import compas.geometry as cg
from compas.colors import Color
from compas.data import Data
from compas.geometry import Vector
from compas_dem.interactions import ContactProperties
from compas_dem.interactions import JointModel
from compas_dem.interactions import MohrCoulomb
from compas_dem.models import BlockModel
from compas_dem.problem.boundary_condition import BoundaryConditionGroup
from compas_dem.problem.solvers import Solver


class Problem(Data):
    """Defines a structural problem over a block model.

    The problem holds boundary conditions (loads and prescribed displacements) and
    contact properties.

    Parameters
    ----------
    model : :class:`compas_dem.models.BlockModel`
        The discrete element model. Kept as a transient (non-serialized) reference.
    name : str, optional
        Name of the problem.

    Examples
    --------
    >>> from compas_dem.models import BlockModel
    >>> model = BlockModel()
    >>> problem = Problem(model)
    >>> _ = problem.add_boundary_condition("gravity").add_gravity()
    >>> problem.set_solver(Solver.CRA())  # doctest: +SKIP
    >>> result = problem.solve()  # doctest: +SKIP
    """

    def __init__(self, model: BlockModel, name: Optional[str] = None, **kwargs) -> None:
        super().__init__(name=name)
        self.model_id = str(model.guid)
        self._model: Optional[BlockModel] = model
        self._boundary_conditions: list[BoundaryConditionGroup] = []
        self._contact_properties = ContactProperties()
        self._solver = None

    @property
    def __data__(self) -> dict:
        return {
            "name": self.name,
            "model_id": self.model_id,
            "boundary_conditions": self._boundary_conditions,
            "contact_properties": self._contact_properties,
            "solver": self._solver,
        }

    @classmethod
    def __from_data__(cls, data: dict) -> "Problem":
        obj = cls.__new__(cls)
        Data.__init__(obj, name=data.get("name"))
        obj.model_id = data["model_id"]
        obj._boundary_conditions = list(data.get("boundary_conditions", []))
        obj._contact_properties = data["contact_properties"]
        obj._solver = data["solver"]
        obj._model = None
        return obj

    @property
    def model(self) -> BlockModel:
        """The block model this problem is defined over. Transient: never serialized with the problem."""
        if self._model is None:
            raise ValueError(f"No model loaded into this problem (model_id={self.model_id}). Call problem.load_model(model) first.")
        return self._model

    def load_model(self, model: BlockModel) -> None:
        """Load the model into the problem, checking that the model ID matches.

        Parameters
        ----------
        model : :class:`compas_dem.models.BlockModel`
            The model to load.

        Raises
        ------
        ValueError
            If the model's ``guid`` does not match the problem's ``model_id``.
        """
        if str(model.guid) != self.model_id:
            raise ValueError(f"Model ID {model.guid} does not match problem's model_id {self.model_id}.")
        self._model = model

    # ============================================================================
    # Boundary conditions
    # ============================================================================

    def add_boundary_condition(self, name: str = "default") -> BoundaryConditionGroup:
        """Register a boundary condition on the problem.

        Parameters
        ----------
        name : str, optional
            Name for the boundary condition. Default ``"default"``.
        Raises
        ------
        ValueError
            If a boundary condition with the same name is already registered.
        Returns
        -------
        BoundaryConditionGroup
            The newly added boundary condition instance.
        """
        if name == "default" and name in (bc.name for bc in self._boundary_conditions):
            name = f"default_{len(self._boundary_conditions)}"
        if name in (bc.name for bc in self._boundary_conditions):
            raise ValueError(f"A boundary condition named '{name}' is already registered on this problem.")
        else:
            boundary_condition = BoundaryConditionGroup(name=name)
            self._boundary_conditions.append(boundary_condition)
            return boundary_condition

    @property
    def boundary_conditions(self) -> list[BoundaryConditionGroup]:
        """The ordered list of boundary conditions attached to this problem."""
        return self._boundary_conditions

    def _find_boundary_condition(self, key: Union[int, str, BoundaryConditionGroup]) -> BoundaryConditionGroup:
        """Return the registered boundary condition identified by index, name, or object."""
        if isinstance(key, BoundaryConditionGroup):
            if any(bc is key for bc in self._boundary_conditions):
                return key
            raise ValueError("The given boundary condition is not registered on this problem. Call problem.add_boundary_condition(boundary_condition) first.")
        if isinstance(key, int) and not isinstance(key, bool):
            if 0 <= key < len(self._boundary_conditions):
                return self._boundary_conditions[key]
            raise ValueError(f"No boundary condition at index {key}; {len(self._boundary_conditions)} are registered.")
        if isinstance(key, str):
            matches = [bc for bc in self._boundary_conditions if bc.name == key]
            if not matches:
                raise ValueError(f"No boundary condition named '{key}' is registered on this problem.")
            if len(matches) > 1:
                raise ValueError(f"Multiple boundary conditions are named '{key}'; identify it by index or object instead.")
            return matches[0]
        raise TypeError("Identify a boundary condition by its index, its name, or the BoundaryConditionGroup object itself.")

    def set_solve_order(self, boundary_conditions: list[Union[str, BoundaryConditionGroup]]) -> None:
        """Reorder the registered boundary conditions.

        Setting one boundary condition inside the method only reorders the list of boundary conditions by placing it first,
        and the rest of the boundary conditions will follow in their original order.

        Parameters
        ----------
        boundary_conditions : list[str | :class:`BoundaryConditionGroup`]

        Raises
        ------
        ValueError
            If the list is empty, if an entry does not resolve to a registered boundary
            condition, or if the same boundary condition appears more than once.
        TypeError
            If an entry is not an str, or :class:`BoundaryConditionGroup`.
        """
        if not boundary_conditions:
            raise ValueError("No boundary conditions given to reorder.")
        resolved = [self._find_boundary_condition(key) for key in boundary_conditions]
        if len(set(id(bc) for bc in resolved)) != len(resolved):
            raise ValueError("The solve order contains the same boundary condition more than once.")
        remainder = [bc for bc in self._boundary_conditions if not any(bc is r for r in resolved)]
        self._boundary_conditions = resolved + remainder

    # ============================================================================
    # Pre-visualization utilities
    # ============================================================================

    def inspect_model(
        self,
        show_blocks: bool = False,
        face_indices: bool = True,
        show_loads: bool = True,
        show_supports: bool = True,
        grid: bool = False,
        kill: bool = True,
    ) -> None:
        """Visualize the block model with block indices, loads and boundary conditions.

        Each kind of load gets its own group in the scene tree — "Point Loads",
        "Surface Loads", "Body Forces", "Supports" and "Prescribed Displacements" —
        so they can be toggled independently. A group is only created if the
        corresponding entries exist in at least one of the problem's boundary conditions.

        .. danger::

           With the default ``kill=True`` this method is for inspection only, and
           halts the script once the viewer is closed. **Comment out or remove
           before solving** — leaving it in will block the solver. Pass
           ``kill=False`` to inspect and then carry on to the solve.

        Parameters
        ----------
        model : :class:`compas_dem.models.BlockModel`
            The model to inspect.
        show_blocks : bool, optional
            Draw the block volumes. Default ``False``.
        face_indices : bool, optional
            Draw each face separately so faces can be identified by index.
            Default ``True``.
        show_loads : bool, optional
            Draw point loads, surface loads and body forces. Default ``True``.
        show_supports : bool, optional
            Draw supports and prescribed displacements/rotations. Default ``True``.
        grid : bool, optional
            Show the viewer grid. Default ``False``.
        kill : bool, optional
            Stop the script once the viewer is closed, by raising
            :class:`ChildProcessError`. Default ``True``. Set to ``False`` to
            let execution continue on to the solve.

        Raises
        ------
        ChildProcessError
            If ``kill`` is ``True``, once the viewer is closed.
        """
        from compas_viewer.scene import Tag  # noqa: F401
        from compas_viewer.viewer import Viewer

        viewer = Viewer()
        model = self.model
        if not grid:
            viewer.config.renderer.show_grid = False

        blocks = {block.graphnode: block for block in model.elements()}
        multiple_boundary_conditions = len(self._boundary_conditions) > 1

        def suffix(boundary_condition: BoundaryConditionGroup) -> str:
            """Disambiguate entries by boundary condition, but only when there is more than one."""
            return f"  [{boundary_condition.name or '<unnamed>'}]" if multiple_boundary_conditions else ""

        def block_scale(block) -> float:
            return block.modelgeometry.edge_length([0, 1]) / 2

        def arrow(point, vector: Vector, scale: float) -> Optional[cg.Line]:
            """A line running from ``point`` back along ``vector``, i.e. pointing at ``point``."""
            if vector.length == 0:
                return None
            return cg.Line(point, [p - v for p, v in zip(point, vector.unitized() * scale)])

        def entries(attr: str) -> list[tuple[BoundaryConditionGroup, object]]:
            """Flatten one kind of entry across all boundary conditions, keeping its origin."""
            return [(bc, entry) for bc in self._boundary_conditions for entry in getattr(bc, attr)]

        def resolve_block(boundary_condition: BoundaryConditionGroup, index: int, kind: str):
            """Look up a block, warning instead of raising so inspection still runs."""
            if index not in blocks:
                print(f"{kind} references block_index={index}, which does not exist in the model.{suffix(boundary_condition)}")
                return None
            return blocks[index]

        if show_loads:
            point_loads = entries("point_loads")
            surface_loads = entries("surface_loads")
            body_forces = entries("body_forces")

            if not point_loads:
                print("No point loads defined in the problem boundary conditions.")
            else:
                loads_view = viewer.scene.add_group(name="Point Loads")
                for bc, loads in point_loads:
                    block = resolve_block(bc, loads.block_index, "Point load")
                    if block is None:
                        continue
                    force = Vector(*loads.force)
                    point = loads.point if loads.point is not None else list(block.point)
                    line = arrow(point, force, block_scale(block))
                    if line is None:
                        continue
                    loads_view.add(
                        line,
                        name=f"Point Load: [{force.x:.1f}, {force.y:.1f}, {force.z:.1f}] \n Moment: {loads.moment if loads.moment else [0, 0, 0]}{suffix(bc)}",
                        linewidth=2.5,
                        linecolor=Color.red(),
                    )

            if not surface_loads:
                print("No surface loads defined in the problem boundary conditions.")
            else:
                surface_view = viewer.scene.add_group(name="Surface Loads")
                for bc, loads in surface_loads:
                    block = resolve_block(bc, loads.block_index, "Surface load")
                    if block is None:
                        continue
                    mesh = block.modelgeometry
                    face = loads.face_index
                    if face not in list(mesh.faces()):
                        print(f"Surface load on block {loads.block_index} references face_index={face}, which does not exist.{suffix(bc)}")
                        continue
                    load = Vector(*loads.load)
                    # The solver multiplies the traction by the face area to get the resultant.
                    resultant = load * mesh.face_area(face)
                    label = (
                        f"Surface Load: [{load.x:.1f}, {load.y:.1f}, {load.z:.1f}] on block {loads.block_index}, face {face} \n"
                        f" Resultant: [{resultant.x:.1f}, {resultant.y:.1f}, {resultant.z:.1f}]{suffix(bc)}"
                    )
                    surface_view.add(
                        mesh.face_polygon(face),
                        name=f"Loaded Face: block {loads.block_index}, face {face}{suffix(bc)}",
                        color=Color.cyan(),
                        opacity=0.5,
                    )
                    line = arrow(mesh.face_center(face), load, block_scale(block))
                    if line is not None:
                        surface_view.add(line, name=label, linewidth=2.5, linecolor=Color.cyan())

            if body_forces:
                # Body forces are global, so they are drawn once at the centre of the model.
                body_view = viewer.scene.add_group(name="Body Forces")
                origin = cg.centroid_points([list(block.point) for block in blocks.values()])
                scale = max(block_scale(block) for block in blocks.values()) if blocks else 1.0
                for bc, entry in body_forces:
                    vector = Vector(*entry.acceleration)
                    line = arrow(origin, vector, scale)
                    if line is None:
                        continue
                    body_view.add(
                        line,
                        name=f"Body Force: [{vector.x:.2f}, {vector.y:.2f}, {vector.z:.2f}] m/s² ({entry.loading_type}){suffix(bc)}",
                        linewidth=2.5,
                        linecolor=Color.orange(),
                    )

        if show_supports:
            # Supports live on the model (block.is_support); the boundary conditions
            # only hold prescribed movements.
            prescribed: list[tuple[BoundaryConditionGroup, dict]] = entries("displacements")

            support_blocks = [block for block in model.supports()]
            if not support_blocks:
                print("No supports defined in the model.")
            else:
                supports_view = viewer.scene.add_group(name="Supports")
                for block in support_blocks:
                    supports_view.add(
                        block.modelgeometry,
                        name=f"Support: block {block.graphnode}",
                        color=Color.red(),
                        opacity=0.5,
                    )

            if prescribed:
                prescribed_view = viewer.scene.add_group(name="Prescribed Displacements")
                for bc, entry in prescribed:
                    block = resolve_block(bc, entry.block_index, "Prescribed displacement")
                    if block is None:
                        continue
                    # Translation carries only `translation`, Rotation only `rotation`.
                    translation = getattr(entry, "translation", None)
                    rotation = getattr(entry, "rotation", None)
                    components = translation if translation is not None else rotation
                    if components is None:
                        continue
                    # Unconstrained components come through as None.
                    vector = Vector(*[c or 0.0 for c in components])
                    kind = "Displacement" if translation is not None else "Rotation"
                    units = "m" if translation is not None else "rad"
                    line = arrow(list(block.point), vector, block_scale(block))
                    if line is None:
                        continue
                    prescribed_view.add(
                        line,
                        name=f"Prescribed {kind}: {translation or rotation} {units} on block {entry.block_index}{suffix(bc)}",
                        linewidth=2.5,
                        linecolor=Color.violet(),
                    )

        blocks_view = viewer.scene.add_group(name="Blocks")

        for element in model.elements():
            block_view = viewer.scene.add_group(name=f"Block {element.graphnode}")
            if show_blocks:
                blocks_view.add(
                    element.modelgeometry,
                    opacity=0.25,
                    name=f"Block {element.graphnode}",
                    color=Color.grey(),
                )
            if face_indices:
                for idx in element.modelgeometry.faces():
                    block_view.add(
                        element.modelgeometry.face_polygon(idx),
                        name=f"Face {idx}",
                        color=Color.grey(),
                        opacity=0.25,
                    )
        viewer.show()

        if kill:
            raise ChildProcessError("Model inspection complete. Please comment out or remove the call to inspect_model(), or pass kill=False, to proceed.")

    # ============================================================================
    # Boundary conditions
    # ============================================================================

    def add_global_body_force(
        self,
        ax: float,
        ay: float,
        az: float,
        loading_type: str = "ramp",
        boundary_condition: BoundaryConditionGroup = None,
    ) -> None:
        """Add a global body acceleration applied to all blocks.

        The resultant force on each block is F = [ax, ay, az] * density * volume.

        Parameters
        ----------
        ax, ay, az : float
            Acceleration components in [m/s²].
        loading_type : str, optional
            Time-series shape used by the solver. ``"ramp"`` (default) ramps
            from zero to full over the simulation; ``"instantaneous"`` applies
            the full load at t=0 and releases it at the end.
        boundary_condition : :class:`BoundaryConditionGroup`
            The boundary condition to write to.

        .. note::
            This method takes acceleration components, not forces.
        """
        if boundary_condition is None:
            raise ValueError("No boundary condition specified. Please specify a boundary condition to add the global body force to.")
        boundary_condition.add_global_body_force(ax, ay, az, loading_type=loading_type)

    def add_point_load_at_vertex(
        self,
        block_index: int,
        vertex_index: int,
        force: list[float],
        loading_type: str = "ramp",
        boundary_condition: BoundaryConditionGroup = None,
    ) -> None:
        """Add a point load at a specific vertex of a block.

        Parameters
        ----------
        block_index : int
            Graph node index of the target block.
        vertex_index : int
            Index of the vertex on which to apply the load.
        force : list[float]
            Force vector [fx, fy, fz].
        loading_type : str, optional
            Time-series shape used by the solver. ``"ramp"`` (default) ramps
            from zero to full over the simulation; ``"instantaneous"`` applies
            the full load at t=0 and releases it at the end.
        boundary_condition : :class:`BoundaryConditionGroup`
            The boundary condition to write to.
        """
        if boundary_condition is None:
            raise ValueError("No boundary condition specified. Please specify a boundary condition to add the point load to.")
        block = self.model._block(block_index)
        try:
            point = block.modelgeometry.vertex_coordinates(vertex_index)
        except KeyError:
            raise ValueError(f"Block {block_index} does not have a vertex with index {vertex_index}.") from None
        boundary_condition.add_point_load(block_index, force, point=point, loading_type=loading_type)

    def add_point_load_at_face(
        self,
        block_index: int,
        face_index: int,
        force: list[float],
        loading_type: str = "ramp",
        boundary_condition: BoundaryConditionGroup = None,
    ) -> None:
        """Add a point load at the centroid of a specific face of a block.

        Parameters
        ----------
        block_index : int
            Graph node index of the target block.
        face_index : int
            Index of the face on which to apply the load.
        force : list[float]
            Force vector [fx, fy, fz].
        loading_type : str, optional
            Time-series shape used by the solver. ``"ramp"`` (default) ramps
            from zero to full over the simulation; ``"instantaneous"`` applies
            the full load at t=0 and releases it at the end.
        boundary_condition : :class:`BoundaryConditionGroup`
            The boundary condition to write to.
        """
        if boundary_condition is None:
            raise ValueError("No boundary condition specified. Please specify a boundary condition to add the point load to.")
        block = self.model._block(block_index)
        try:
            point = block.modelgeometry.face_center(face_index)
        except KeyError:
            raise ValueError(f"Block {block_index} does not have a face with index {face_index}.") from None
        boundary_condition.add_point_load(block_index, force, point=point, loading_type=loading_type)

    def add_point_load_at_point(
        self,
        block_index: int,
        point: list[float],
        force: list[float],
        loading_type: str = "ramp",
        boundary_condition: BoundaryConditionGroup = None,
    ) -> None:
        """Add a point load at an arbitrary point on a block.

        Parameters
        ----------
        block_index : int
            Graph node index of the target block.
        point : list[float]
            Application point [x, y, z]. The equivalent moment at the block centroid
            is resolved at solve time.
        force : list[float]
            Force vector [fx, fy, fz].
        loading_type : str, optional
            Time-series shape used by the solver. ``"ramp"`` (default) ramps
            from zero to full over the simulation; ``"instantaneous"`` applies
            the full load at t=0 and releases it at the end.
        boundary_condition : :class:`BoundaryConditionGroup`
            The boundary condition to write to.
        """
        if boundary_condition is None:
            raise ValueError("No boundary condition specified. Please specify a boundary condition to add the point load to.")
        self.model._block(block_index)
        boundary_condition.add_point_load(block_index, force, point=point, loading_type=loading_type)

    def add_point_load_at_centroid(
        self,
        block_index: int,
        force: list[float],
        loading_type: str = "ramp",
        boundary_condition: BoundaryConditionGroup = None,
    ) -> None:
        """Add a point load at the centroid of a block.

        Parameters
        ----------
        block_index : int
            Graph node index of the target block.
        force : list[float]
            Force vector [fx, fy, fz].
        loading_type : str, optional
            Time-series shape used by the solver. ``"ramp"`` (default) ramps
            from zero to full over the simulation; ``"instantaneous"`` applies
            the full load at t=0 and releases it at the end.
        boundary_condition : :class:`BoundaryConditionGroup`
            The boundary condition to write to.
        """
        if boundary_condition is None:
            raise ValueError("No boundary condition specified. Please specify a boundary condition to add the point load to.")
        self.model._block(block_index)
        boundary_condition.add_point_load(block_index, force, loading_type=loading_type)

    def add_moment(self, block_index: int, moment: list[float], loading_type: str = "ramp", boundary_condition: BoundaryConditionGroup = None) -> None:
        """Add a moment at the centroid of a block.

        Parameters
        ----------
        block_index : int
            Graph node index of the target block.
        moment : list[float]
            Moment vector [mx, my, mz].
        loading_type : str, optional
            Time-series shape used by the solver. ``"ramp"`` (default) ramps
            from zero to full over the simulation; ``"instantaneous"`` applies
            the full load at t=0 and releases it at the end.
        boundary_condition : :class:`BoundaryConditionGroup`, optional
            The boundary condition to write to. Defaults to the first (default) boundary condition.
        """
        if boundary_condition is None:
            raise ValueError("No boundary condition specified. Please specify a boundary condition to add the moment to.")
        boundary_condition.add_moment(block_index, moment=moment, loading_type=loading_type)

    def add_surface_load(
        self,
        block_index: int,
        face_index: int,
        load: list[float],
        loading_type: str = "ramp",
        boundary_condition: BoundaryConditionGroup = None,
    ) -> None:
        """Add a distributed pressure load over a block face.

        The equivalent centroidal force and moment are resolved at solve time
        using the model geometry.

        Parameters
        ----------
        block_index : int
            Graph node index of the target block.
        face_index : int
            Index of the face on which to apply the load.
        load : list[float]
            Load vector [fx, fy, fz].
        loading_type : str, optional
            ``"ramp"`` (default) or ``"instantaneous"``.
        boundary_condition : :class:`BoundaryConditionGroup`, optional
            The boundary condition to write to. Defaults to the first (default) boundary condition.
        """
        if boundary_condition is None:
            raise ValueError("No boundary condition specified. Please specify a boundary condition to add the surface load to.")
        boundary_condition.add_surface_load(block_index, face_index, load, loading_type)

    def add_displacement(
        self,
        block_index: int,
        displacement: Optional[list[float]] = None,
        boundary_condition: BoundaryConditionGroup = None,
    ) -> None:
        """Prescribe a displacement and/or rotation on a block.

        Parameters
        ----------
        block_index : int
            Node index of the target block.
        displacement : list[float], optional
            Translational displacement [dx, dy, dz] in [m].
        rotation : list[float], optional
            Rotation vector [rx, ry, rz] in [rad].
        boundary_condition : :class:`BoundaryConditionGroup`, optional
            The boundary condition to write to. Defaults to the first (default) boundary condition.
        """
        if boundary_condition is None:
            raise ValueError("No boundary condition specified. Please specify a boundary condition to add the displacement to.")
        if displacement is not None:
            boundary_condition.add_displacement(block_index, *displacement)

    def add_rotation(self, block_index: int, rotation: list[float], boundary_condition: BoundaryConditionGroup = None) -> None:
        """Prescribe a rotation on a block about its centroid.

        Parameters
        ----------
        block_index : int
            Node index of the target block.
        rotation : list[float]
            Rotation vector [rx, ry, rz] in [rad].
        boundary_condition : :class:`BoundaryConditionGroup`, optional
            The boundary condition to write to. Defaults to the first (default) boundary condition.
        """
        if boundary_condition is None:
            raise ValueError("No boundary condition specified. Please specify a boundary condition to add the rotation to.")
        boundary_condition.add_rotation(block_index, rotation)

    # =============================================================================
    # Contact properties
    # =============================================================================

    _CONTACT_MODELS: dict[str, type] = {
        "MohrCoulomb": MohrCoulomb,
    }

    def set_contact_model(self, model: str, **kwargs) -> None:
        """Set the contact model by name.

        Parameters
        ----------
        model : str
            Contact model type. Supported: ``"MohrCoulomb"``.
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

    def set_joint_model(self, kn: float, kt: float) -> None:
        """Set the joint stiffness model.

        Parameters
        ----------
        kn : float
            Normal stiffness [N/m].
        kt : float
            Tangential stiffness [N/m].
        """
        self._contact_properties.joint_model = JointModel(kn=kn, kt=kt)

    @property
    def contact_properties(self) -> ContactProperties:
        """The contact properties attached to this problem."""
        return self._contact_properties

    # =============================================================================
    # Solve
    # =============================================================================
    def set_solver(self, solver: Solver) -> None:
        self._solver = solver

    def solve(self):
        """Solve the problem on the loaded model using the configured solver.

        All boundary conditions registered on the problem are solved concurrently.
        To reorder them beforehand, call :meth:`set_solve_order`.

        Returns
        -------
        :class:`~compas_dem.problem.Results`

        Raises
        ------
        ValueError
            If no model is loaded, no solver is configured, or the solver name is not recognised.
        """
        model = self.model
        if self._solver is None:
            raise ValueError("No solver configured. Call problem.set_solver(Solver.LMGC90(...)) before solving.")
        self._check_model_validity(model)
        solver = self._solver
        params = {k: v for k, v in solver.parameters.items() if v is not None}
        if solver.name == "LMGC90":
            from compas_dem.analysis.lmgc90 import lmgc90_solve

            return lmgc90_solve(self, model, **params)
        elif solver.name in ("3DEC", "threeDEC"):
            from compas_dem.analysis.threedec import threedec_solve

            return threedec_solve(self, model, **params)
        elif solver.name == "CRA":
            from compas_dem.analysis.cra import cra_solve

            return cra_solve(self, model, **params)
        elif solver.name == "RBE":
            from compas_dem.analysis.cra import rbe_solve

            return rbe_solve(self, model, **params)
        elif solver.name == "PRD":
            from compas_dem.analysis.prd import prd_solve

            return prd_solve(self, model, **params)
        elif solver.name == "BLA":
            from compas_dem.analysis.bla import bla_solve

            return bla_solve(self, model, **params)
        else:
            raise ValueError(f"Solver '{solver.name}' is not recognised. Available: 'LMGC90', '3DEC', 'CRA', 'RBE', 'PRD', 'BLA'.")

    # ============================================================================
    # Validation
    # ============================================================================

    def _check_model_validity(self, model: BlockModel) -> None:
        """Check that the model is valid for solving.

        Parameters
        ----------
        model : :class:`compas_dem.models.BlockModel`

        Raises
        ------
        ValueError
            If the model is invalid.
        """
        if not any(element.is_support for element in model.elements()):
            raise ValueError("The model has no supports defined. Flag support blocks with block.is_support = True before solving.")
        if not self.contact_properties.contact_model:
            raise ValueError("No contact model defined. Please add a contact model before solving.")
