from compas.geometry import Vector
from compas_cgal.measure import mesh_volume


def _element_mass(element) -> float:
    """Return the mass of any model element in [kg].

    Uses the element's `mass` property if available (Block), otherwise
    computes density × volume directly from `material` and `modelgeometry`.
    """
    if hasattr(element, "mass"):
        return element.mass
    if element.material is None or element.material.density is None:
        raise ValueError(f"Element at node {element.graphnode} ({type(element).__name__}) has no material with a density assigned.")
    volume = mesh_volume(element.modelgeometry.to_vertices_and_faces(True))
    return element.material.density * volume


def resolve_centroidal_loads(problem, model, loadcase=None) -> dict:
    """Resolve load-case loads to (force, moment) pairs at each block centroid.

    Handles body forces, point loads (with explicit point or moment), and
    surface loads (converted to equivalent point loads at face centroids).
    Gravity is intentionally excluded — each solver applies it through its
    own mechanism.

    Parameters
    ----------
    problem : :class:`~compas_dem.problem.Problem`
    model : :class:`~compas_dem.models.BlockModel`
    loadcase : :class:`~compas_dem.problem.LoadCase`, optional
        Resolve only this load case. If ``None`` (default), all of the
        problem's load cases are summed together.

    Returns
    -------
    dict[int, dict]
        ``{block_index: {"force": Vector, "moment": Vector, "loading_type": str}}``
    """
    blocks = {block.graphnode: block for block in model.elements()}
    loadcases = [loadcase] if loadcase is not None else [problem.loadcases[0]]

    loads = {idx: {"force": Vector(0, 0, 0), "moment": Vector(0, 0, 0), "loading_type": "ramp"} for idx in blocks}

    for lc in loadcases:
        for acc in lc.body_forces:
            a_vec = Vector(*acc)
            for idx, block in blocks.items():
                loads[idx]["force"] += a_vec * _element_mass(block)

        for entry in lc.point_loads:
            idx = entry["block_index"]
            if idx not in blocks:
                raise ValueError(f"Point load references block_index={idx} which does not exist in the model.")
            force = Vector(*entry["force"])
            if entry["point"] is not None:
                r = Vector(*entry["point"]) - blocks[idx].point
                moment = r.cross(force)
            elif entry["moment"] is not None:
                moment = Vector(*entry["moment"])
            else:
                moment = Vector(0, 0, 0)
            loads[idx]["force"] += force
            loads[idx]["moment"] += moment
            loads[idx]["loading_type"] = entry["loading_type"]

        for entry in lc.surface_loads:
            idx = entry["block_index"]
            if idx not in blocks:
                raise ValueError(f"Surface load references block_index={idx} which does not exist in the model.")
            block = blocks[idx]
            loading_point = block.modelgeometry.face_center(entry["face_index"])
            area = block.modelgeometry.face_area(entry["face_index"])
            force = Vector(*entry["load"]) * area
            r = Vector(*loading_point) - block.point
            moment = r.cross(force)
            loads[idx]["force"] += force
            loads[idx]["moment"] += moment
            loads[idx]["loading_type"] = entry["loading_type"]

    return loads


def resolve_centroidal_displacements(problem, loadcase=None) -> dict:
    """Resolve prescribed displacements and rotations per block index.

    Parameters
    ----------
    problem : :class:`~compas_dem.problem.Problem`
    loadcase : :class:`~compas_dem.problem.LoadCase`, optional
        Resolve only this load case. If ``None`` (default), all of the
        problem's load cases are merged together.

    Returns
    -------
    dict[int, dict]
        ``{block_index: {"translation": list, "rotation": list}}``
        Components are ``None`` where unconstrained.
    """
    displacements = {}
    loadcases = [loadcase] if loadcase is not None else [problem.loadcases[0]]
    for lc in loadcases:
        for entry in lc.displacements:
            idx = entry["block_index"]
            if idx not in displacements:
                displacements[idx] = {"translation": [None, None, None], "rotation": [None, None, None]}
            if entry["translation"] is not None:
                for j, v in enumerate(entry["translation"]):
                    if v is not None:
                        displacements[idx]["translation"][j] = v
            if entry["rotation"] is not None:
                for j, v in enumerate(entry["rotation"]):
                    if v is not None:
                        displacements[idx]["rotation"][j] = v
    return displacements
