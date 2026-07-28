from compas_dem.analysis.resolve import resolve_centroidal_displacements
from compas_dem.analysis.resolve import resolve_centroidal_loads
from compas_dem.interactions import FrictionContact
from compas_dem.interactions.contact import local_resultant
from compas_dem.models import BlockModel
from compas_dem.problem.problem import Problem
from compas_dem.problem.results import Results

try:
    from compas_bla.core import BLAModel
    from compas_bla.viz.helpers import deformed_contacts
except ImportError:
    raise ImportError("compas_bla is not installed. Install it locally to use the BLA solver.")


def bla_solve(
    problem: Problem,
    model: BlockModel,
    n_steps: int = 1,
    associative: bool = True,
    non_associative_params: dict = None,
    non_linear_params: dict = None,
    mu: float = None,
    solver: str = "CLARABEL",
    verbose: bool = False,
) -> BLAModel:
    """Translate a Problem into a BLAModel, run the analysis, and post-process
    results back into the BlockModel in-place.

    Parameters
    ----------
    problem : :class:`~compas_dem.problem.Problem`
    model : :class:`~compas_dem.models.BlockModel`
    n_steps : int, optional
        Number of steps for the incremental solve.
        if ``1`` (default), run the one-shot linear LP.
    associative : bool, optional
        If ``True`` (default), use associative Coulomb friction.
    non_associative_params : dict, optional
        Parameters for non-associative friction.
        Keys: ``mu``, ``betta``, ``xi``, ``gamma``, ``c_0k``, ``tol``, ``max_iter``.
    non_linear_params : dict, optional
        Parameters for the incremental nonlinear solve (``n_steps > 1``).
        ``{nsteps: 80, open_tol: 1e-3}``
    mu : float, optional
        Friction coefficient. Falls back to the contact model's ``mu``.
    solver : str, optional
        CVXPY back-end solver. Default ``"CLARABEL"``.
    verbose : bool, optional
        Print solver output. Default ``False``.

    Returns
    -------
    :class:`compas_bla.core.BLAModel`
    """
    if mu is None:
        if problem.contact_properties.contact_model:
            mu = problem.contact_properties.contact_model.mu
        else:
            raise ValueError("No friction coefficient defined. Add a contact model via problem.add_contact_model('MohrCoulomb', mu=...) before solving.")

    bla = BLAModel(model)

    # ------------------------------------------------------------------
    # Loads
    # ------------------------------------------------------------------
    centroidal_loads = resolve_centroidal_loads(problem, model)
    loads = []
    for idx, entry in centroidal_loads.items():
        f = entry["force"]
        m = entry["moment"]
        if abs(f.x) > 1e-12:
            loads.append(["fx", idx, float(f.x)])
        if abs(f.y) > 1e-12:
            loads.append(["fy", idx, float(f.y)])
        if abs(f.z) > 1e-12:
            loads.append(["fz", idx, float(f.z)])
        if abs(m.x) > 1e-12:
            loads.append(["mx", idx, float(m.x)])
        if abs(m.y) > 1e-12:
            loads.append(["my", idx, float(m.y)])
        if abs(m.z) > 1e-12:
            loads.append(["mz", idx, float(m.z)])
    if loads:
        bla.set_force(loads)

    # ------------------------------------------------------------------
    # Displacement BCs
    # ------------------------------------------------------------------
    centroidal_displacements = resolve_centroidal_displacements(problem)
    disps = []
    for idx, entry in centroidal_displacements.items():
        t = entry.get("translation") or [0.0, 0.0, 0.0]
        r = entry.get("rotation") or [0.0, 0.0, 0.0]
        t = [v if v is not None else 0.0 for v in t]
        r = [v if v is not None else 0.0 for v in r]
        disps.append((idx, t + r))
    if disps:
        bla.set_displacement_bc(disps)

    # ------------------------------------------------------------------
    # Non-associative parameters
    # ------------------------------------------------------------------
    if not associative:
        params = non_associative_params or {}
        bla.set_non_associative_params(**params)

    # ------------------------------------------------------------------
    # Solve
    # ------------------------------------------------------------------
    nl = non_linear_params or {}
    _nsteps = nl.get("nsteps", 80)
    _open_tol = nl.get("open_tol", 1e-3)

    if n_steps == 1 and associative:
        cvx_result = bla.solve_static_associative(solver=solver, mu=mu, verbose=verbose)
    elif n_steps == 1 and not associative:
        cvx_result = bla.solve_static_non_associative(solver=solver, verbose=verbose)
    elif n_steps > 1 and associative:
        cvx_result = bla.solve_static_associative_non_linear(nsteps=_nsteps, mu=mu, open_tol=_open_tol, solver=solver, verbose=verbose)
    else:
        cvx_result = bla.solve_static_non_associative_non_linear(nsteps=_nsteps, open_tol=_open_tol, solver=solver, verbose=verbose)

    bla.post_process_results()

    bla.name = "BLA"
    results = _post_processing_bla(bla, problem, model)
    results.metadata["mu"] = mu
    results.metadata["solver_status"] = cvx_result.status
    return results


def _post_processing_bla(bla: BLAModel, problem: Problem, model: BlockModel) -> Results:
    """Build a standalone :class:`~compas_dem.problem.Results` from BLA solver output.

    The contacts are rebuilt from the solver results by
    :func:`compas_bla.viz.helpers.deformed_contacts`, so the geometry stored on the
    results is the contact in its displaced position -- the mid-surface between the
    two blocks after the solve -- and not the original undisplaced contact.

    Returns
    -------
    :class:`~compas_dem.problem.Results`
    """
    results = Results(model_id=str(model.guid), problem_id=str(problem.guid))
    graph = model.graph

    for block in model.elements():
        T = graph.node_attribute(block.graphnode, "transform")
        if T is not None:
            results.set_node(block.graphnode, "transformation", T)

    deformed: dict[tuple, FrictionContact] = dict(deformed_contacts(bla))

    for edge in graph.edges():
        fc = deformed.get(edge)
        if fc is None:
            continue

        n_pts = len(fc.points)

        resultant_lines = fc.resultantforce
        if resultant_lines:
            force_vec = list(resultant_lines[0].vector)
            force_mag = float(resultant_lines[0].vector.length)
        else:
            force_vec = [0.0, 0.0, 0.0]
            force_mag = 0.0

        results.set_edge(edge, "contact_polygon", fc.polygon)
        results.set_edge(edge, "contact_data", fc)
        results.set_edge(edge, "force_magnitude", force_mag)
        results.set_edge(edge, "resultant_global", force_vec)
        results.set_edge(edge, "resultant_local", local_resultant(fc.forces))
        results.set_edge(edge, "face_contact", n_pts >= 3)
        results.set_edge(edge, "edge_contact", n_pts == 2)
        results.set_edge(edge, "point_contact", n_pts == 1)
        results.set_edge(edge, "contact_points", [list(p) for p in fc.points])
        results.set_edge(edge, "force_normal", [f["c_np"] - f["c_nn"] for f in fc.forces])
        results.set_edge(edge, "force_tangent1", [f["c_u"] for f in fc.forces])
        results.set_edge(edge, "force_tangent2", [f["c_v"] for f in fc.forces])
        if fc.frame is not None:
            results.set_edge(edge, "contact_frame", fc.frame)

    return results
