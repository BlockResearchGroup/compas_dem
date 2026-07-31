from typing import Optional

from compas.data import Data

LOADING_TYPES = ("ramp", "instantaneous")


def check_loading_type(loading_type: str) -> str:
    """Validate a loading type, returning it unchanged."""
    if loading_type not in LOADING_TYPES:
        raise ValueError(f"loading_type must be one of {LOADING_TYPES}, got {loading_type!r}.")
    return loading_type


class BoundaryCondition(Data):
    """A named set of loads and displacement BCs applied together to a block model.

    A boundary condition groups loads that act simultaneously. Build one up via method
    calls (either directly on the :class:`BoundaryCondition`, or through
    :class:`~compas_dem.problem.Problem`), then register it on a problem with
    :meth:`~compas_dem.problem.Problem.add_boundary_condition`. A problem may hold several
    boundary conditions; the order in which they are solved is decided at solve time.

    Parameters
    ----------
    g : float, optional
        Gravitational acceleration in [m/s²]. Default 9.81.
    name : str, optional
        Name for this boundary condition.

    Examples
    --------
    >>> bc = BoundaryCondition(name="Live")
    >>> bc.add_point_load(block_index=10, force=[0, 0, -5000])
    """

    def __init__(self, name: Optional[str] = None, g: float = 9.81, **kwargs) -> None:
        self._body_forces: list[dict] = []
        self._point_loads: list[dict] = []
        self._surface_loads: list[dict] = []
        self._displacements: list[dict] = []

        super().__init__(name=name)

        self.g = g

    @property
    def __data__(self) -> dict:
        return {
            "name": self.name,
            "g": self.g,
            "body_forces": self._body_forces,
            "point_loads": self._point_loads,
            "surface_loads": self._surface_loads,
            "displacements": self._displacements,
        }

    @classmethod
    def __from_data__(cls, data: dict) -> "BoundaryCondition":
        obj = cls(
            g=data["g"],
            name=data.get("name"),
        )
        # Body forces used to be stored as bare [ax, ay, az] lists, before they carried
        # a loading type; normalise so older files keep loading.
        obj._body_forces = [entry if isinstance(entry, dict) else {"acceleration": list(entry), "loading_type": "ramp"} for entry in data["body_forces"]]
        obj._point_loads = data["point_loads"]
        obj._surface_loads = data["surface_loads"]
        obj._displacements = data["displacements"]
        return obj

    # =========================================================================
    # Forces
    # =========================================================================
    def add_gravity(self, g: float = 9.81) -> None:
        """Apply self-weight to all blocks using material density.

        Parameters
        ----------
        g : float, optional
            Gravitational acceleration in [m/s²]. Default 9.81.
        """
        self.g = g

    def add_global_body_force(self, ax: float, ay: float, az: float, loading_type: str = "ramp") -> None:
        """Add a global body force applied to all blocks, as a ratio of gravitational acceleration.

        The resultant force on each block is F = [ax, ay, az] * density * volume.

        Parameters
        ----------
        ax, ay, az : float
            Acceleration components in [m/s²].
        loading_type : str, optional
            Time-series shape used by the solver. ``"ramp"`` (default) ramps
            from zero to full over the simulation; ``"instantaneous"`` applies
            the full load at t=0 and releases it at the end.
        """
        self._body_forces.append(
            {
                "acceleration": [ax, ay, az],
                "loading_type": check_loading_type(loading_type),
            }
        )

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
            centroid is resolved by :class:`Problem`.
            Cannot be combined with `moment`.
        loading_type : str, optional
            Time-series shape used by the solver. ``"ramp"`` (default) ramps
            from zero to full over the simulation; ``"instantaneous"`` applies
            the full load at t=0 and releases it at the end.

        Raises
        ------
        ValueError
            If both `moment` and `point` are provided.
        """
        if moment is not None and point is not None:
            raise ValueError("Provide either `moment` or `point`, not both.")
        self._point_loads.append(
            {
                "block_index": block_index,
                "force": force,
                "moment": moment,
                "point": point,
                "loading_type": check_loading_type(loading_type),
            }
        )

    def add_surface_load(
        self,
        block_index: int,
        face_index: int,
        load: list[float],
        loading_type: str = "ramp",
    ) -> None:
        """Add a distributed pressure load over a block face.

        Parameters
        ----------
        block_index : int
            Graph node index of the target block.
        face_index : int
            Index of the face on which to apply the load.
        load : list[float]
            Load vector [fx, fy, fz].
        direction : list[float], optional
            Unit vector [dx, dy, dz]. If ``None``, the polygon outward normal is used.
        loading_type : str, optional
            Time-series shape used by the solver. ``"ramp"`` (default) ramps
            from zero to full over the simulation; ``"instantaneous"`` applies
            the full load at t=0 and releases it at the end.
        """
        self._surface_loads.append(
            {
                "block_index": block_index,
                "face_index": face_index,
                "load": load,
                "loading_type": check_loading_type(loading_type),
            }
        )

    def add_moment(self, block_index: int, moment: list[float], loading_type: str = "ramp") -> None:
        """Add a concentrated moment to a specific block.

        Parameters
        ----------
        block_index : int
            Graph node index of the target block.
        moment : list[float]
            Moment vector [mx, my, mz] applied at the centroid.
        loading_type : str, optional
            Time-series shape used by the solver. ``"ramp"`` (default) ramps
            from zero to full over the simulation; ``"instantaneous"`` applies
            the full load at t=0 and releases it at the end.
        """
        self._point_loads.append(
            {
                "block_index": block_index,
                "force": [0.0, 0.0, 0.0],
                "moment": moment,
                "point": None,
                "loading_type": check_loading_type(loading_type),
            }
        )

    # =========================================================================
    # Displacement BCs
    # =========================================================================

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
            Graph node index of the target block.
        dx, dy, dz : float, optional
            Displacement components in [m]. ``None`` leaves that DOF unconstrained.
        """
        self._displacements.append(
            {
                "block_index": block_index,
                "translation": [dx, dy, dz],
                "rotation": None,
            }
        )

    def add_rotation(self, block_index: int, rotation: list[float]) -> None:
        """Prescribe a rotation on a block about its centroid.

        Parameters
        ----------
        block_index : int
            Graph node index of the target block.
        rotation : list[float]
            Rotation vector [rx, ry, rz] in [rad].
        """
        self._displacements.append(
            {
                "block_index": block_index,
                "translation": None,
                "rotation": rotation,
            }
        )

    # =========================================================================
    # Access
    # =========================================================================

    @property
    def body_forces(self) -> list[list[float]]:
        return self._body_forces

    @property
    def point_loads(self) -> list[dict]:
        return self._point_loads

    @property
    def surface_loads(self) -> list[dict]:
        return self._surface_loads

    @property
    def displacements(self) -> list[dict]:
        return self._displacements


