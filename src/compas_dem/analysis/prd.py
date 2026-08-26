from compas_dem.analysis.resolve import resolve_centroidal_displacements
from compas_dem.analysis.resolve import resolve_centroidal_loads
from compas_dem.interactions import FrictionContact
from compas_dem.interactions.contact import local_resultant
from compas_dem.models import BlockModel
from compas_dem.problem.problem import Problem
from compas_dem.problem.results import Results

try:
    from compas_pr3d.prd import PR3DModel
except ImportError:
    raise ImportError("compas_pr3d is not installed. Install it locally to use the PRD solver.")


def prd_solve(
    problem: Problem,
    model: BlockModel,
    n_steps: int = 1,
    open_tol: float = 1e-3,
    mu: float = None,
    solver: str = "CLARABEL",
    verbose: bool = False,
) -> Results:
    """Translate a Problem into a PR3DModel, run the analysis, and return the results.

    Parameters
    ----------
    problem : :class:`~compas_dem.problem.Problem`
    model : :class:`~compas_dem.models.BlockModel`
    n_steps : int, optional
        Number of increments for the incremental nonlinear solve.
        If ``1`` (default), run the one-shot linear LP instead.
    open_tol : float, optional
        Contact opening tolerance, used when ``n_steps > 1``. Default ``1e-3``.
    mu : float, optional
        Friction coefficient. Falls back to the contact model's ``mu``.
    solver : str, optional
        CVXPY back-end solver. Default ``"CLARABEL"``.
    verbose : bool, optional
        Print solver output. Default ``False``.

    Returns
    -------
    :class:`~compas_dem.problem.Results`
    """
    if n_steps < 1:
        raise ValueError(f"n_steps must be at least 1, got {n_steps}.")

    if mu is None:
        if problem.contact_properties.contact_model:
            mu = problem.contact_properties.contact_model.mu
        else:
            raise ValueError("No friction coefficient defined. Add a contact model via problem.set_contact_model('MohrCoulomb', mu=...) before solving.")

    prd = PR3DModel(model)

    # ------------------------------------------------------------------
    # Loads
    # ------------------------------------------------------------------
    centroidal_loads = resolve_centroidal_loads(model, problem.boundary_conditions)
    loads = []
    for idx, entry in centroidal_loads.items():
        f = entry["force"]
        if abs(f.x) > 1e-12:
            loads.append(["fx", idx, float(f.x)])
        if abs(f.y) > 1e-12:
            loads.append(["fy", idx, float(f.y)])
        if abs(f.z) > 1e-12:
            loads.append(["fz", idx, float(f.z)])
    if loads:
        prd.set_force(loads)

    # ------------------------------------------------------------------
    # Displacement BCs (incremental solve only)
    # ------------------------------------------------------------------
    if n_steps > 1:
        centroidal_displacements = resolve_centroidal_displacements(problem.boundary_conditions)
        disps = []
        for idx, entry in centroidal_displacements.items():
            t = entry.get("translation") or [0.0, 0.0, 0.0]
            r = entry.get("rotation") or [0.0, 0.0, 0.0]
            t = [v if v is not None else 0.0 for v in t]
            r = [v if v is not None else 0.0 for v in r]
            disps.append((idx, t + r))
        if disps:
            prd.set_displacement_bc(disps)

    # ------------------------------------------------------------------
    # Solve
    # ------------------------------------------------------------------
    if n_steps == 1:
        prd.solve(dual=True, mu=mu, verbose=verbose, solver=solver)
    else:
        prd.solve_nonlinear(
            nsteps=n_steps,
            open_tol=open_tol,
            solver=solver,
            mu=mu,
            verbose=verbose,
        )

    prd.post_process_results()

    prd.name = "PRD"
    results = _post_processing_prd(prd, problem, model)
    results.metadata["mu"] = mu
    return results


def _post_processing_prd(prd: PR3DModel, problem: Problem, model: BlockModel) -> Results:
    """Build a standalone :class:`~compas_dem.problem.Results` from PRD solver output.

    Does **not** mutate the model or its graph.

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

    for edge in graph.edges():
        contacts = graph.edge_attribute(edge, "contacts")
        if not contacts:
            continue

        fc: FrictionContact = contacts[0]
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
