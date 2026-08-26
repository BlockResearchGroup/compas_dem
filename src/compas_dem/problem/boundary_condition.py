from typing import Optional

from compas.data import Data

LOADING_TYPES = ("ramp", "instantaneous")


def check_loading_type(loading_type: str) -> str:
    """Validate a loading type, returning it unchanged."""
    if loading_type not in LOADING_TYPES:
        raise ValueError(f"loading_type must be one of {LOADING_TYPES}, got {loading_type!r}.")
    return loading_type


class BoundaryCondition(Data):
    """Base class for a single boundary condition applied to a block model.

    A boundary condition is either a :class:`Load` or a :class:`Displacement`. This base
    class exists so both can be held together and told apart by type; it carries no load
    or displacement data of its own and is not meant to be instantiated directly.

    Boundary conditions that act simultaneously are collected in a
    :class:`BoundaryConditionGroup`, which is what a
    :class:`~compas_dem.problem.Problem` holds.

    Parameters
    ----------
    name : str, optional
        Name for this boundary condition.
    """

    def __init__(self, name: Optional[str] = None) -> None:
        super().__init__(name=name)


# =============================================================================
# Loads
# =============================================================================


class Load(BoundaryCondition):
    """Base class for applied loads.

    Every load carries a ``loading_type``, the time-series shape the solver gives it.

    Parameters
    ----------
    loading_type : str, optional
        Time-series shape used by the solver. ``"ramp"`` (default) ramps
        from zero to full over the simulation; ``"instantaneous"`` applies
        the full load at t=0 and releases it at the end.
    name : str, optional
        Name for this load.
    """

    def __init__(self, loading_type: str = "ramp", name: Optional[str] = None) -> None:
        super().__init__(name=name)
        self.loading_type = check_loading_type(loading_type)


class PointLoad(Load):
    """A concentrated force applied to a specific block.

    Built by :meth:`BoundaryConditionGroup.add_point_load`.

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
        centroid is resolved by :class:`~compas_dem.problem.Problem`.
        Cannot be combined with `moment`.
    loading_type : str, optional
        See :class:`Load`.
    name : str, optional
        Name for this load.

    Raises
    ------
    ValueError
        If both `moment` and `point` are provided.
    """

    def __init__(
        self,
        block_index: int,
        force: list[float],
        moment: Optional[list[float]] = None,
        point: Optional[list[float]] = None,
        loading_type: str = "ramp",
        name: Optional[str] = None,
    ) -> None:
        super().__init__(loading_type=loading_type, name=name)
        if moment is not None and point is not None:
            raise ValueError("Provide either `moment` or `point`, not both.")
        self.block_index = block_index
        self.force = force
        self.moment = moment
        self.point = point

    @property
    def __data__(self) -> dict:
        return {
            "block_index": self.block_index,
            "force": self.force,
            "moment": self.moment,
            "point": self.point,
            "loading_type": self.loading_type,
        }


class SurfaceLoad(Load):
    """A distributed pressure load over a block face.

    Built by :meth:`BoundaryConditionGroup.add_surface_load`.

    Parameters
    ----------
    block_index : int
        Graph node index of the target block.
    face_index : int
        Index of the face on which to apply the load.
    load : list[float]
        Load vector [fx, fy, fz].
    loading_type : str, optional
        See :class:`Load`.
    name : str, optional
        Name for this load.
    """

    def __init__(
        self,
        block_index: int,
        face_index: int,
        load: list[float],
        loading_type: str = "ramp",
        name: Optional[str] = None,
    ) -> None:
        super().__init__(loading_type=loading_type, name=name)
        self.block_index = block_index
        self.face_index = face_index
        self.load = load

    @property
    def __data__(self) -> dict:
        return {
            "block_index": self.block_index,
            "face_index": self.face_index,
            "load": self.load,
            "loading_type": self.loading_type,
        }


