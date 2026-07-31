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
