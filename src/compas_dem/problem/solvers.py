from typing import Optional

from compas.data import Data


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
        contact_law: str = "IQS_CLB",
        verbose: int = 0,
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
        contact_law : str
            Contact law to use in LMGC90. Default is "IQS_CLB" (a common choice for DEM simulations).
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
            "contact_law": contact_law,
            "verbose": verbose,
        }
        return self

    @classmethod
    def CRA(
        cls,
        d_bnd: float = 0.001,
        eps: float = 0.0001,
        verbose: bool = False,
        timer: bool = False,
    ):
        """
        CRA solver configuration.

        Parameters
        ----------
        d_bnd : float
            Penalty boundary parameter. Default ``0.001``.
        eps : float
            Penalty convergence tolerance. Default ``0.0001``.
        verbose : bool
            Print solver output.
        timer : bool
            Print timing information.
        """
        self = cls()
        self.name = "CRA"
        self.parameters = {
            "method": "cra",
            "d_bnd": d_bnd,
            "eps": eps,
            "verbose": verbose,
            "timer": timer,
        }
        return self

    @classmethod
    def PRD(
        cls,
        linear: bool = True,
        mu: Optional[float] = None,
        solver: str = "CLARABEL",
        non_linear_params: Optional[dict] = None,
        verbose: bool = False,
    ):
        """PRD (Piecewise Rigid Displacement) solver configuration.

        Parameters
        ----------
        linear : bool
            If ``True`` (default), run the one-shot linear LP.
            If ``False``, run the incremental nonlinear solve.
        mu : float, optional
            Friction coefficient. Falls back to the contact model's ``mu`` if not given.
        solver : str
            CVXPY back-end solver. Default ``"CLARABEL"``.
            Other options: ``"MOSEK"``, ``"GUROBI"``, ``"HIGHS"``.
        non_linear_params : dict, optional
            Parameters for the incremental nonlinear solve (used when ``linear=False``).
                {nsteps: 80, open_tol: 1e-3}
        verbose : bool
            Print solver output. Default ``False``.
        """
        self = cls()
        self.name = "PRD"
        self.parameters = {
            "linear": linear,
            "mu": mu,
            "solver": solver,
            "non_linear_params": non_linear_params or {"nsteps": 80, "open_tol": 1e-3},
            "verbose": verbose,
        }
        return self

    @classmethod
    def DPRD(
        cls,
        linear: bool = True,
        associative: bool = True,
        non_associative_params: Optional[dict] = None,
        non_linear_params: Optional[dict] = None,
        mu: Optional[float] = None,
        solver: str = "CLARABEL",
        verbose: bool = False,
    ):
        """DPRD (Dual Piecewise Rigid Displacement) solver configuration.

        Parameters
        ----------
        linear : bool
            If ``True`` (default), run the one-shot linear LP.
            If ``False``, run the incremental nonlinear solve.
        associative : bool
            If ``True`` (default), use associative friction model.
            If ``False``, use non-associative friction model with parameters in ``non_associative_params``.
        mu : float, optional
            Friction coefficient. Falls back to the contact model's ``mu`` if not given.
        solver : str
            CVXPY back-end solver. Default ``"CLARABEL"``.
            Other options: ``"MOSEK"``, ``"GUROBI"``, ``"HIGHS"``.
        non_linear_params : dict, optional
            Parameters for the incremental nonlinear solve (used when ``linear=False``).
                {nsteps: 80, open_tol: 1e-3}
        non_associative_params : dict, optional
            Parameters for non-associative friction model (used when ``associative=False``).
                {mu: 0.6, betta: 0.6, xi: 0.0, gamma: 0.0, c_0k: 1e-5, tol: 1e-3, max_iter: 10}
        verbose : bool
            Print solver output. Default ``False``.
        """
        self = cls()
        self.name = "DPRD"
        self.parameters = {
            "linear": linear,
            "associative": associative,
            "non_associative_params": non_associative_params,
            "non_linear_params": non_linear_params or {"nsteps": 80, "open_tol": 1e-3},
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
            "method": "rbe",
            "verbose": verbose,
            "timer": timer,
        }
        return self
