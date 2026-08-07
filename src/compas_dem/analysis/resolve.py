from compas.geometry import Vector
from compas_cgal.measure import mesh_volume
from compas_dem.problem.boundary_condition import LOADING_TYPES
from compas_dem.problem.boundary_condition import check_loading_type


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


def _as_list(boundary_conditions) -> list:
    """Accept either a single boundary condition or a collection of them."""
    if isinstance(boundary_conditions, (list, tuple)):
        return list(boundary_conditions)
    return [boundary_conditions]


def resolve_centroidal_loads(model, boundary_conditions) -> dict:
    """Resolve the loads of the given boundary conditions to (force, moment) pairs at each block centroid.

    Handles body forces, point loads (with explicit point or moment), and
    surface loads (converted to equivalent point loads at face centroids).
    Gravity is intentionally excluded — each solver applies it through its
    own mechanism.

    Which boundary conditions to resolve is the caller's decision: the solvers pass
    ``problem.boundary_conditions``.

    Parameters
    ----------
    model : :class:`~compas_dem.models.BlockModel`
    boundary_conditions : :class:`~compas_dem.problem.BoundaryConditionGroup` | list[:class:`~compas_dem.problem.BoundaryConditionGroup`]
        The boundary condition(s) to resolve. Multiple boundary conditions are summed together.

    Returns
    -------
    dict[int, dict]
        ``{block_index: {"force": Vector, "moment": Vector, "by_loading_type": {str: {"force": Vector, "moment": Vector}}}}``

        ``force`` and ``moment`` are the totals over every loading type, which is what
        the static solvers apply. ``by_loading_type`` keeps the same totals split per
        loading type, so a time-stepping solver can give each its own time series
        instead of having to pick one for the whole block.
    """
    boundary_conditions = _as_list(boundary_conditions)
    blocks = {block.graphnode: block for block in model.elements()}

    loads = {
        idx: {
            "force": Vector(0, 0, 0),
            "moment": Vector(0, 0, 0),
            "by_loading_type": {lt: {"force": Vector(0, 0, 0), "moment": Vector(0, 0, 0)} for lt in LOADING_TYPES},
        }
        for idx in blocks
    }

    def accumulate(idx: int, force: Vector, moment: Vector, loading_type: str) -> None:
        check_loading_type(loading_type)
        loads[idx]["force"] += force
        loads[idx]["moment"] += moment
        bucket = loads[idx]["by_loading_type"][loading_type]
        bucket["force"] += force
        bucket["moment"] += moment

    for bc in boundary_conditions:
        for entry in bc.body_forces:
            a_vec = Vector(*entry.acceleration)
            for idx, block in blocks.items():
                accumulate(idx, a_vec * _element_mass(block), Vector(0, 0, 0), entry.loading_type)

        for entry in bc.point_loads:
            idx = entry.block_index
            if idx not in blocks:
                raise ValueError(f"Point load references block_index={idx} which does not exist in the model.")
            force = Vector(*(entry.force or [0.0, 0.0, 0.0]))
            if entry.point is not None:
                r = Vector(*entry.point) - blocks[idx].point
                moment = r.cross(force)
            elif entry.moment is not None:
                moment = Vector(*entry.moment)
            else:
                moment = Vector(0, 0, 0)
            accumulate(idx, force, moment, entry.loading_type)

        for entry in bc.surface_loads:
            idx = entry.block_index
            if idx not in blocks:
                raise ValueError(f"Surface load references block_index={idx} which does not exist in the model.")
            block = blocks[idx]
            loading_point = block.modelgeometry.face_center(entry.face_index)
            area = block.modelgeometry.face_area(entry.face_index)
            force = Vector(*entry.load) * area
            r = Vector(*loading_point) - block.point
            moment = r.cross(force)
            accumulate(idx, force, moment, entry.loading_type)

    return loads


def resolve_centroidal_displacements(boundary_conditions) -> dict:
    """Resolve the prescribed displacements and rotations of the given boundary conditions, per block index.

    Which boundary conditions to resolve is the caller's decision: the solvers pass
    ``problem.boundary_conditions``. Supports are not part of the boundary conditions;
    they come from the model (``block.is_support``).

    Parameters
    ----------
    boundary_conditions : :class:`~compas_dem.problem.BoundaryConditionGroup` | list[:class:`~compas_dem.problem.BoundaryConditionGroup`]
        The boundary condition(s) to resolve. Multiple boundary conditions are merged
        together, per component.

    Returns
    -------
    dict[int, dict]
        ``{block_index: {"translation": list, "rotation": list}}``
        Components are ``None`` where unconstrained.

    """
    displacements = {}

    for bc in _as_list(boundary_conditions):
        for entry in bc.displacements:
            idx = entry.block_index
            if idx not in displacements:
                displacements[idx] = {"translation": [None, None, None], "rotation": [None, None, None]}
            for key in ("translation", "rotation"):
                components = getattr(entry, key, None)
                if components is not None:
                    for j, v in enumerate(components):
                        if v is not None:
                            displacements[idx][key][j] = v

    return displacements
