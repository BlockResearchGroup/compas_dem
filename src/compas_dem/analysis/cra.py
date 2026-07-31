import contextlib
from typing import Optional

import numpy as np

try:
    from compas_assembly.datastructures import Assembly
    from compas_assembly.datastructures import Block

    # Aliased: this module exposes its own ``cra_solve`` / ``rbe_solve`` taking a
    # Problem and a BlockModel, while these take a compas_cra Assembly.
    from compas_cra.equilibrium import cra_penalty_solve as _cra_penalty_backend
    from compas_cra.equilibrium import cra_solve as _cra_backend
    from compas_cra.equilibrium import rbe_solve as _rbe_backend
except ImportError:
    raise ImportError("compas_cra is not installed. Install it to use the CRA / RBE solvers.")

import compas.geometry as cg
from compas_dem.interactions import FrictionContact
from compas_dem.interactions.contact import local_resultant
from compas_dem.models import BlockModel
from compas_dem.problem import Problem
from compas_dem.problem.results import Results

#: IPOPT tolerances used for the CRA solves.
#:
#: compas_cra hardcodes ``tol=1e-10``, ``constr_viol_tol=1e-12`` and
#: ``compl_inf_tol=1e-12`` on the solver it builds internally. That precision is
#: out of reach for the MUMPS linear solver that conda-forge IPOPT is built
#: against, so the solve ends in ``Restoration Failed`` or exhausts IPOPT's
#: iteration limit — reproducible with compas_cra's own arch example, and on a
#: 2024 stack (compas_cra 0.4.0 / pyomo 6.4.2 / IPOPT 3.14.14) as well, so it is
#: not a regression. These are IPOPT's own defaults, plus a raised iteration cap.
#: An IPOPT built against HSL MA27 can handle the original values.
DEFAULT_IPOPT_OPTIONS: dict = {
    "tol": 1e-6,
    "constr_viol_tol": 1e-4,
    "compl_inf_tol": 1e-4,
    "acceptable_tol": 1e-4,
    "acceptable_constr_viol_tol": 1e-2,
    "acceptable_compl_inf_tol": 1e-2,
    "max_iter": 10000,
}


@contextlib.contextmanager
def _ipopt_options(options: dict):
    """Apply ``options`` to the IPOPT solver that compas_cra creates internally.

    compas_cra sets its tolerances on a solver object it never exposes, so the
    only way to override them is to hand it a factory whose solver re-applies
    ours immediately before solving. The patch is on ``pyomo.environ`` and is
    always undone, but it is process-wide while held, so it is not thread-safe.
    """
    import pyomo.environ as pyo

    original = pyo.SolverFactory

    def factory(*args, **kwargs):
        solver = original(*args, **kwargs)
        inner_solve = solver.solve

        def solve(*a, **kw):
            for key, value in options.items():
                solver.options[key] = value
            return inner_solve(*a, **kw)

        solver.solve = solve
        return solver

    pyo.SolverFactory = factory
    try:
        yield
    finally:
        pyo.SolverFactory = original


def _blockmodel_to_assembly(model: BlockModel) -> Assembly:
    element_block: dict[int, int] = {}

    assembly = Assembly()

    for element in model.elements():
        block: Block = element.modelgeometry.copy(cls=Block)
        x, y, z = element.point
        node = assembly.add_block(block, x=x, y=y, z=z, is_support=element.is_support)
        element_block[element.graphnode] = node

        assembly.graph.node_attribute(node, "graphnode", element.graphnode)

    for edge in model.graph.edges():
        u = element_block[edge[0]]  # type: ignore
        v = element_block[edge[1]]

        contacts = model.graph.edge_attribute(edge, name="contacts")  # type: ignore
        assembly.graph.add_edge(u, v, interfaces=contacts)

    return assembly


