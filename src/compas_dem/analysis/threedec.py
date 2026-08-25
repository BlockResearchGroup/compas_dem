from typing import Optional

from compas_dem.models import BlockModel
from compas_dem.problem.problem import Problem
from compas_dem.problem.results import Results


def threedec_solve(
    problem: Problem,
    model: BlockModel,
    version: str = "7.0",
    executable: Optional[str] = None,
    workspace: Optional[str] = None,
    arguments: Optional[list[str]] = None,
    ratio: float = 1e-5,
    ratio_keyword: str = "ratio-local",
    time: float = 1.0,
    gravity_steps: int = 10,
    stages: Optional[list[list[str]]] = None,
    suppress_output: bool = True,
    timeout: Optional[float] = None,
    gridpoint_tolerance: float = 1e-6,
    progress_callback=None,
    event_pump=None,
    poll_interval: float = 0.2,
) -> Results:
    """Solve a refactored COMPAS DEM problem with ``compas_3dec``."""
    try:
        from compas_3dec import ThreeDECAnalysisBuilder
        from compas_3dec import ThreeDECSolver
    except (ImportError, FileNotFoundError):
        raise ImportError("compas_3dec is required for Solver.ThreeDEC(). Install it in the same environment as compas_dem.")

    # The problem is the canonical input boundary. It owns a transient model
    # reference restored by compas_dem.models.Analysis after deserialization.
    if problem.model is not model:
        problem.load_model(model)

    solver = ThreeDECSolver(
        version=version,
        executable=executable,
        workspace=workspace,
        arguments=arguments,
        suppress_output=suppress_output,
        timeout=timeout,
        gridpoint_tolerance=gridpoint_tolerance,
        progress_callback=progress_callback,
        event_pump=event_pump,
        poll_interval=poll_interval,
    )
    analysis = ThreeDECAnalysisBuilder.from_dem_problem(problem).build()

    # These values live in Problem.solver and are picked up by
    # ThreeDECAnalysisBuilder when it creates the portable snapshot.
    _ = (ratio, ratio_keyword, time, gravity_steps, stages)
    raw_results = solver.solve(analysis)
    return raw_results.to_compas_dem_results(analysis)
