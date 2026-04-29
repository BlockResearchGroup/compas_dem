import compas.geometry as cg
from compas_assembly.datastructures import Assembly
from compas_assembly.datastructures import Block
from compas_cra.equilibrium import cra_penalty_solve as _cra_penalty_solve
from compas_cra.equilibrium import rbe_solve as _rbe_solve

from compas_dem.interactions import FrictionContact
from compas_dem.models import BlockModel
from compas_dem.problem.problem import Problem


def _blockmodel_to_assembly(model: BlockModel) -> tuple[Assembly, dict]:
    """Convert a BlockModel to a compas_assembly Assembly.

    Returns
    -------
    tuple
        (assembly, asm_to_graphnode)
    """
    graphnode_to_asm: dict[int, int] = {}
    assembly = Assembly()

    for element in model.elements():
        block: Block = element.modelgeometry.copy(cls=Block)
        x, y, z = element.point
        node = assembly.add_block(block, x=x, y=y, z=z, is_support=element.is_support)
        graphnode_to_asm[element.graphnode] = node

    for u, v in model.graph.edges():
        u_asm = graphnode_to_asm[u]
        v_asm = graphnode_to_asm[v]
        contacts = model.graph.edge_attribute((u, v), name="contacts")
        assembly.graph.add_edge(u_asm, v_asm, interfaces=contacts)

    return assembly, {v: k for k, v in graphnode_to_asm.items()}


def _post_processing_cra(assembly: Assembly, asm_to_graphnode: dict, problem: Problem) -> None:
    """Write CRA results back to the Problem's BlockModel in-place.

    Block attributes set
    --------------------
    displacement : :class:`compas.geometry.Transformation`
        Identity transformation — CRA is static, blocks do not move.

    Edge attributes set
    -------------------
    friction_contact : :class:`FrictionContact`
        Solved contact forces, in the same format as LMGC90 output.
    contact_polygon : :class:`compas.geometry.Polygon`
        The contact interface polygon.
    force : list[float]
        Resultant force vector [fx, fy, fz] at the interface.
    """
    model = problem.model

    # Block annotations (static — no displacement)
    for block in model.elements():
        block.displacement = cg.Transformation()

    # Edge annotations from solved interfaces
    for u_asm, v_asm in assembly.graph.edges():
        interfaces = assembly.graph.edge_attribute((u_asm, v_asm), name="interfaces")
        if not interfaces:
            continue

        u = asm_to_graphnode[u_asm]
        v = asm_to_graphnode[v_asm]

        for interface in interfaces:
            if not interface.forces:
                continue

            # FrictionContact with frame already set from interface detection
            fc = FrictionContact(points=interface.points, frame=interface.frame)
            fc.forces = interface.forces
            model.graph.edge_attribute((u, v), "friction_contact", fc)

            model.graph.edge_attribute((u, v), "contact_point", [list(p) for p in interface.points])
            model.graph.edge_attribute((u, v), "contact_polygon", interface.polygon)

            # Resultant global force vector from summed components
            fn = sum(f["c_np"] - f["c_nn"] for f in interface.forces)
            fu = sum(f["c_u"] for f in interface.forces)
            fv = sum(f["c_v"] for f in interface.forces)
            w = list(interface.frame.zaxis)
            u_ax = list(interface.frame.xaxis)
            v_ax = list(interface.frame.yaxis)
            force = [fn * w[j] + fu * u_ax[j] + fv * v_ax[j] for j in range(3)]
            model.graph.edge_attribute((u, v), "force", force)


def cra_solve(
    problem: Problem,
    method: str = "penalty",
    mu: float = None,
    density: float = None,
    d_bnd: float = 0.01,
    eps: float = 0.001,
    verbose: bool = True,
    timer: bool = False,
) -> None:
    """Solve a Problem using CRA and write results back to the BlockModel in-place.

    Requires ``problem.model.compute_contacts()`` to have been called first.

    Parameters
    ----------
    problem : :class:`~compas_dem.problem.Problem`
        The problem containing model, forces, BCs, and contact properties.
    method : str, optional
        ``"penalty"`` (default) or ``"rbe"``.
    mu : float, optional
        Friction coefficient. Falls back to ``problem.contact_properties.contact_model.mu``
        or 0.6 if not set.
    density : float, optional
        Normalized material density. CRA uses unit-less relative density — default ``1.0``.
        Do not pass actual kg/m³ values; they will make gravity forces too large for the solver.
    d_bnd : float, optional
        Penalty boundary parameter. Default ``0.001``.
    eps : float, optional
        Penalty convergence tolerance. Default ``0.0001``.
    verbose : bool, optional
        Print solver output.
    timer : bool, optional
        Print timing information.
    """
    model = problem.model

    # Support flags from boundary conditions
    for block in model.elements():
        idx = block.graphnode
        disp = problem.centroidal_displacements.get(idx)
        if disp is not None:
            t = disp["translation"] or [0.0, 0.0, 0.0]
            r = disp["rotation"] or [0.0, 0.0, 0.0]
            if all(v == 0.0 for v in t) and all(v == 0.0 for v in r):
                block.is_support = True

    # Friction coefficient
    if mu is None:
        if problem.contact_properties.contact_model:
            mu = problem.contact_properties.contact_model.mu
        else:
            mu = 0.6

    # CRA uses normalized density (1.0 = unit mass per unit volume).
    # Passing actual kg/m³ values inflates forces far beyond solver tolerances.
    if density is None:
        density = 2000.0

    assembly, asm_to_graphnode = _blockmodel_to_assembly(model)

    if method == "rbe":
        _rbe_solve(assembly, mu=mu, density=density, verbose=verbose, timer=timer)
    elif method == "penalty":
        _cra_penalty_solve(
            assembly,
            mu=mu,
            density=density,
            d_bnd=d_bnd,
            eps=eps,
            verbose=verbose,
            timer=timer,
        )
    else:
        raise ValueError(f"Unknown CRA method '{method}'. Use 'rbe' or 'penalty'.")

    _post_processing_cra(assembly, asm_to_graphnode, problem)