# def _post_processing_cra(assembly: Assembly, model: BlockModel, density: float = 1.0) -> None:
#     """Write CRA results directly onto the BlockModel graph (in-place). Kept for reference."""
#     for block in model.elements():
#         model.graph.node_attribute(block.graphnode, "transformation", cg.Transformation())
#     for u_asm, v_asm in assembly.graph.edges():
#         interfaces = assembly.graph.edge_attribute((u_asm, v_asm), name="interfaces")
#         if not interfaces:
#             continue
#         u = assembly.graph.node_attribute(u_asm, "graphnode")
#         v = assembly.graph.node_attribute(v_asm, "graphnode")
#         for interface in interfaces:
#             if not interface.forces:
#                 continue
#             scale = density * 9.81
#             scaled_forces = [{k: v * scale for k, v in f.items()} for f in interface.forces]
#             fc = FrictionContact(points=interface.points, frame=interface.frame)
#             fc.forces = scaled_forces
#             model.graph.edge_attribute((u, v), "contact_data", fc)
#             model.graph.edge_attribute((u, v), "face_contact", True)
#             model.graph.edge_attribute((u, v), "contact_point", [list(p) for p in interface.points])
#             model.graph.edge_attribute((u, v), "contact_polygon", interface.polygon)
#             fn = sum(f["c_np"] - f["c_nn"] for f in scaled_forces)
#             fu = sum(f["c_u"] for f in scaled_forces)
#             fv = sum(f["c_v"] for f in scaled_forces)
#             w = list(interface.frame.zaxis)
#             u_ax = list(interface.frame.xaxis)
#             v_ax = list(interface.frame.yaxis)
#             force = [fn * w[j] + fu * u_ax[j] + fv * v_ax[j] for j in range(3)]
#             model.graph.edge_attribute((u, v), "force", force)
#             model.graph.edge_attribute((u, v), "force_magnitude", np.linalg.norm(force))


def _post_processing_cra(assembly: Assembly, problem: Problem, model: BlockModel, density: float = 1.0) -> Results:
    """Build a standalone :class:`~compas_dem.problem.Results` from CRA / RBE solver output.

    Does **not** mutate the model or its graph.

    Parameters
    ----------
    assembly : :class:`compas_assembly.datastructures.Assembly`
    problem : :class:`~compas_dem.problem.Problem`
    model : :class:`~compas_dem.models.BlockModel`
    density : float, optional
        Physical material density used to rescale forces. Default ``1.0``.

    Returns
    -------
    :class:`~compas_dem.problem.Results`
    """
    results = Results(model_id=str(model.guid), problem_id=str(problem.guid))

    for block in model.elements():
        results.set_node(block.graphnode, "transformation", cg.Transformation())

    for u_asm, v_asm in assembly.graph.edges():
        interfaces = assembly.graph.edge_attribute((u_asm, v_asm), name="interfaces")
        if not interfaces:
            continue

        u = assembly.graph.node_attribute(u_asm, "graphnode")
        v = assembly.graph.node_attribute(v_asm, "graphnode")

        for interface in interfaces:
            if not interface.forces:
                continue

            scale = density * 9.81
            scaled_forces = [{k: val * scale for k, val in f.items()} for f in interface.forces]

            fc = FrictionContact(points=interface.points, frame=interface.frame)
            fc.forces = scaled_forces
            results.set_edge((u, v), "contact_data", fc)
            results.set_edge((u, v), "face_contact", True)
            results.set_edge((u, v), "contact_points", [list(p) for p in interface.points])
            results.set_edge((u, v), "contact_polygon", interface.polygon)

            fu, fv, fn = local_resultant(scaled_forces)
            w = list(interface.frame.zaxis)
            u_ax = list(interface.frame.xaxis)
            v_ax = list(interface.frame.yaxis)
            force = [fn * w[j] + fu * u_ax[j] + fv * v_ax[j] for j in range(3)]
            results.set_edge((u, v), "resultant_global", force)
            results.set_edge((u, v), "resultant_local", [fu, fv, fn])
            results.set_edge((u, v), "force_magnitude", float(np.linalg.norm(force)))

    return results