class BodyForce(Load):
    """A global body force applied to all blocks.

    The resultant force on each block is F = [ax, ay, az] * density * volume.

    Built by :meth:`BoundaryConditionGroup.add_global_body_force`.

    Parameters
    ----------
    acceleration : list[float]
        Acceleration components [ax, ay, az] in [m/s²].
    loading_type : str, optional
        See :class:`Load`.
    name : str, optional
        Name for this load.
    """

    def __init__(
        self,
        acceleration: list[float],
        loading_type: str = "ramp",
        name: Optional[str] = None,
    ) -> None:
        super().__init__(loading_type=loading_type, name=name)
        self.acceleration = acceleration

    @property
    def __data__(self) -> dict:
        return {
            "acceleration": self.acceleration,
            "loading_type": self.loading_type,
        }


class Gravity(Load):
    """Self-weight applied to all blocks using material density.

    Parameters
    ----------
    g : float, optional
        Gravitational acceleration in [m/s²]. Default 9.81.
    name : str, optional
        Name for this load.
    """

    def __init__(self, g: float = 9.81, name: Optional[str] = None) -> None:
        super().__init__(name=name)
        self.g = g

    @property
    def __data__(self) -> dict:
        return {"g": self.g}


# =============================================================================
# Displacement BCs
# =============================================================================


class Displacement(BoundaryCondition):
    """Base class for prescribed movements of a block.

    Parameters
    ----------
    block_index : int
        Graph node index of the target block.
    name : str, optional
        Name for this boundary condition.
    """

    def __init__(self, block_index: int, name: Optional[str] = None) -> None:
        super().__init__(name=name)
        self.block_index = block_index


class Translation(Displacement):
    """A prescribed translational displacement on a block, per component.

    Built by :meth:`BoundaryConditionGroup.add_displacement`.

    Parameters
    ----------
    block_index : int
        Graph node index of the target block.
    dx, dy, dz : float, optional
        Displacement components in [m]. ``None`` leaves that DOF unconstrained.
    name : str, optional
        Name for this boundary condition.
    """

    def __init__(
        self,
        block_index: int,
        dx: Optional[float] = None,
        dy: Optional[float] = None,
        dz: Optional[float] = None,
        name: Optional[str] = None,
    ) -> None:
        super().__init__(block_index=block_index, name=name)
        self.translation = [dx, dy, dz]

    @property
    def __data__(self) -> dict:
        return {
            "block_index": self.block_index,
            "translation": self.translation,
        }

    @classmethod
    def __from_data__(cls, data: dict) -> "Translation":
        dx, dy, dz = data["translation"]
        return cls(block_index=data["block_index"], dx=dx, dy=dy, dz=dz)


class Rotation(Displacement):
    """A prescribed rotation on a block about its centroid.

    Built by :meth:`BoundaryConditionGroup.add_rotation`.

    Parameters
    ----------
    block_index : int
        Graph node index of the target block.
    rotation : list[float]
        Rotation vector [rx, ry, rz] in [rad].
    name : str, optional
        Name for this boundary condition.
    """

    def __init__(
        self,
        block_index: int,
        rotation: list[float],
        name: Optional[str] = None,
    ) -> None:
        super().__init__(block_index=block_index, name=name)
        self.rotation = rotation

    @property
    def __data__(self) -> dict:
        return {
            "block_index": self.block_index,
            "rotation": self.rotation,
        }


# =============================================================================
# Group
# =============================================================================


