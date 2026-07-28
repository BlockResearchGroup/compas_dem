from collections import defaultdict

import numpy as np

import compas.geometry as cg
from compas_dem.analysis.resolve import _element_mass
from compas_dem.analysis.resolve import resolve_centroidal_displacements
from compas_dem.analysis.resolve import resolve_centroidal_loads
from compas_dem.interactions import EdgeContact
from compas_dem.interactions import FrictionContact
from compas_dem.interactions import VertexContact
from compas_dem.models import BlockModel
from compas_dem.problem.problem import Problem
from compas_dem.problem.results import Results

try:
    from compas_lmgc90.solver import Solver
except (ImportError, FileNotFoundError):
    raise ImportError("compas_lmgc90 is not installed. Install it to use the LMGC90 solver.")


# ---------------------------------------------------------------------------
# UFR – Unbalanced Force Ratio
# ---------------------------------------------------------------------------


def compute_urf(solver: Solver, problem: Problem, model: BlockModel) -> float:
    """Return the Unbalanced Force Ratio for the current simulation step.

    UFR = Σ_i |F_i_net| / ( Σ_i |F_i_applied| + Σ_ij |F_ij_contact| )
    """
    result = solver.last_result
    blocks = {b.graphnode: b for b in model.elements()}
    lmgc_to_graphnode = {i: el.graphnode for i, el in enumerate(model.elements())}

    g_vec = np.array([0.0, 0.0, -9.81])
    centroidal_loads = resolve_centroidal_loads(problem, model)

    applied_forces = {}
    for idx, block in blocks.items():
        external = np.asarray(list(centroidal_loads[idx]["force"]), dtype=float)
        gravity = _element_mass(block) * g_vec
        applied_forces[idx] = external + gravity

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
    model: BlockModel,
    contact_law: str = "IQS_CLB",
    duration: float = None,
    n_steps: int = None,
    dt: float = None,
    theta: float = 0.7,
    urf_threshold: float = None,
    track_block: int = None,
    verbose: int = 0,
) -> Solver:
    """
    Translate a Problem into a configured LMGC90 Solver. Run the simulation and
    post-process results back into the BlockModel in-place.

    Parameters
    ----------
    problem : :class:`~compas_dem.problem.Problem`
        The problem containing forces, BCs, and contact properties.
    model : :class:`~compas_dem.models.BlockModel`
        The block model to solve.
    contact_law : str, optional
        LMGC90 contact law identifier. Default ``"IQS_CLB"``.
    duration : float, optional
        Total simulation time [s].
    n_steps : int, optional
        Number of time steps.
    dt : float, optional
        Time step size [s].
    theta : float, optional
        Time-integration parameter. Default ``0.7``.
    urf_threshold : float, optional
        Unbalanced Force Ratio convergence threshold.

    Returns
    -------
    :class:`compas_lmgc90.solver.Solver`
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

    # ------------------------------------------------------------------
    # Density: first block with material, or fallback
    # ------------------------------------------------------------------
    density = None
    for block in model.blocks():
        if block.material and block.material.density:
            density = block.material.density
            break

    # ------------------------------------------------------------------
    # Contact friction
    # ------------------------------------------------------------------
    if problem.contact_properties.contact_model:
        mu = problem.contact_properties.contact_model.mu
    else:
        raise Warning("No contact properties with a contact model found in the problem; defaulting to mu=0.6.")

    # ------------------------------------------------------------------
    # Resolve BCs
    # ------------------------------------------------------------------
    if len(problem.loadcases) > 1:
        raise NotImplementedError("LMGC90 solver currently supports only one loadcase per problem.")

    centroidal_displacements = resolve_centroidal_displacements(problem)
    centroidal_loads = resolve_centroidal_loads(problem, model)

    # Mark fully-fixed blocks as supports on the model
    for block in model.elements():
        idx = block.graphnode
        disp = centroidal_displacements.get(idx)
        if disp is not None:
            t = disp["translation"] or [0.0, 0.0, 0.0]
            r = disp["rotation"] or [0.0, 0.0, 0.0]
            if all(v == 0.0 for v in t) and all(v == 0.0 for v in r):
                block.is_support = True

    solver = Solver(density=density, dt=dt, theta=theta)
    solver.geometry_from_model(model)
    # ------------------------------------------------------------------
    # Displacement BCs → apply_velocity
    # ------------------------------------------------------------------
    for i, block in enumerate(model.elements()):
        idx = block.graphnode
        disp = centroidal_displacements.get(idx)
        if disp is None:
            continue

        translation = disp["translation"] or [None, None, None]
        rotation = disp["rotation"] or [None, None, None]

        for component, value in zip(["Vx", "Vy", "Vz"], translation):
            if value is not None:
                solver.apply_velocity(
                    block_index=i,
                    component=component,
                    value=np.array([[0.0, duration], [value / duration, 0.0]]),
                )
        for component, value in zip(["Rx", "Ry", "Rz"], rotation):
            if value is not None:
                solver.apply_velocity(
                    block_index=i,
                    component=component,
                    value=np.array([[0.0, duration], [value / duration, 0.0]]),
                )

    # ------------------------------------------------------------------
    # Applied forces → per-axis time series
    # ------------------------------------------------------------------
    t_series = np.array([0.0, duration * 0.98, duration])

    for idx, entry in centroidal_loads.items():
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
        if step == 0:
            result = solver.lmgc90.compute_one_step()

            for i, block in enumerate(model.elements()):
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
                urf = compute_urf(solver, problem, model)
                urf_history.append(urf)
                print(f"Completed step {step}/{n_steps}...  UFR = {urf:.2e}")
                if urf >= 1.0:
                    print(f"Diverged at step {step} (UFR = {urf:.2e} >= 1.0). Stopping.")
                    break

                _jump_window = 200
                _Max_URF_JUMP_FACTOR = 3.5

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

    solver.force_time = force_time
    solver.urf_history = urf_history
    solver.displacement_history = displacement_history

    print("LMGC90 solver run complete.")
    results = _post_processing_lmgc90(solver, problem, model)
    results.metadata["mu"] = mu
    results.metadata["force_time"] = force_time
    results.metadata["urf_history"] = urf_history
    results.metadata["n_steps"] = step + 1
    results.metadata["displacement_history"] = [d.tolist() for d in displacement_history]

    solver.name = "LMGC90"
    solver.finalize()

    return results


def _contact_axes(result, p: int) -> tuple:
    """Return ``(t1, t2, n)`` for contact point ``p``, ordered so that ``t1 x t2 == n``.

    LMGC90's local frame is ``(t, n, s)`` with ``t x n == s``, hence ``t x s == -n``.
    Using LMGC90's ``s`` directly as the frame y-axis therefore yields a frame whose
    z-axis is *minus* the contact normal. We instead take ``t2 = n x t``, which is
    exactly ``-s``, so the resulting frame has ``zaxis == n`` as every consumer
    (:class:`FrictionContact`, :class:`EdgeContact`, the viewer) expects.
    """
    n = cg.Vector(*result.interaction_normals[p])
    t1 = cg.Vector(*result.interaction_tangent1[p])
    t2 = n.cross(t1).unitized()  # == -interaction_tangent2[p]
    return t1, t2, n


def _contact_forces(result, p: int) -> dict:
    """Return the force at contact point ``p`` in the frame built by :func:`_contact_axes`.

    LMGC90 reports ``rloc = (Ft, Fn, Fs)`` in its own ``(t, n, s)`` frame, and
    ``Ft*t + Fn*n + Fs*s`` reproduces ``interaction_force_global`` exactly. Since the
    frame's y-axis is ``-s``, the component along it is ``-Fs``; the components along
    ``t`` and ``n`` are taken as-is.
    """
    Ft, Fn, Fs = result.interaction_rloc[p]
    return {"c_np": max(Fn, 0.0), "c_nn": max(-Fn, 0.0), "c_u": Ft, "c_v": -Fs}


def _process_contact_points(result, points: list) -> list[dict]:
    """Return a list of dicts containing contact point data for the given LMGC90 contact indices.

    Each dict contains:
        - "point": :class:`compas.geometry.Point` of the contact point
        - "indices": list of LMGC90 contact indices that coincide at this point
        - "fn": net normal force (positive = tension, negative = compression)
        - "c_u": tangential force along t1
        - "c_v": tangential force along t2
    """
    merged: list[dict] = []
    for p in points:
        pt = cg.Point(*result.interaction_coords[p])
        f = _contact_forces(result, p)
        entry = next((m for m in merged if m["point"] == pt), None)
        if entry is None:
            merged.append(
                {
                    "point": pt,
                    "indices": [p],
                    "fn": f["c_np"] - f["c_nn"],
                    "c_u": f["c_u"],
                    "c_v": f["c_v"],
                }
            )
        else:
            entry["indices"].append(p)
            entry["fn"] += f["c_np"] - f["c_nn"]
            entry["c_u"] += f["c_u"]
            entry["c_v"] += f["c_v"]

    for m in merged:
        m["forces"] = {
            "c_np": max(m["fn"], 0.0),
            "c_nn": max(-m["fn"], 0.0),
            "c_u": m["c_u"],
            "c_v": m["c_v"],
        }
    return merged


def _local_resultant(merged: list[dict]) -> np.ndarray:
    """Return a contact's resultant force in its own frame, as ``[Fu, Fv, Fn]``.

    Parameters
    ----------
    merged : list[dict]
        Contact points as returned by :func:`_process_contact_points`.

    Returns
    -------
    ``[Fu, Fv, Fn]``, or a zero vector if the contact carries no points.
    """
    if not merged:
        return [0, 0, 0]
    return [
        sum(m["c_u"] for m in merged),
        sum(m["c_v"] for m in merged),
        sum(m["fn"] for m in merged),
    ]


def _post_processing_lmgc90(solver: "Solver", problem: Problem, model: BlockModel) -> Results:
    """Build a standalone :class:`~compas_dem.problem.Results` from LMGC90 solver output.

    Does **not** mutate the model or its graph. All data is written only to the
    returned :class:`Results` object, which can be serialized independently via
    ``compas.json_dump``.

    Parameters
    ----------
    solver : :class:`compas_lmgc90.solver.Solver`
    problem : :class:`~compas_dem.problem.Problem`
    model : :class:`~compas_dem.models.BlockModel`

    Returns
    -------
    :class:`~compas_dem.problem.Results`
    """
    results = Results(model_id=str(model.guid), problem_id=str(problem.guid))

    elements = list(model.elements())
    contact_data = solver.get_contacts()
    result = solver.last_result

    # LMGC90 body ids are 1-based indices into ``model.elements()``; the graph node
    # of an element is not guaranteed to be that same index.
    lmgc_to_graphnode = {i: el.graphnode for i, el in enumerate(elements)}

    # ------------------------------------------------------------------
    # Node data — block transformations
    # ------------------------------------------------------------------
    for i, block in enumerate(elements):
        pos = np.array(result.bodies[i])
        rot = np.array(result.body_frames[i]).reshape(3, 3)
        new_frame = cg.Frame(pos, rot[0, :], rot[1, :])
        T = cg.Transformation.from_frame_to_frame(block.init_frame, new_frame)
        results.set_node(block.graphnode, "transformation", T)

    # LMGC90 key -> Results key. ``force_tangent2`` is written separately below: LMGC90
    # reports it along ``s``, while the contact frame stored here uses ``-s`` as y-axis.
    _per_point_keys = [
        "contact_points",
        "gaps",
        "status",
    ]
    _new_key_name = [
        "contact_points",
        "gap",
        "status",
    ]

    # Group solver contact indices by body pair
    contact_groups: dict[tuple, list] = {}
    for i in range(len(result.interaction_coords)):
        body_pair = tuple(sorted(lmgc_to_graphnode[b - 1] for b in result.interaction_bodies[i]))
        if body_pair not in contact_groups:
            contact_groups[body_pair] = []
        contact_groups[body_pair].append(i)

    # ------------------------------------------------------------------
    # Edge data — contacts
    # ------------------------------------------------------------------
    graph = model.graph
    for pair, points in contact_groups.items():
        u, v = pair

        if not points:
            continue

        # Determine canonical edge direction from the graph (read-only).
        # If neither direction exists, record it so model.attach() can add it.
        if graph.has_edge((u, v)):
            edge = (u, v)
        elif graph.has_edge((v, u)):
            edge = (v, u)
        else:
            edge = (u, v)
            results.metadata.setdefault("added_edges", []).append(list(edge))

        results.set_edge(edge, "face_contact", False)
        results.set_edge(edge, "point_contact", False)
        results.set_edge(edge, "edge_contact", False)

        # Coincident interactions are merged first, so that every per-point array below
        # and the contact object's own points stay the same length.
        lmgc90_contacts = _process_contact_points(result, points)
        if len(lmgc90_contacts) != len(points):
            results.metadata.setdefault("merged_contacts", {})[f"{edge[0]},{edge[1]}"] = [len(points), len(lmgc90_contacts)]

        # ``gap`` and ``status`` describe the interaction itself, so a merged point takes
        # them from its first constituent. Force components are summed over the merge.
        for k, name in zip(_per_point_keys, _new_key_name):
            results.set_edge(edge, name, [contact_data[k][m["indices"][0]] for m in lmgc90_contacts])
        results.set_edge(edge, "contact_points", [list(m["point"]) for m in lmgc90_contacts])
        results.set_edge(edge, "force_normal", [m["fn"] for m in lmgc90_contacts])
        results.set_edge(edge, "force_tangent1", [m["c_u"] for m in lmgc90_contacts])
        results.set_edge(edge, "force_tangent2", [m["c_v"] for m in lmgc90_contacts])

        # ``interaction_force_global`` is the force on the *candidate* body of each
        # interaction. Record which node that is so the sign of "force" is unambiguous,
        # and flip any point whose candidate is the other node before summing.
        def _signed(p):
            sign = 1.0 if lmgc_to_graphnode[result.interaction_bodies[p][0] - 1] == edge[0] else -1.0
            return sign * np.asarray(result.interaction_force_global[p], dtype=float)

        force_vectors = [np.sum([_signed(p) for p in m["indices"]], axis=0).tolist() for m in lmgc90_contacts]
        resultant = np.sum(force_vectors, axis=0)

        local_resultant = _local_resultant(lmgc90_contacts)
        results.set_edge(edge, "resultant_local", local_resultant)
        # results.set_edge(edge, "force_on_node", edge[0])
        results.set_edge(edge, "force_vector", force_vectors)
        results.set_edge(edge, "resultant_global", resultant.tolist())
        # Magnitude of the resultant, consistent with "force" and with the other backends.
        results.set_edge(edge, "force_magnitude", float(np.linalg.norm(resultant)))
        results.set_edge(edge, "nodal_force_magnitudes", [float(np.linalg.norm(f)) for f in force_vectors])

        contact_frames = [cg.Frame(m["point"], *_contact_axes(result, m["indices"][0])[:2]) for m in lmgc90_contacts]
        results.set_edge(edge, "contact_frames", contact_frames)
        results.set_edge(edge, "contact_frame", contact_frames[0])

        contact_pts = [m["point"] for m in lmgc90_contacts]
        forces = [m["forces"] for m in lmgc90_contacts]
        t1, t2, _ = _contact_axes(result, points[0])

        if len(contact_pts) >= 3:
            results.set_edge(edge, "contact_polygon", cg.Polygon(contact_pts))
            results.set_edge(edge, "face_contact", True)
            fc = FrictionContact(points=contact_pts)
            fc._frame = cg.Frame(contact_frames[0].point, t1, t2)
            fc.forces = forces
            results.set_edge(edge, "contact_data", fc)

        elif len(contact_pts) == 2:
            line = cg.Line(contact_pts[0], contact_pts[1])
            ec = EdgeContact(
                points=contact_pts,
                frame=cg.Frame(line.midpoint, t1, t2),
                forces=forces,
            )
            results.set_edge(edge, "edge_contact", True)
            results.set_edge(edge, "contact_data", ec)
            results.set_edge(edge, "contact_geometry", line)

        elif len(contact_pts) == 1:
            results.set_edge(edge, "point_contact", True)
            vc = VertexContact(
                point=contact_pts[0],
                frame=cg.Frame(contact_pts[0], t1, t2),
                forces=forces,
            )
            results.set_edge(edge, "contact_data", vc)
            results.set_edge(edge, "contact_geometry", contact_pts[0])

        else:
            print(f"Warning: contact between bodies {u} and {v} has no contact points.")

    return results