def _resolve_mu(problem: Problem, mu: Optional[float]) -> float:
    """Return the friction coefficient, falling back to the problem's contact model."""
    if mu is not None:
        return mu
    elif problem.contact_properties.contact_model:
        return problem.contact_properties.contact_model.mu
    else:
        raise ValueError("No friction coefficient provided and no contact model in the problem.")


def _resolve_density(model: BlockModel, density: Optional[float]) -> float:
    """Return the density used to rescale forces: the first block that declares one."""
    if density is not None:
        return density
    for block in model.elements():
        if block.material and block.material.density:
            return block.material.density
        else:
            raise ValueError(f"Block {block.graphnode} has no material with a density assigned.")


def rbe_solve(
    problem: Problem,
    model: BlockModel,
    mu: Optional[float] = None,
    density: Optional[float] = None,
    verbose: bool = True,
    timer: bool = False,
) -> Results:
    """Solve a Problem with RBE and return the results.

    Requires ``model.compute_contacts()`` to have been called first.

    Parameters
    ----------
    problem : :class:`~compas_dem.problem.Problem`
    model : :class:`~compas_dem.models.BlockModel`
    mu : float, optional
        Friction coefficient. Falls back to ``problem.contact_properties.contact_model.mu``.
    density : float, optional
        Physical material density for force rescaling. Falls back to the first
        block that declares one.
    verbose : bool, optional
        Print solver output.
    timer : bool, optional
        Print timing information.

    Returns
    -------
    :class:`~compas_dem.problem.Results`
    """
    mu = _resolve_mu(problem, mu)
    density = _resolve_density(model, density)

    assembly = _blockmodel_to_assembly(model)
    _rbe_backend(assembly, mu=mu, density=1.0, verbose=verbose, timer=timer)

    results = _post_processing_cra(assembly, problem, model, density=density)
    results.metadata["mu"] = mu
    return results


def cra_solve(
    problem: Problem,
    model: BlockModel,
    penalty: bool = False,
    mu: Optional[float] = None,
    density: Optional[float] = None,
    d_bnd: float = 0.01,
    eps: float = 0.001,
    ipopt_options: Optional[dict] = None,
    verbose: bool = True,
    timer: bool = False,
) -> Results:
    """Solve a Problem with CRA and return the results.

    Requires ``model.compute_contacts()`` to have been called first.

    Parameters
    ----------
    problem : :class:`~compas_dem.problem.Problem`
    model : :class:`~compas_dem.models.BlockModel`
    penalty : bool, optional
        If ``True``, use the penalty formulation. Default ``False``, the plain
        CRA solve. For RBE, call :func:`rbe_solve` instead.
    mu : float, optional
        Friction coefficient. Falls back to ``problem.contact_properties.contact_model.mu``.
    density : float, optional
        Physical material density for force rescaling. Falls back to the first
        block that declares one.
    d_bnd : float, optional
        Penalty boundary parameter. Default ``0.01``.
    eps : float, optional
        Penalty convergence tolerance. Default ``0.001``.
    ipopt_options : dict, optional
        IPOPT options overriding the tolerances compas_cra hardcodes. Merged
        over :data:`DEFAULT_IPOPT_OPTIONS`; pass ``{}`` to keep those as they
        are, or e.g. ``{"tol": 1e-10}`` to restore compas_cra's own value.
    verbose : bool, optional
        Print solver output.
    timer : bool, optional
        Print timing information.

    Returns
    -------
    :class:`~compas_dem.problem.Results`
    """
    options = dict(DEFAULT_IPOPT_OPTIONS)
    options.update(ipopt_options or {})

    mu = _resolve_mu(problem, mu)
    density = _resolve_density(model, density)

    assembly = _blockmodel_to_assembly(model)

    backend = _cra_penalty_backend if penalty else _cra_backend
    with _ipopt_options(options):
        backend(assembly, mu=mu, density=1.0, d_bnd=d_bnd, eps=eps, verbose=verbose, timer=timer)

    results = _post_processing_cra(assembly, problem, model, density=density)
    results.metadata["mu"] = mu
    results.metadata["penalty"] = penalty
    return results
