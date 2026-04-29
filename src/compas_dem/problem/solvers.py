from compas.data import Data


class Solver(Data):
    """Container for solver configuration. Call one of the solver methods to set it up.

    Examples
    --------
    >>> s = Solver()
    >>> s.lmgc90(duration=1.0, n_steps=100)
    >>> problem.solve(s)
    """

    def __init__(self):
        super().__init__()
        self.name = None
        self.parameters = {}

    def __repr__(self):
        return f"Solver(name={self.name}, parameters={self.parameters})"

    def LMGC90(
        self,
        duration: float = 1.0,
        n_steps: int = 100,
        dt: float = None,
        theta: float = 0.5,
        urf_threshold: float = None,
        track_block: int = None,
        contact_law: str = "IQS_CLB",
    ):
        """
        LMGC90 solver configuration.
        Parameters
        ----------
        duration : float
            Total duration of the simulation in seconds.
        n_steps : int
            Number of time steps to simulate.
        dt : float
            Time step size. If None, it will be computed automatically based on the model properties.
        theta : float
            Time integration parameter (0.5 for mid-point rule, 1.0 for backward Euler).
        urf_threshold : float
            Unbalanced force threshold for convergence. If None, it will be set to a default value based on the model.
        track_block : int
            Optional block index to track and print its displacement/rotation during the simulation.
        contact_law : str
            Contact law to use in LMGC90. Default is "IQS_CLB" (a common choice for DEM simulations).
        """
        self.name = "LMGC90"
        self.parameters = {
            "duration": duration,
            "n_steps": n_steps,
            "dt": dt,
            "theta": theta,
            "urf_threshold": urf_threshold,
            "track_block": track_block,
            "contact_law": contact_law,
        }
        return self

    def CRA(
        self,
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
        self.name = "CRA"
        self.parameters = {
            "method": "penalty",
            "d_bnd": d_bnd,
            "eps": eps,
            "verbose": verbose,
            "timer": timer,
        }
        return self

    def RBE(
        self,
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
        self.name = "RBE"
        self.parameters = {
            "method": "rbe",
            "verbose": verbose,
            "timer": timer,
        }
        return self
