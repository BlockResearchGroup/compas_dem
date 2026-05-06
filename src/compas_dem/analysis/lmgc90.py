from collections import defaultdict

import compas.geometry as cg
import numpy as np

from compas_dem.interactions import EdgeContact
from compas_dem.interactions import FrictionContact
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
    lmgc_to_graphnode = {i: el.graphnode for i, el in enumerate(problem.model.elements())}

    # Applied forces from the problem plus LMGC90's always-on gravity
    g_vec = np.array([0.0, 0.0, -9.81])
    applied_forces = {}
    for idx, block in problem._blocks.items():
        external = np.asarray(list(problem.centroidal_loads[idx]["force"]), dtype=float)
        mass = getattr(block, "mass", None)
        gravity = mass * g_vec if mass is not None else np.zeros(3)
        applied_forces[idx] = external + gravity

    # Net contact force per body — interaction_bodies uses 1-based LMGC90 indices
    contact_net: dict = defaultdict(lambda: np.zeros(3))
    for i in range(len(result.interaction_bodies)):
        cd_id, an_id = result.interaction_bodies[i]
        f = np.asarray(result.interaction_force_global[i], dtype=float)
        contact_net[lmgc_to_graphnode[cd_id - 1]] += f
        contact_net[lmgc_to_graphnode[an_id - 1]] -= f

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
    """Translate a Problem into a configured LMGC90 Solver. Run the simulation and
    Postprocess results back into the Problem's BlockModel in-place after the run (refer
    to :func:`_post_processing_lmgc90` for details).

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
    density = 2000.0
    for block in model.blocks():
        if block.material and block.material.density:
            density = block.material.density
            break

    # ------------------------------------------------------------------
    # Contact friction: last contact properties added to the problem
    # ------------------------------------------------------------------
    if problem.contact_properties.contact_model:
        mu = problem.contact_properties.contact_model.mu
    else:
        Warning("No contact properties with a contact model found in the problem; defaulting to mu=0.6.")
        mu = 0.6
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
        if disp is None:
            continue

        translation = disp["translation"] or [None, None, None]
        rotation = disp["rotation"] or [None, None, None]

        for component, value in zip(["Vx", "Vy", "Vz"], translation):
            if value is not None:
                solver.apply_velocity(block_index=idx, component=component, value=value / duration)
        for component, value in zip(["Rx", "Ry", "Rz"], rotation):
            if value is not None:
                solver.apply_velocity(block_index=idx, component=component, value=value / duration)

    # ------------------------------------------------------------------
    # Applied forces: decompose centroidal (force, moment) into per-axis
    # time series — The three values inputted are at t=0, t=duration*0.9, and t=duration, allowing for ramped or instantaneous loading.
    # ------------------------------------------------------------------
    t_series = np.array([0.0, duration * 0.98, duration])
    # t_series = np.array([0.0, duration * 0.2, 0.8*duration, duration * 0.98])

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

    # raise NotImplementedError("The LMGC90 solver run loop and postprocessing are still being developed. This function is not yet complete.")
    force_time = []
    urf_history = []
    displacement_history = []
    initial_pos = np.array(solver.trimeshes[track_block].centroid()) if track_block is not None else None
    print("Starting LMGC90 solver analysis...")
    for step in range(n_steps):
        if step == 0:
            result = solver.lmgc90.compute_one_step()

            for i, block in enumerate(problem.model.elements()):
                pos = np.array(result.bodies[i])
                rot = np.array(result.body_frames[i]).reshape(3, 3)
                block.init_frame = cg.Frame(pos, rot[0, :], rot[1, :])

            solver._update_meshes(result)
            solver.last_result = result

        else:
            solver.run(nb_steps=1)

        if track_block is not None:
            current_pos = np.array(solver.trimeshes[track_block].centroid())
            displacement_history.append(current_pos - initial_pos)

        if urf_threshold is not None:
            if step % 10 == 0:
                urf = compute_urf(solver, problem)
                urf_history.append(urf)
                print(f"Completed step {step}/{n_steps}...  UFR = {urf:.2e}")
                if urf >= 1.0:
                    print(f"Diverged at step {step} (UFR = {urf:.2e} >= 1.0). Stopping.")
                    break

                _jump_window = 200  # Ignores URF jumps in the first n steps
                # Allows the solver to stabilize initially

                _Max_URF_JUMP_FACTOR = 3.5  # If UFR jumps by more than this factor compared to the recent average, consider it a failure

                if len(urf_history) > _jump_window:
                    baseline = np.mean(urf_history[-_jump_window - 1 : -1])
                    if urf > baseline * _Max_URF_JUMP_FACTOR:
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

        # This is the solver loop, New tracking functions can be added here,
        # Such as tracking specific contact forces, displacements, or other quantities of interest at each step.

    solver.force_time = force_time
    solver.urf_history = urf_history
    solver.displacement_history = displacement_history

    print("LMGC90 solver run complete.")
    _post_processing_lmgc90(solver, problem)

    solver.name = "LMGC90"

    solver.finalize()

    return


def _post_processing_lmgc90(solver: "Solver", problem: Problem) -> None:
    """Post-process results from the LMGC90 solver into BlockModel on the graph's edges and nodes.


    Block attributes set
    --------------------
    displacement : list[float]
        [dx, dy, dz] between initial and final centroid positions.
    deformed_mesh : :class:`compas.datastructures.Mesh`
        The deformed mesh from the solver.

    Edge attributes set
    -------------------
    contacts : dict
        Per-contact-point data aggregated for that interface:
        ``contact_point``, ``force_magnitude``, ``force_vector``,
        ``contact_polygon``, ``gap``, ``status``.
    """
    elements = list(problem.model.elements())
    contact_data = solver.get_contacts()
    result = solver.last_result
    model = problem.model

    # ==============================================================================
    # Annotate each block result via graph node attribute (serializable)
    # Attribute: "transformation"
    # ==============================================================================
    for i, block in enumerate(elements):
        pos = np.array(result.bodies[i])
        rot = np.array(result.body_frames[i]).reshape(3, 3)
        new_frame = cg.Frame(pos, rot[0, :], rot[1, :])
        T = cg.Transformation.from_frame_to_frame(block.init_frame, new_frame)
        model.graph.node_attribute(block.graphnode, "transformation", T)

    # ==============================================================================
    # Annotate contact results via graph edge attributes (serializable)
    # Attributes: "contact_point", "force_magnitude", "force_vector", "contact_polygon", "gap", "status"
    # ==============================================================================
    # Contact attributes are extracted from LMGC90's per contact point data.

    _per_point_keys = [
        "contact_points",
        "force_normal",
        "force_tangent1",
        "force_tangent2",
        "gaps",
        "status",
    ]
    _new_key_name = [
        "contact_point",
        "force_normal",
        "force_tangent1",
        "force_tangent2",
        "gap",
        "status",
    ]

    # ==============================================================================
    # Group contact points by body pairs - Taken directly from compas_LMGC90's post-processing method.
    # ==============================================================================
    contact_groups = {}
    for i in range(len(solver.last_result.interaction_coords)):
        body_pair = tuple(sorted(b - 1 for b in solver.last_result.interaction_bodies[i]))
        if body_pair not in contact_groups:
            contact_groups[body_pair] = []
        contact_groups[body_pair].append(i)

    # ==============================================================================
    # Recall Last result from LMGC90

    result = solver.last_result
    graph = problem.model.graph

    # Loop through LMGC90's contact pairs and indices of contact points.

    for pair, points in contact_groups.items():
        u, v = pair

        if not points:
            continue

        # -----------------------------------------------------------------------------
        # LMGC90 body pairs are undirected (sorted); compas graph edges are directed.
        # Checking for both orientations if they exist and setting the edge accordingly.
        if graph.has_edge((u, v)):
            edge = (u, v)
        elif graph.has_edge((v, u)):
            edge = (v, u)
        else:
            if not graph.has_node(u) or not graph.has_node(v):
                print(f"Warning: body {u} or {v} not in model graph (support/boundary body). Skipping contact.")
                continue
            print(f"Warning: contact between bodies {u} and {v} has no corresponding edge in the model graph. Adding edge.")
            graph.add_edge(u, v)
            edge = (u, v)
        # -----------------------------------------------------------------------------

        # per-point contact data
        # -------
        for k, name in zip(_per_point_keys, _new_key_name):
            graph.edge_attribute(edge, name, [contact_data[k][i] for i in points])
        graph.edge_attribute(
            edge,
            "force_magnitude",
            float(np.linalg.norm(np.sum([result.interaction_force_global[p] for p in points], axis=0))),
        )
        graph.edge_attribute(
            edge,
            "force_vector",
            [list(result.interaction_force_global[p]) for p in points],
        )
        graph.edge_attribute(
            edge,
            "force",
            np.sum([result.interaction_force_global[p] for p in points], axis=0).tolist(),
        )
        # -----------------------------------------------------------------------------

        # Identify contact type based on the number of contact points and set attributes accordingly.
        # ----------
        graph.edge_attribute(edge, "face_contact", False)
        graph.edge_attribute(edge, "point_contact", False)
        graph.edge_attribute(edge, "edge_contact", False)

        contact_frames = [
            cg.Frame(
                point=cg.Point(*result.interaction_coords[p]),
                xaxis=cg.Vector(*result.interaction_tangent1[p]),
                yaxis=cg.Vector(*result.interaction_normals[p]),
            )
            for p in points
        ]

        graph.edge_attribute(edge, "contact_frame", contact_frames[0])

        polygon_pts = [result.interaction_coords[p] for p in points]

        fv_vecs = graph.edge_attribute(edge, "force_vector")
        contact_pts = graph.edge_attribute(edge, "contact_point")
        contact_frames = graph.edge_attribute(edge, "contact_frame")

        if len(polygon_pts) >= 3:
            graph.edge_attribute(edge, "contact_polygon", cg.Polygon(polygon_pts))

            graph.edge_attribute(edge, "face_contact", True)
            fc = FrictionContact(points=[cg.Point(*p) for p in contact_pts])
            lmgc_normal = contact_frames.yaxis
            lmgc_tangent = contact_frames.xaxis
            tangent2 = lmgc_normal.cross(lmgc_tangent).unitized()
            fc._frame = cg.Frame(contact_frames.point, lmgc_tangent, tangent2)
            frame = fc.frame
            fc.forces = [
                {
                    "c_np": max(cg.Vector(*fv).dot(frame.zaxis), 0),
                    "c_nn": max(-cg.Vector(*fv).dot(frame.zaxis), 0),
                    "c_u": cg.Vector(*fv).dot(frame.xaxis),
                    "c_v": cg.Vector(*fv).dot(frame.yaxis),
                }
                for fv in fv_vecs
            ]
            graph.edge_attribute(edge, "contact_data", fc)

        elif len(polygon_pts) == 2:
            print(f"Edge contact between bodies {u} and {v} with contact points {polygon_pts}. Setting edge_contact=True.")
            graph.edge_attribute(edge, "edge_contact", True)

            lmgc_normal = contact_frames.yaxis
            lmgc_tangent = contact_frames.xaxis
            tangent2 = lmgc_normal.cross(lmgc_tangent).unitized()

            ec = EdgeContact(
                points=[cg.Point(*p) for p in polygon_pts],
                frame=cg.Frame(
                    cg.Line(cg.Point(*polygon_pts[0]), cg.Point(*polygon_pts[1])).midpoint,
                    lmgc_tangent,
                    tangent2,
                ),
            )
            ec.forces = [
                {
                    "c_np": max(cg.Vector(*fv).dot(ec.frame.zaxis), 0),
                    "c_nn": max(-cg.Vector(*fv).dot(ec.frame.zaxis), 0),
                    "c_u": cg.Vector(*fv).dot(ec.frame.xaxis),
                    "c_v": cg.Vector(*fv).dot(ec.frame.yaxis),
                }
                for fv in fv_vecs
            ]
            graph.edge_attribute(edge, "edge_contact", True)
            graph.edge_attribute(edge, "contact_data", ec)

        elif len(polygon_pts) == 1:
            graph.edge_attribute(edge, "point_contact", True)

        else:
            print(f"Warning: contact between bodies {u} and {v} has no contact points. This is unexpected; check LMGC90 results.")

        # ------------------------------------------------------------------------------
        # --- contact frames (T, N at each contact point) ---
        contact_frames = [
            cg.Frame(
                result.interaction_coords[p],
                result.interaction_tangent1[p],
                result.interaction_normals[p],
            )
            for p in points
        ]
        graph.edge_attribute(edge, "contact_frames", contact_frames)
