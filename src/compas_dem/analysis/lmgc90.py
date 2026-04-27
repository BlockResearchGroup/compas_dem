from collections import defaultdict

import numpy as np

from compas_dem.problem.problem import Problem

try:
    from compas_lmgc90.solver import Solver
except ImportError:
    raise ImportError("compas_lmgc90 is not installed. Install it to use the LMGC90 solver.")
# ---------------------------------------------------------------------------
# UFR – Unbalanced Force Ratio
# ---------------------------------------------------------------------------


def compute_urf(solver: Solver, problem: Problem) -> float:
    """Return the Unbalanced Force Ratio for the current simulation step.

    UFR = Σ_i |F_i_net| / ( Σ_i |F_i_applied| + Σ_ij |F_ij_contact| )

    Reads from ``solver.last_result`` (set by :meth:`Solver.run`).
    Returns 0.0 when no forces are present, and approaches 0 at equilibrium.
    """
    result = solver.last_result

    # Applied forces from the problem plus LMGC90's always-on gravity
    g_vec = np.array([0.0, 0.0, -9.81])
    applied_forces = {}
    for idx, block in problem._blocks.items():
        external = np.asarray(list(problem.centroidal_loads[idx]["force"]), dtype=float)
        mass = getattr(block, "mass", None)
        gravity = mass * g_vec if mass is not None else np.zeros(3)
        applied_forces[idx] = external + gravity

    # Net contact force per body (Newton's third law)
    contact_net: dict = defaultdict(lambda: np.zeros(3))
    for i in range(len(result.interaction_bodies)):
        cd_id, an_id = result.interaction_bodies[i]
        f = np.asarray(result.interaction_force_global[i], dtype=float)
        contact_net[cd_id] += f
        contact_net[an_id] -= f

    numerator = sum(np.linalg.norm(applied_forces.get(idx, np.zeros(3)) + cf) for idx, cf in contact_net.items())
    for idx, af in applied_forces.items():
        if idx not in contact_net:
            numerator += np.linalg.norm(af)

    total_applied = sum(np.linalg.norm(af) for af in applied_forces.values())
    total_contact = sum(result.interaction_force_magnitude[i] for i in range(len(result.interaction_bodies)))
    denominator = total_applied + total_contact

    return 0.0 if denominator == 0.0 else numerator / denominator