class BoundaryConditionGroup(Data):
    """A named set of loads and displacement BCs applied together to a block model.

    A group collects the boundary conditions that act simultaneously. Build one up via
    method calls (either directly on the :class:`BoundaryConditionGroup`, or through
    :class:`~compas_dem.problem.Problem`), then register it on a problem with
    :meth:`~compas_dem.problem.Problem.add_boundary_condition`. A problem may hold
    several groups; the order in which they are solved is decided at solve time.

    Each ``add_*`` method builds the corresponding :class:`BoundaryCondition` subclass
    and stores it, so the group holds objects rather than plain dicts.

    Parameters
    ----------
    g : float, optional
        Gravitational acceleration in [m/s²]. Default 9.81.
    name : str, optional
        Name for this group.

    Examples
    --------
    >>> bc = BoundaryConditionGroup(name="Live")
    >>> point_load = bc.add_point_load(block_index=10, force=[0, 0, -5000])
    >>> len(bc.point_loads)
    1
    """

    def __init__(self, name: Optional[str] = None, g: float = 9.81, **kwargs) -> None:
        self._body_forces: list[BodyForce] = []
        self._point_loads: list[PointLoad] = []
        self._surface_loads: list[SurfaceLoad] = []
        self._displacements: list[Displacement] = []

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
    def __from_data__(cls, data: dict) -> "BoundaryConditionGroup":
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

    def add_global_body_force(self, ax: float, ay: float, az: float, loading_type: str = "ramp") -> BodyForce:
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

        Returns
        -------
        :class:`BodyForce`
        """
        body_force = BodyForce(acceleration=[ax, ay, az], loading_type=loading_type)
        self._body_forces.append(body_force)
        return body_force

    def add_point_load(
        self,
        block_index: int,
        force: list[float],
        moment: Optional[list[float]] = None,
        point: Optional[list[float]] = None,
        loading_type: str = "ramp",
    ) -> PointLoad:
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

        Returns
        -------
        :class:`PointLoad`

        Raises
        ------
        ValueError
            If both `moment` and `point` are provided.
        """
        point_load = PointLoad(
            block_index=block_index,
            force=force,
            moment=moment,
            point=point,
            loading_type=loading_type,
        )
        self._point_loads.append(point_load)
        return point_load

    def add_surface_load(
        self,
        block_index: int,
        face_index: int,
        load: list[float],
        loading_type: str = "ramp",
    ) -> SurfaceLoad:
        """Add a distributed pressure load over a block face.

        Parameters
        ----------
        block_index : int
            Graph node index of the target block.
        face_index : int
            Index of the face on which to apply the load.
        load : list[float]
            Load vector [fx, fy, fz].
        loading_type : str, optional
            Time-series shape used by the solver. ``"ramp"`` (default) ramps
            from zero to full over the simulation; ``"instantaneous"`` applies
            the full load at t=0 and releases it at the end.

        Returns
        -------
        :class:`SurfaceLoad`
        """
        surface_load = SurfaceLoad(
            block_index=block_index,
            face_index=face_index,
            load=load,
            loading_type=loading_type,
        )
        self._surface_loads.append(surface_load)
        return surface_load

    def add_moment(self, block_index: int, moment: list[float], loading_type: str = "ramp") -> PointLoad:
        """Add a concentrated moment to a specific block.

        Stored as a :class:`PointLoad` with no net force.

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

        Returns
        -------
        :class:`PointLoad`
        """
        point_load = PointLoad(
            block_index=block_index,
            force=[0.0, 0.0, 0.0],
            moment=moment,
            point=None,
            loading_type=loading_type,
        )
        self._point_loads.append(point_load)
        return point_load

    # =========================================================================
    # Displacement BCs
    # =========================================================================

    def add_displacement(
        self,
        block_index: int,
        dx: Optional[float] = None,
        dy: Optional[float] = None,
        dz: Optional[float] = None,
    ) -> Translation:
        """Prescribe a translational displacement on a block, per component.

        Parameters
        ----------
        block_index : int
            Graph node index of the target block.
        dx, dy, dz : float, optional
            Displacement components in [m]. ``None`` leaves that DOF unconstrained.

        Returns
        -------
        :class:`Translation`
        """
        translation = Translation(block_index=block_index, dx=dx, dy=dy, dz=dz)
        self._displacements.append(translation)
        return translation

    def add_rotation(self, block_index: int, rotation: list[float]) -> Rotation:
        """Prescribe a rotation on a block about its centroid.

        Parameters
        ----------
        block_index : int
            Graph node index of the target block.
        rotation : list[float]
            Rotation vector [rx, ry, rz] in [rad].

        Returns
        -------
        :class:`Rotation`
        """
        rotation_bc = Rotation(block_index=block_index, rotation=rotation)
        self._displacements.append(rotation_bc)
        return rotation_bc

    # =========================================================================
    # Access
    # =========================================================================

    @property
    def body_forces(self) -> list[BodyForce]:
        return self._body_forces

    @property
    def point_loads(self) -> list[PointLoad]:
        return self._point_loads

    @property
    def surface_loads(self) -> list[SurfaceLoad]:
        return self._surface_loads

    @property
    def displacements(self) -> list[Displacement]:
        return self._displacements
