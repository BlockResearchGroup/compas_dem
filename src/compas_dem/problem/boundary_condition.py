from typing import Optional

from compas.data import Data


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
    >>> bc.add_support(block_index=0)
    >>> bc.add_support(block_index=99)
    """

    def __init__(self, name: Optional[str] = None, g: float = 9.81, **kwargs) -> None:
        self._body_forces: list[list[float]] = []
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
        obj._body_forces = data["body_forces"]
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

    def add_global_body_force(self, ax: float, ay: float, az: float) -> None:
        """Add a global body acceleration applied to all blocks.

        The resultant force on each block is F = [ax, ay, az] * density * volume.

        Parameters
        ----------
        ax, ay, az : float
            Acceleration components in [m/s²].
        """
        self._body_forces.append([ax, ay, az])

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
        if loading_type not in ("ramp", "instantaneous"):
            raise ValueError("loading_type must be 'ramp' or 'instantaneous'.")
        self._point_loads.append(
            {
                "block_index": block_index,
                "force": force,
                "moment": moment,
                "point": point,
                "loading_type": loading_type,
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
                "loading_type": loading_type,
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

    def add_support(self, block_index: int) -> None:
        """Fix a block — zero translation and zero rotation.

        Parameters
        ----------
        block_index : int
            Graph node index of the block to fix.
        """
        self._displacements.append(
            {
                "block_index": block_index,
                "translation": [0.0, 0.0, 0.0],
                "rotation": [0.0, 0.0, 0.0],
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