def lmgc90_solve(
    problem: Problem,
    contact_law: str = "IQS_CLB",
    duration: float = None,
    n_steps: int = None,
    dt: float = None,
    theta: float = 0.5,
    urf_threshold: float = None,
    track_block: int = None,
) -> Solver:
    """Translate a Problem into a configured LMGC90 Solver.

    Parameters
    ----------
    problem : :class:`~compas_dem.problem.Problem`
        The problem containing model, forces, BCs, and contact properties.
    contact_law : str, optional
        LMGC90 contact law identifier. Default ``"IQS_CLB"``.
    duration : float, optional
        Total simulation time [s].
    n_steps : int, optional
        Number of time steps.
    dt : float, optional
        Time step size [s].
    theta : float, optional
        Time-integration parameter. Default ``0.5``.
    urf_threshold : float, optional
        Unbalanced Force Ratio convergence threshold.  When provided, the UFR
        is computed after every step and the simulation stops early once UFR
        drops below this value.  ``None`` (default) disables UFR tracking.
        Requires ``solver.get_contacts()`` to expose ``"body_ids"`` and
        ``"force_vectors"`` keys; a warning is printed and tracking is skipped
        if those keys are absent.

    Returns
    -------
    :class:`compas_lmgc90.solver.Solver`
        A configured LMGC90 solver after running the simulation.
        ``solver.urf_history`` (list of float) is attached when *urf_threshold*
        is provided.

    Examples
    --------
    >>> solver = lmgc90_solve(problem, duration=1.0, n_steps=100)
    >>> solver = lmgc90_solve(problem, dt=0.01, n_steps=100)
    >>> solver = lmgc90_solve(problem, duration=1.0, dt=0.01)
    >>> solver = lmgc90_solve(problem, duration=1.0, n_steps=500, urf_threshold=1e-3)
    """
    given = sum(x is not None for x in [duration, n_steps, dt])
    if given == 3:
        raise ValueError("Provide exactly two of duration, n_steps, dt — the third is computed automatically.")
    elif given == 1:
        raise ValueError("Provide exactly two of duration, n_steps, dt.")
    elif given == 0:
        print("No time parameters provided; defaulting to duration=0.5s, n_steps=50.")
        duration, n_steps = 0.5, 50
        dt = duration / n_steps
    else:
        if duration is None:
            duration = dt * n_steps
        elif n_steps is None:
            n_steps = round(duration / dt)
        else:
            dt = duration / n_steps

    model = problem.model

    # ------------------------------------------------------------------
    # Density: first non-support block with material, or fallback
    # ------------------------------------------------------------------
    for block in model.blocks():
        if block.material and block.material.density:
            density = block.material.density
            break

    # ------------------------------------------------------------------
    # Contact friction: last contact properties added to the problem
    # ------------------------------------------------------------------
    mu = 0.65
    if problem.contact_properties:
        cp = problem.contact_properties[-1]
        if cp.contact_model:
            mu = cp.contact_model.mu

    # ------------------------------------------------------------------
    # Build solver
    # ------------------------------------------------------------------
    # Fully-fixed blocks (all-zero translation + rotation) must go through
    # set_supports_from_model() so LMGC90 receives np.zeros([6]) with v[4]=0,
    # matching the expected drvdof format. apply_velocity(value=0.0) produces
    # [[0,0,0,0,1,0]] (v[4]=1) which activates the constraint differently.
    for block in model.elements():
        idx = block.graphnode
        disp = problem.centroidal_displacements.get(idx)
        if disp is not None:
            t = disp["translation"] or [0.0, 0.0, 0.0]
            r = disp["rotation"] or [0.0, 0.0, 0.0]
            if all(v == 0.0 for v in t) and all(v == 0.0 for v in r):
                block.is_support = True

    solver = Solver(model, density=density, dt=duration / n_steps, theta=theta)
    solver.set_supports_from_model()

    # ------------------------------------------------------------------
    # Displacement BCs → apply_velocity (prescribed non-zero only)
    # ------------------------------------------------------------------
    for block in model.elements():
        idx = block.graphnode
        disp = problem.centroidal_displacements.get(idx)
        if disp is None or block.is_support:
            continue

        translation = disp["translation"] if disp["translation"] is not None else [0.0, 0.0, 0.0]
        rotation = disp["rotation"] if disp["rotation"] is not None else [0.0, 0.0, 0.0]

        for component, value in zip(["Vx", "Vy", "Vz"], translation):
            if value != 0.0:
                solver.apply_velocity(block_index=idx, component=component, value=value / duration)
        for component, value in zip(["Rx", "Ry", "Rz"], rotation):
            if value != 0.0:
                solver.apply_velocity(block_index=idx, component=component, value=value / duration)

    # ------------------------------------------------------------------
    # Applied forces: decompose centroidal (force, moment) into per-axis
    # time series — The three values inputted are at t=0, t=duration*0.9, and t=duration, allowing for ramped or instantaneous loading.
    # ------------------------------------------------------------------
    t_series = np.array([0.0, duration * 0.98, duration])

    for idx, entry in problem.centroidal_loads.items():
        f = entry["force"]
        m = entry["moment"]
        ramp = entry.get("loading_type", "ramp") == "ramp"

        def _vals(v):
            return [0, v, v] if ramp else [v, v, 0]

        if abs(f.x) > 1e-12:
            solver.apply_force(block_index=idx, component="Fx", value=np.array([t_series, _vals(f.x)]))
        if abs(f.y) > 1e-12:
            solver.apply_force(block_index=idx, component="Fy", value=np.array([t_series, _vals(f.y)]))
        if abs(f.z) > 1e-12:
            solver.apply_force(block_index=idx, component="Fz", value=np.array([t_series, _vals(f.z)]))
        if abs(m.x) > 1e-12:
            solver.apply_force(block_index=idx, component="Mx", value=np.array([t_series, _vals(m.x)]))
        if abs(m.y) > 1e-12:
            solver.apply_force(block_index=idx, component="My", value=np.array([t_series, _vals(m.y)]))
        if abs(m.z) > 1e-12:
            solver.apply_force(block_index=idx, component="Mz", value=np.array([t_series, _vals(m.z)]))

    # ------------------------------------------------------------------
    # Contact law
    # ------------------------------------------------------------------
    solver.contact_law(contact_law, mu)

    solver.preprocess()
    force_time = []
    urf_history = []
    displacement_history = []
    initial_pos = np.array(solver.trimeshes[track_block].centroid()) if track_block is not None else None
    print("Starting LMGC90 solver analysis...")
    for step in range(n_steps):
        solver.run(nb_steps=1)

        if track_block is not None:
            current_pos = np.array(solver.trimeshes[track_block].centroid())
            displacement_history.append(current_pos - initial_pos)

        if urf_threshold is not None:
            urf = compute_urf(solver, problem)
            urf_history.append(urf)
            if step % 10 == 0:
                print(f"Completed step {step}/{n_steps}...  UFR = {urf:.2e}")
            if urf >= 1.0:
                print(f"Diverged at step {step} (UFR = {urf:.2e} >= 1.0). Stopping.")
                break
            _jump_window = 100
            if len(urf_history) > _jump_window:
                baseline = np.mean(urf_history[-_jump_window - 1 : -1])
                if urf > baseline * 3.5:
                    print(f"Failure detected at step {step} (UFR jumped from ~{baseline:.2e} to {urf:.2e}). Stopping.")
                    break
            if urf < urf_threshold:
                print(f"Converged at step {step} (UFR = {urf:.2e} < {urf_threshold:.2e}). Stopping early.")
                break
        elif step % 10 == 0:
            print(f"Completed step {step}/{n_steps}...")

        if step % 10 == 0:
            result = solver.last_result
            force_time.append([result.interaction_force_magnitude[i] for i in range(len(result.interaction_bodies))])

    solver.force_time = force_time
    solver.urf_history = urf_history
    solver.displacement_history = displacement_history

    print("LMGC90 solver run complete.")
    return solver