class Load(BoundaryCondition):
    pass


class Displacement(BoundaryCondition):
    pass


class PointLoad(Load):
    @classmethod
    def at_vertex(cls, block_index: int, vertex_index: int, force: list[float], bc: BoundaryCondition) -> None:
        """Add a point load at a specific vertex of a block."""
        bc.add_point_load(block_index=block_index, force=force, point=vertex_index)


class SurfaceLoad(Load):
    pass


class Gravity(Load):
    pass


class BodyForce(Load):
    pass


class Rotation(Displacement):
    pass


class Translation(Displacement):
    pass


# load = Load.Surface_load(load=(0, 0, -10000))
# point_load = Load.Point_load(block_index=10, force=[0, 0, -100000])

# problem.add_point_load(block_index=10, force=[0, 0, -100000])
# PointLoad.at_vertex()
# PointLoad.at_face()
# PointLoad.at_point()
# PointLoad.at_block()

# problem.add_point_load(block_index=10, force=[0, 0, -100000], point or a face index or a vertex index if none then centroid)

# bc1 = problem.add_boundary_condition(name="Mixed")

# problem.add_point_load_at_vertex(block_index=10, vertex_index=5, force=[0, 0, -100000], bc=bc1)
# problem.add_point_load_at_face(block_index=10, face_index=2, force=[0, 0, -100000], bc=bc1)
# problem.add_point_load_at_point(block_index=10, point=[1, 2, 3], force=[0, 0, -100000], bc=bc1)
# problem.add_point_load_at_block(block_index=10, force=[0, 0, -100000], bc=bc1)  # default to centroid
# problem.add_moment_at_block(block_index=10, moment=[0, 0, -100000], bc=bc1)  # default to centroid
# problem.add_surface_load(block_index=10, face_index=2, load=[0, 0, -10000], bc=bc1)
# problem.add_displacement(block_index=10, displacement=[0.1, 0, 0], bc=bc1)
# problem.add_rotation(block_index=10, rotation=[0, 0, 0.1], bc=bc1)

# bc1.loads.point_loads


# def add_point_load_at_vertex(self, block_index: int, vertex_index: int, force: list[float], bc: BoundaryCondition) -> None:
#     """Add a point load at a specific vertex of a block."""
#     pl = PointLoad.at_vertex(block_index=block_index, vertex_index=vertex_index, force=force, bc=bc)
#     boundary_condition.add_point_load(pl)
#     return pl
