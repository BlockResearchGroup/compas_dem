from typing import Optional

import compas.geometry as cg
from compas.colors import Color
from compas.data import Data
from compas.geometry import Vector
from compas_dem.interactions import ContactProperties
from compas_dem.interactions import JointModel
from compas_dem.interactions import MohrCoulomb
from compas_dem.models import BlockModel
from compas_dem.problem.loadcase import LoadCase
from compas_dem.problem.solvers import Solver

ZERO = [0.0, 0.0, 0.0]


def _is_support(entry: dict) -> bool:
    """Whether a displacement entry is a full fixity rather than a prescribed movement."""
    return entry["translation"] == ZERO and entry["rotation"] == ZERO


class Problem(Data):
    """Defines a structural problem over a block model.

    The problem is a lightweight data container — it stores boundary conditions
    and contact properties identified by ``model_id``, but holds no reference
    to the model itself. Pass the model explicitly when calling :meth:`solve`.

    Parameters
    ----------
    model : :class:`compas_dem.models.BlockModel`
        The discrete element model. Used only to extract ``model.guid``; not stored.
    name : str, optional
        Name of the problem.

    Examples
    --------
    >>> from compas_dem.models import BlockModel
    >>> model = BlockModel()
    >>> problem = Problem(model)
    >>> problem.add_gravity()
    >>> problem.add_support(block_index=0)  # doctest: +SKIP
    >>> result = problem.solve(solver="LMGC90", model=model)  # doctest: +SKIP
    """

    def __init__(self, model: BlockModel, name: Optional[str] = None, **kwargs) -> None:
        super().__init__(name=name)
        self.model_id = str(model.guid)
        self._loadcases: list[LoadCase] = []
        self._supports: list[int] = []
        self._contact_properties = ContactProperties()
        self._solver = None
        # The implicitly created "default" load case, while it is still untouched
        # apart from supports. Dropped as soon as a real load case is registered.
        self._auto_default: Optional[LoadCase] = None

    @property
    def __data__(self) -> dict:
        return {
            "name": self.name,
            "model_id": self.model_id,
            "supports": self._supports,
            "loadcases": self._loadcases,
            "contact_properties": self._contact_properties,
            "solver": self._solver,
        }

    @classmethod
    def __from_data__(cls, data: dict) -> "Problem":
        obj = cls.__new__(cls)
        Data.__init__(obj, name=data.get("name"))
        obj.model_id = data["model_id"]
        obj._loadcases = list(data.get("loadcases", []))
        obj._supports = list(data.get("supports", []))
        obj._contact_properties = data["contact_properties"]
        obj._solver = data["solver"]
        # A deserialized problem has explicit load cases; nothing to auto-drop.
        obj._auto_default = None
        return obj

    # ============================================================================
    # Load cases
    # ============================================================================

    def _default_loadcase(self) -> LoadCase:
        """Return the first load case, creating an empty default one if needed.

        Adding a load directly from the problem, without specifying a load case,
        will write to the default load case.
        This is for backward compatibility with code that predates load cases, and
        convieniece for simple problems.

        """
        if not self._loadcases:
            loadcase = LoadCase(name="default")
            for block_index in self._supports:
                loadcase.add_support(block_index)
            self._loadcases.append(loadcase)
            self._auto_default = loadcase
        return self._loadcases[0]

    def _resolve_target(self, loadcase: Optional[LoadCase]) -> LoadCase:
        """Return the load case a convenience ``add_*`` call should write to.

        ``None`` targets the default (first) load case. A :class:`LoadCase` must
        already be registered on this problem via :meth:`add_loadcase`.
        """
        if loadcase is None:
            return self._default_loadcase()
        if not any(lc is loadcase for lc in self._loadcases):
            raise ValueError("The given load case is not registered on this problem. Call problem.add_loadcase(loadcase) first.")
        return loadcase

    def add_loadcase(self, loadcase: LoadCase) -> int:
        """Register a load case on the problem.

        The problem's supports are copied into the load case, so add them with
        :meth:`add_support` before registering any load case.

        Parameters
        ----------
        loadcase : :class:`LoadCase`
            The load case to append. It is stored by reference, so its ``guid``
            is preserved and later edits to the object are reflected here.

        Returns
        -------
        int
            The index of the newly added load case.
        """
        for block_index in self._supports:
            loadcase.add_support(block_index)

        if self._auto_default is not None:
            self._loadcases[0] = loadcase
            self._auto_default = None
            index = 0
        else:
            self._loadcases.append(loadcase)
            index = len(self._loadcases) - 1

        return index

    @property
    def loadcases(self) -> list[LoadCase]:
        """The ordered list of load cases attached to this problem."""
        return self._loadcases

    @property
    def loadcase(self) -> list[LoadCase]:
        """Alias for :attr:`loadcases`; supports ``problem.loadcase[i]`` indexing."""
        return self._loadcases

    # ============================================================================
    # Pre-visualization utilities
    # ============================================================================

    def inspect_model(
        self,
        model: BlockModel,
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
        corresponding entries exist in at least one of the problem's load cases.

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
        if not grid:
            viewer.config.renderer.show_grid = False

        blocks = {block.graphnode: block for block in model.elements()}
        multiple_loadcases = len(self._loadcases) > 1

        def suffix(loadcase: LoadCase) -> str:
            """Disambiguate entries by load case, but only when there is more than one."""
            return f"  [{loadcase.name or '<unnamed>'}]" if multiple_loadcases else ""

        def block_scale(block) -> float:
            return block.modelgeometry.edge_length([0, 1]) / 2

        def arrow(point, vector: Vector, scale: float) -> Optional[cg.Line]:
            """A line running from ``point`` back along ``vector``, i.e. pointing at ``point``."""
            if vector.length == 0:
                return None
            return cg.Line(point, [p - v for p, v in zip(point, vector.unitized() * scale)])

        def entries(attr: str) -> list[tuple[LoadCase, object]]:
            """Flatten one kind of entry across all load cases, keeping its origin."""
            return [(lc, entry) for lc in self._loadcases for entry in getattr(lc, attr)]

        def resolve_block(loadcase: LoadCase, index: int, kind: str):
            """Look up a block, warning instead of raising so inspection still runs."""
            if index not in blocks:
                print(f"{kind} references block_index={index}, which does not exist in the model.{suffix(loadcase)}")
                return None
            return blocks[index]

        if show_loads:
            point_loads = entries("point_loads")
            surface_loads = entries("surface_loads")
            body_forces = entries("body_forces")

            if not point_loads:
                print("No point loads defined in the problem load cases.")
            else:
                loads_view = viewer.scene.add_group(name="Point Loads")
                for lc, loads in point_loads:
                    block = resolve_block(lc, loads["block_index"], "Point load")
                    if block is None:
                        continue
                    force = Vector(*loads["force"])
                    point = loads["point"] if loads["point"] is not None else list(block.point)
                    line = arrow(point, force, block_scale(block))
                    if line is None:
                        continue
                    loads_view.add(
                        line,
                        name=f"Point Load: [{force.x:.1f}, {force.y:.1f}, {force.z:.1f}] \n Moment: {loads['moment'] if loads['moment'] else [0, 0, 0]}{suffix(lc)}",
                        linewidth=2.5,
                        linecolor=Color.red(),
                    )

            if not surface_loads:
                print("No surface loads defined in the problem load cases.")
            else:
                surface_view = viewer.scene.add_group(name="Surface Loads")
                for lc, loads in surface_loads:
                    block = resolve_block(lc, loads["block_index"], "Surface load")
                    if block is None:
                        continue
                    mesh = block.modelgeometry
                    face = loads["face_index"]
                    if face not in list(mesh.faces()):
                        print(f"Surface load on block {loads['block_index']} references face_index={face}, which does not exist.{suffix(lc)}")
                        continue
                    load = Vector(*loads["load"])
                    # The solver multiplies the traction by the face area to get the resultant.
                    resultant = load * mesh.face_area(face)
                    label = (
                        f"Surface Load: [{load.x:.1f}, {load.y:.1f}, {load.z:.1f}] on block {loads['block_index']}, face {face} \n"
                        f" Resultant: [{resultant.x:.1f}, {resultant.y:.1f}, {resultant.z:.1f}]{suffix(lc)}"
                    )
                    surface_view.add(
                        mesh.face_polygon(face),
                        name=f"Loaded Face: block {loads['block_index']}, face {face}{suffix(lc)}",
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
                for lc, acceleration in body_forces:
                    vector = Vector(*acceleration)
                    line = arrow(origin, vector, scale)
                    if line is None:
                        continue
                    body_view.add(
                        line,
                        name=f"Body Force: [{vector.x:.2f}, {vector.y:.2f}, {vector.z:.2f}] m/s²{suffix(lc)}",
                        linewidth=2.5,
                        linecolor=Color.orange(),
                    )

        if show_supports:
            # Supports live on the problem, so they are drawn once rather than
            # once per load case. Everything left in the load cases is a
            # prescribed movement.
            prescribed: list[tuple[LoadCase, dict]] = [(lc, entry) for lc, entry in entries("displacements") if not _is_support(entry)]

            if not self._supports:
                print("No supports defined in the problem.")
            else:
                supports_view = viewer.scene.add_group(name="Supports")
                for block_index in self._supports:
                    if block_index not in blocks:
                        print(f"Support references block_index={block_index}, which does not exist in the model.")
                        continue
                    supports_view.add(
                        blocks[block_index].modelgeometry,
                        name=f"Support: block {block_index}",
                        color=Color.red(),
                        opacity=0.5,
                    )

            if prescribed:
                prescribed_view = viewer.scene.add_group(name="Prescribed Displacements")
                for lc, entry in prescribed:
                    block = resolve_block(lc, entry["block_index"], "Prescribed displacement")
                    if block is None:
                        continue
                    translation = entry["translation"]
                    rotation = entry["rotation"]
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
                        name=f"Prescribed {kind}: {translation or rotation} {units} on block {entry['block_index']}{suffix(lc)}",
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

    def add_gravity(self, g: float = 9.81, loadcase: Optional[LoadCase] = None) -> None:
        """Changes applied gravity in a load case.

        Parameters
        ----------
        g : float, optional
            Gravitational acceleration in [m/s²]. Default 9.81.
        loadcase : :class:`LoadCase`, optional
            The load case to write to. Must already be registered via
            :meth:`add_loadcase`. Defaults to the first (default) load case.
        """
        self._resolve_target(loadcase).add_gravity(g)

    def add_global_body_force(self, ax: float, ay: float, az: float, loadcase: Optional[LoadCase] = None) -> None:
        """Add a global body acceleration applied to all blocks.

        The resultant force on each block is F = [ax, ay, az] * density * volume.

        Parameters
        ----------
        ax, ay, az : float
            Acceleration components in [m/s²].
        loadcase : :class:`LoadCase`, optional
            The load case to write to. Defaults to the first (default) load case.

        .. note::
            This method takes acceleration components, not forces.
        """
        self._resolve_target(loadcase).add_global_body_force(ax, ay, az)

    def add_point_load(
        self,
        block_index: int,
        force: list[float],
        moment: Optional[list[float]] = None,
        point: Optional[list[float]] = None,
        loading_type: str = "ramp",
        loadcase: Optional[LoadCase] = None,
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
            centroid is resolved at solve time.
            If ``None``, the load is applied at the block centroid (zero moment).
            Cannot be combined with `moment`.
        loading_type : str, optional
            ``"ramp"`` (default) or ``"instantaneous"``.
        loadcase : :class:`LoadCase`, optional
            The load case to write to. Defaults to the first (default) load case.
        """
        self._resolve_target(loadcase).add_point_load(block_index, force, moment, point, loading_type)

    def add_surface_load(
        self,
        block_index: int,
        face_index: int,
        load: list[float],
        loading_type: str = "ramp",
        loadcase: Optional[LoadCase] = None,
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
        loadcase : :class:`LoadCase`, optional
            The load case to write to. Defaults to the first (default) load case.
        """
        self._resolve_target(loadcase).add_surface_load(block_index, face_index, load, loading_type)

    def add_displacement(
        self,
        block_index: int,
        displacement: Optional[list[float]] = None,
        rotation: Optional[list[float]] = None,
        loadcase: Optional[LoadCase] = None,
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
        loadcase : :class:`LoadCase`, optional
            The load case to write to. Defaults to the first (default) load case.
        """
        target = self._resolve_target(loadcase)
        if displacement is not None:
            target.add_displacement(block_index, *displacement)
        if rotation is not None:
            target.add_rotation(block_index, rotation)

    def add_rotation(self, block_index: int, rotation: list[float], loadcase: Optional[LoadCase] = None) -> None:
        """Prescribe a rotation on a block about its centroid.

        Parameters
        ----------
        block_index : int
            Node index of the target block.
        rotation : list[float]
            Rotation vector [rx, ry, rz] in [rad].
        loadcase : :class:`LoadCase`, optional
            The load case to write to. Defaults to the first (default) load case.
        """
        self._resolve_target(loadcase).add_rotation(block_index, rotation)

    def add_support(self, block_index: int) -> None:
        """Fix a block — zero translation and zero rotation.

        Supports belong to the model rather than to any one loading, so they are
        kept on the problem and copied into each load case as it is registered.
        Add them before any call to :meth:`add_loadcase`.

        Parameters
        ----------
        block_index : int
            Node index of the block to fix.
        """
        self._supports.append(block_index)

    def add_supports(self, block_indices: list[int]) -> None:
        """Fix multiple blocks — zero translation and zero rotation.

        Parameters
        ----------
        block_indices : list[int]
            List of node indices of the blocks to fix.
        """
        for block_index in block_indices:
            self.add_support(block_index)

    @property
    def supports(self) -> list[int]:
        """The node indices of the fixed blocks, copied into every load case."""
        return self._supports

    def add_supports_from_model(self, model: BlockModel) -> None:
        """Fix all blocks whose ``is_support`` flag is ``True`` in the block model.

        Parameters
        ----------
        model : :class:`compas_dem.models.BlockModel`
        """
        for block in model.elements():
            if getattr(block, "is_support", False):
                self.add_support(block.graphnode)

    def add_bc(self, bc: LoadCase) -> None:
        """Merge a pre-built load case's contents into the default load case.

        Retained for backward compatibility. To keep a load case as its own
        entry instead of flattening it in, use :meth:`add_loadcase`.

        Parameters
        ----------
        bc : :class:`LoadCase`
            A load case whose contents to absorb.
        """
        target = self._default_loadcase()
        for acc in bc.body_forces:
            target.add_global_body_force(*acc)
        for entry in bc.point_loads:
            target.add_point_load(**entry)
        for entry in bc.surface_loads:
            target.add_surface_load(entry["block_index"], entry["face_index"], entry["load"], entry["loading_type"])
        for entry in bc.displacements:
            target._displacements.append(entry)

    @property
    def boundary_conditions(self) -> LoadCase:
        """The default (first) load case.

        .. deprecated::
            Retained only as a compatibility read for code that predates load
            cases. Prefer :attr:`loadcases`. Returns (creating if needed) the
            first load case; it is never a separate scalar container.
        """
        return self._default_loadcase()

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

    def add_joint_model(self, kn: float, kt: float) -> None:
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
    def solver(self, solver: Solver) -> None:
        self._solver = solver

    # ============================================================================
    # Validation
    # ============================================================================

    def check_model_validity(self, model: BlockModel) -> None:
        """Check that the model is valid for solving.

        Parameters
        ----------
        model : :class:`compas_dem.models.BlockModel`

        Raises
        ------
        ValueError
            If the model is invalid.
        """
        has_supports = bool(self._supports) or any(element.is_support for element in model.elements())
        if not has_supports:
            raise ValueError("The model has no supports defined. Please add supports before solving.")
        if not self.contact_properties.contact_model:
            raise ValueError("No contact model defined. Please add a contact model before solving.")
