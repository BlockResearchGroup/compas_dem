from typing import Optional

from compas.data import Data
from compas.geometry import Polygon


class BoundaryConditions(Data):
    """Container for all forces and displacement BCs applied to a block model.

    Build up conditions via method calls, then pass to :class:`Problem` via
    :meth:`~compas_dem.problem.Problem.apply_bc`.

    Parameters
    ----------
    gravity : bool, optional
        Apply self-weight to all blocks using material density. Default False.
    g : float, optional
        Gravitational acceleration in [m/s²]. Default 9.81.
    name : str, optional
        Name for this boundary condition set.

    Examples
    --------
    >>> bc = BoundaryConditions(gravity=True)
    >>> bc.add_point_load(block_index=10, force=[0, 0, -5000])
    >>> bc.add_fixed(block_index=0)
    >>> bc.add_fixed(block_index=99)
    """

    def __init__(
        self,
        gravity: bool = False,
        g: float = 9.81,
        name: Optional[str] = None,
    ) -> None:
        super().__init__(name=name)
        self.gravity = gravity
        self.g = g
        self._body_forces: list[list[float]] = []
        self._point_loads: list[dict] = []
        self._surface_loads: list[dict] = []
        self._displacements: list[dict] = []

    # =========================================================================
    # Forces
    # =========================================================================
    def add_gravity(self, g: float = 9.81) -> "BoundaryConditions":
        """Apply self-weight to all blocks using material density.

        Parameters
        ----------
        g : float, optional
            Gravitational acceleration in [m/s²]. Default 9.81.
        """
        self.gravity = True
        self.g = g
        return self

    def add_global_body_force(self, ax: float, ay: float, az: float) -> "BoundaryConditions":
        """Add a global body acceleration applied to all blocks.

        The resultant force on each block is F = [ax, ay, az] * density * volume.

        Parameters
        ----------
        ax, ay, az : float
            Acceleration components in [m/s²].
        """
        self._body_forces.append([ax, ay, az])
        return self

    def add_point_load(
        self,
        block_index: int,
        force: list[float],
        moment: Optional[list[float]] = None,
        point: Optional[list[float]] = None,
        loading_type: str = "ramp",
    ) -> "BoundaryConditions":
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
        return self

    def add_surface_load(
        self,
        block_index: int,
        polygon: Polygon,
        magnitude: float,
        direction: Optional[list[float]] = None,
    ) -> "BoundaryConditions":
        """Add a distributed pressure load over a polygon on a block face.

        Parameters
        ----------
        block_index : int
            Graph node index of the target block.
        polygon : :class:`compas.geometry.Polygon`
            The loaded face polygon picked from the block surface.
        magnitude : float
            Pressure magnitude in [N/m²].
        direction : list[float], optional
            Unit vector [dx, dy, dz]. If ``None``, the polygon outward normal is used.
        """
        self._surface_loads.append(
            {
                "block_index": block_index,
                "polygon": polygon,
                "magnitude": magnitude,
                "direction": direction,
            }
        )
        return self

    # =========================================================================
    # Displacement BCs
    # =========================================================================

    def add_displacement(self, block_index: int, displacement: list[float]) -> "BoundaryConditions":
        """Prescribe a translational displacement on a block.

        Parameters
        ----------
        block_index : int
            Graph node index of the target block.
        displacement : list[float]
            Translation vector [dx, dy, dz] in [m].
        """
        self._displacements.append(
            {
                "block_index": block_index,
                "translation": displacement,
                "rotation": None,
            }
        )
        return self

    def add_rotation(self, block_index: int, rotation: list[float]) -> "BoundaryConditions":
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
        return self

    def add_fixed(self, block_index: int) -> "BoundaryConditions":
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
        return self

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

    # =========================================================================
    # Serialization
    # =========================================================================

    @property
    def __data__(self) -> dict:
        return {
            "name": self.name,
            "gravity": self.gravity,
            "g": self.g,
            "body_forces": self._body_forces,
            "point_loads": self._point_loads,
            "surface_loads": self._surface_loads,
            "displacements": self._displacements,
        }
