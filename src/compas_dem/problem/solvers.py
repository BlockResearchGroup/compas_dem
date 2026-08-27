from typing import Optional

from compas.data import Data


def _validate_threedec_stages(stages):
    """Return a normalized 3DEC boundary-condition stage plan."""
    if not isinstance(stages, (list, tuple)) or not stages:
        raise ValueError("3DEC stages must be a non-empty sequence of stages.")
    normalized = []
    used = set()
    for index, stage in enumerate(stages, start=1):
        if not isinstance(stage, (list, tuple)) or not stage:
            raise ValueError("3DEC stage {} must contain at least one boundary-condition name.".format(index))
        names = []
        for name in stage:
            name = str(name).strip()
            if not name:
                raise ValueError("3DEC stage names cannot be empty.")
            if name in used:
                raise ValueError("Boundary condition {!r} occurs in more than one 3DEC stage.".format(name))
            used.add(name)
            names.append(name)
        normalized.append(names)
    return normalized


class Solver(Data):
    """Container for solver configuration. Call one of the solver methods to set it up.

    Examples
    --------
    >>> s = Solver()
    >>> _ = s.LMGC90(duration=1.0, n_steps=100)
    >>> _ = s.CRA(d_bnd=0.001, eps=0.0001)
    """

    def __init__(self):
        super().__init__()
        self.name = None
        self.parameters = {}

    def __repr__(self):
        return f"Solver(name={self.name}, parameters={self.parameters})"

    @property
    def __data__(self):
        return {"name": self.name, "parameters": self.parameters}

    @classmethod
    def __from_data__(cls, data: dict) -> "Solver":
        # Solver.__init__ takes no arguments and the factory classmethods
        # (LMGC90/CRA/...) set name+parameters, so reconstruct by hand rather
        # than the default cls(**data).
        obj = cls()
        obj.name = data["name"]
        obj.parameters = data["parameters"]
        return obj

    @classmethod
    def LMGC90(
        cls,
        duration: Optional[float] = None,
        n_steps: Optional[int] = None,
        dt: Optional[float] = None,
        theta: float = 0.5,
        urf_threshold: Optional[float] = None,
        track_block: Optional[int] = None,
        verbose: int = 1000,
    ):
        """
        LMGC90 solver configuration.

        Parameters
        ----------
        duration : float, Optional
            Total duration of the simulation in seconds.
        n_steps : int, Optional
            Number of time steps to simulate.
        dt : float, Optional
            Time step size. If None, it will be computed automatically based on the model properties.
        theta : float
            Time integration parameter (0.5 for mid-point rule, 1.0 for backward Euler).
        urf_threshold : float, Optional
            Unbalanced force threshold for convergence. If None, it will be set to a default value based on the model.
        track_block : int, Optional
            Optional block index to track and print its displacement/rotation during the simulation.
        """
        self = cls()
        self.name = "LMGC90"
        self.parameters = {
            "duration": duration,
            "n_steps": n_steps,
            "dt": dt,
            "theta": theta,
            "urf_threshold": urf_threshold,
            "track_block": track_block,
            "verbose": verbose,
        }
        return self

    @classmethod
    def ThreeDEC(
        cls,
        version: str = "7.0",
        executable: Optional[str] = None,
        workspace: Optional[str] = None,
        arguments: Optional[list[str]] = None,
        ratio: float = 1e-5,
        ratio_keyword: str = "ratio-local",
        time: float = 1.0,
        gravity_steps: int = 10,
        suppress_output: bool = True,
        timeout: Optional[float] = None,
        gridpoint_tolerance: float = 1e-6,
        stages: Optional[list[list[str]]] = None,
    ):
        """Configure the solver provided by ``compas_3dec``.

        Analysis parameters are copied into the portable prepared analysis by
        ``compas_3dec``. Executable and workspace settings are used only by the
        runtime solver and are filtered from that prepared snapshot.
        """
        self = cls()
        self.name = "3DEC"
        self.parameters = {
            "version": version,
            "executable": executable,
            "workspace": workspace,
            "arguments": arguments,
            "ratio": ratio,
            "ratio_keyword": ratio_keyword,
            "time": time,
            "gravity_steps": gravity_steps,
            "suppress_output": suppress_output,
            "timeout": timeout,
            "gridpoint_tolerance": gridpoint_tolerance,
            "stages": _validate_threedec_stages(stages) if stages is not None else None,
        }
        return self

    def set_stages(self, stages):
        """Set the ordered 3DEC load-stage grouping.

        Names in the same stage are synchronized in one 3DEC DAT file.
        Prescribed displacements are still isolated by ``compas_3dec``.
        """
        if self.name not in ("3DEC", "threeDEC"):
            raise ValueError("set_stages is only available for the 3DEC solver.")
        self.parameters["stages"] = _validate_threedec_stages(stages)
        return self

    @classmethod
    def threeDEC(cls, **kwargs):
        """Backward-compatible alias for :meth:`ThreeDEC`."""
        return cls.ThreeDEC(**kwargs)

    @classmethod
    def CRA(
        cls,
        d_bnd: float = 0.01,
        eps: float = 0.001,
        penalty: bool = False,
        verbose: bool = False,
        timer: bool = False,
    ):
        """
        CRA solver configuration.

        Parameters
        ----------
        d_bnd : float
            Bound on the virtual displacement. Default ``0.01``.

            Deliberately looser than compas_cra's own ``0.001``: on a finely
            discretised model that bound is too tight to satisfy the contact
            constraints and the solve reports ``infeasible``.
        eps : float
            Contact overlapping parameter. Default ``0.001``.
        penalty : bool
            Use the penalty formulation instead of the plain CRA solve.
        verbose : bool
            Print solver output.
        timer : bool
            Print timing information.
        """
        self = cls()
        self.name = "CRA"
        self.parameters = {
            "d_bnd": d_bnd,
            "eps": eps,
            "penalty": penalty,
            "verbose": verbose,
            "timer": timer,
        }
        return self

    @classmethod
    def PRD(
        cls,
        n_steps: int = 1,
        open_tol: float = 1e-3,
        mu: Optional[float] = None,
        solver: str = "CLARABEL",
        verbose: bool = False,
    ):
        """PRD (Piecewise Rigid Displacement) solver configuration.

        Parameters
        ----------
        n_steps : int
            Number of increments for the incremental nonlinear solve.
            If ``1`` (default), run the one-shot linear LP instead.
        open_tol : float
            Contact opening tolerance, used when ``n_steps > 1``. Default ``1e-3``.
        mu : float, optional
            Friction coefficient. Falls back to the contact model's ``mu`` if not given.
        solver : str
            CVXPY back-end solver. Default ``"CLARABEL"``.
            Other options: ``"MOSEK"``, ``"GUROBI"``, ``"HIGHS"``.
        verbose : bool
            Print solver output. Default ``False``.
        """
        self = cls()
        self.name = "PRD"
        self.parameters = {
            "n_steps": n_steps,
            "open_tol": open_tol,
            "mu": mu,
            "solver": solver,
            "verbose": verbose,
        }
        return self

    @classmethod
    def BLA(
        cls,
        n_steps: int = 1,
        open_tol: float = 1e-3,
        associative: bool = True,
        non_associative_params: Optional[dict] = None,
        mu: Optional[float] = None,
        solver: str = "CLARABEL",
        verbose: bool = False,
    ):
        """BLA (Block Limit Analysis) solver configuration.

        Parameters
        ----------
        n_steps : int
            Number of increments for the incremental solve.
            If ``1`` (default), run the one-shot linear LP instead.
        open_tol : float
            Contact opening tolerance, used when ``n_steps > 1``. Default ``1e-3``.
        associative : bool
            If ``True`` (default), use associative friction model.
            If ``False``, use non-associative friction model with parameters in ``non_associative_params``.
        non_associative_params : dict, optional
            Parameters for non-associative friction model (used when ``associative=False``).
                {mu: 0.6, betta: 0.6, xi: 0.0, gamma: 0.0, c_0k: 1e-5, tol: 1e-3, max_iter: 10}
        mu : float, optional
            Friction coefficient. Falls back to the contact model's ``mu`` if not given.
        solver : str
            CVXPY back-end solver. Default ``"CLARABEL"``.
            Other options: ``"MOSEK"``, ``"GUROBI"``, ``"HIGHS"``.
        verbose : bool
            Print solver output. Default ``False``.
        """
        self = cls()
        self.name = "BLA"
        self.parameters = {
            "n_steps": n_steps,
            "open_tol": open_tol,
            "associative": associative,
            "non_associative_params": non_associative_params,
            "mu": mu,
            "solver": solver,
            "verbose": verbose,
        }
        return self

    @classmethod
    def RBE(
        cls,
        verbose: bool = False,
        timer: bool = False,
    ):
        """RBE solver configuration.

        Parameters
        ----------
        verbose : bool
            Print solver output.
        timer : bool
            Print timing information.
        """
        self = cls()
        self.name = "RBE"
        self.parameters = {
            "verbose": verbose,
            "timer": timer,
        }
        return self
