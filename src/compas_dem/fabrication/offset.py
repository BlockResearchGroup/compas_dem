from typing import Optional

from compas.datastructures import Mesh
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Vector
from compas.geometry import distance_point_point_sqrd
from compas.geometry import intersection_line_plane
from compas.geometry import intersection_plane_plane
from compas.geometry import is_parallel_vector_vector
from compas.itertools import pairwise


def offset_planar_blocks(
    mesh: Mesh,
    offset: float = 0.0,
    chamfer: float = 0.05,
    thickness_scale_bottom: float = 0.0,
    thickness_scale_top: float = 1.0,
    project_bottom: bool = True,
    project_top: bool = False,
    tolerance_parallel: float = 0.5,
) -> list[Mesh]:
    """
    Offset a mesh to create blocks with planar sides and chamfered corners.

    Parameters
    ----------
    mesh : :class:`compas.datastructures.Mesh`
        A mesh.
    offset : float
        The offset distance.
    chamfer : float
        The chamfer distance.
    thickness_scale_bottom : float
        The thickness scale for the bottom.
    thickness_scale_top : float
        The thickness scale for the top.
    project_bottom : bool
        Whether to project the bottom face of the mesh.
    project_top : bool
        Whether to project the top face of the mesh.
    tolerance_parallel : float
        The tolerance for parallelism.

    Returns
    -------
    list[:class:`compas.datastructures.Mesh`]
        A list of meshes.
    """

    # =============================================================================
    # Check if mesh has thickness values if not raise error
    # =============================================================================

    m_o = mesh.copy()
    if not m_o.vertices_attribute("thickness") or offset != 0:
        for v in m_o.vertices():
            m_o.vertex_attribute(v, "thickness", offset)

    # =============================================================================
    # Offset
    # =============================================================================

    for v in m_o.vertices():
        n: Vector = m_o.vertex_normal(v)
        t: float = m_o.vertex_attribute(v, "thickness")
        mesh.set_vertex_point(v, mesh.vertex_point(v) + n * t * thickness_scale_bottom)

    # =============================================================================
    # frames at m_o edges
    # normals are computed by an average of two face normals
    # frames are stored at each half edge and are flipped for the opposite half edge
    # =============================================================================

    e_frames: dict[tuple[int, int], Frame] = {}

    for e in m_o.edges():
        faces: tuple[int | None, int | None] = m_o.edge_faces(e)
        o: Point = (m_o.vertex_point(e[1]) + m_o.vertex_point(e[0])) / 2
        x0: Vector = m_o.face_normal(faces[0]) if faces[0] is not None else Vector(0, 0, 0)
        x1: Vector = m_o.face_normal(faces[1]) if faces[1] is not None else Vector(0, 0, 0)
        x: Vector = (x0 + x1) / 2
        y: Vector = m_o.edge_direction(e)
        e_frames[e] = Frame(o, x, y)
        e_frames[e[::-1]] = Frame(o, x, -y)

    # =============================================================================
    # frames at the corners of the block for chamfering
    # =============================================================================

    v_frames: dict[tuple[int, int], Frame] = {}
    parallel: dict[tuple[int, int], bool] = {}

    for f in m_o.faces():
        halfedges: list[tuple[int, int]] = m_o.face_halfedges(f)

        for i in range(len(halfedges)):
            # indexing
            id0: int = (i - 1) % len(halfedges)
            id1: int = i
            e0: tuple[int, int] = halfedges[id0]
            e1: tuple[int, int] = halfedges[id1]

            # orientation
            o: Point = m_o.vertex_point(e0[1])
            x0: Vector = e_frames[e0].zaxis
            x1: Vector = e_frames[e1].zaxis
            y0: Vector = e_frames[e0].xaxis
            y1: Vector = e_frames[e1].xaxis
            parallel[e1] = False

            # when frames are parallel: _ _ , we constuct 90 degrees rotated frame _|_
            if is_parallel_vector_vector(x0, x1, tol=tolerance_parallel):
                x: Vector = x0 + x1
                y: Vector = y0 + y1
                parallel[e1] = True
            # when frames are not parallel: _ / , we constuct frame from intersection of planes _\/
            else:
                r_pp: Optional[tuple[[float, float, float], [float, float, float]]] = intersection_plane_plane(Plane.from_frame(e_frames[e0]), Plane.from_frame(e_frames[e1]))
                if r_pp:
                    x: Vector = x1 - x0
                    y: Vector = Point(*r_pp[1]) - Point(*r_pp[0])
                else:
                    raise Exception("No Plane-Plane intersection in get_corner_frames method.")

            v_frames[e1] = Frame(o, x, y)

            # Calculate angle in radians from dot product of unit vectors
            # Map from dot product to chamfer factor:
            # - When dot = -1 (180°), factor = 0
            # - When dot approaches 1 (0°), factor approaches 1
            dot: float = x0.dot(x1)  # Range: [-1, 1]
            chamfer_factor: float = (1 - dot) / 2  # Range: [0, 1]

            if not m_o.is_vertex_on_boundary(e1[0]) and not is_parallel_vector_vector(x0, x1, tol=tolerance_parallel):
                v_frames[e1].translate(v_frames[e1].zaxis * chamfer * chamfer_factor)

    # =============================================================================
    # get vertex normals for each face
    # =============================================================================

    face_vertex_directions_0: dict[int, list[Line]] = {}
    face_vertex_directions_1: dict[int, list[Line]] = {}

    for f in m_o.faces():
        halfedges = m_o.face_halfedges(f)

        for i in range(len(halfedges)):
            # ._e0_.e1_.
            e0: tuple[int, int] = halfedges[(i - 1) % len(halfedges)]
            e1: tuple[int, int] = halfedges[i]

            # 1. we intersect vertex and edge frames _.\
            r_pp: tuple[[float, float, float], [float, float, float]] | None = intersection_plane_plane(Plane.from_frame(e_frames[e0]), Plane.from_frame(v_frames[e1]))

            if not r_pp:
                raise Exception("No Plane-Plane intersection.")

            # create line from intersection
            line = Line(r_pp[0], r_pp[1])

            # the intersection line is oriented in the same direction as the vertex normal
            p_o: Point = m_o.vertex_point(e1[0]) + m_o.vertex_normal(e1[0])
            if distance_point_point_sqrd(line[0] - line.vector, p_o) < distance_point_point_sqrd(line[1] + line.vector, p_o):
                line = Line(line[1], line[0])

            # We cut the line only for vizualization purposes to show the new face normals from approximate m_o vertex position
            pl = Plane(m_o.vertex_point(e1[0]), m_o.vertex_normal(e1[0]))
            r_lp: [float, float, float] | None = intersection_line_plane(line, pl)

            if not r_lp:
                raise Exception("No Line-Plane intersection.")

            face_vertex_directions_0[halfedges[i]] = Line(Point(*r_lp), Point(*r_lp) + line.vector)

            # 2. Second we intersect vertex and edge frames \./
            r_pp: tuple[[float, float, float], [float, float, float]] | None = intersection_plane_plane(Plane.from_frame(e_frames[e1]), Plane.from_frame(v_frames[e1]))

            if not r_pp:
                raise Exception("No Plane-Plane intersection.")

            line = Line(r_pp[0], r_pp[1])

            # orient line in the direction of the normal
            p_o = m_o.vertex_point(e1[0]) + m_o.vertex_normal(e1[0])
            if distance_point_point_sqrd(line[0] - line.vector, p_o) < distance_point_point_sqrd(line[1] + line.vector, p_o):
                line = Line(line[1], line[0])

            # We cut the line only for vizualization purposes to show the new face normals from approximate m_o vertex position
            pl = Plane(m_o.vertex_point(e1[0]), m_o.vertex_normal(e1[0]))
            r_lp: [float, float, float] | None = intersection_line_plane(line, pl)

            if not r_lp:
                raise Exception("No Line-Plane intersection.")

            face_vertex_directions_1[halfedges[i]] = Line(Point(*r_lp), Point(*r_lp) + line.vector)

    # =============================================================================
    # Get Blocks
    # =============================================================================

    blocks: list[Mesh] = []

    for face in m_o.faces():
        vertex_thickness: list[float] = m_o.vertices_attribute("thickness", keys=m_o.face_vertices(face))

        # intrados plane from m_o face centroind and its normal
        bottom_points: list[Point] = []
        o: Point = m_o.face_centroid(face)
        pl: Plane = Plane(o, m_o.face_normal(face))

        # We iterated over the face vertices and intersect the normal lines with the plane
        fv: list[int] = m_o.face_vertices(face)
        for idx, halfedge in enumerate(m_o.face_halfedges(face)):
            # If we want to keep have continouos m_o we construct planes at each vertex using their normals:
            if not project_bottom:
                pl = Plane(m_o.vertex_point(fv[idx]) + m_o.vertex_normal(fv[idx]) * vertex_thickness[idx] * 0, m_o.vertex_normal(fv[idx]))
                p0: Point = pl.projected_point(m_o.vertex_point(fv[(idx - 1) % len(fv)]))
                p1: Point = pl.projected_point(m_o.vertex_point(fv[idx]))
                p2: Point = pl.projected_point(m_o.vertex_point(fv[(idx + 1) % len(fv)]))
                v0: Vector = p1 - p0
                v1: Vector = p1 - p2
                v0.unitize()
                v1.unitize()

                if not is_parallel_vector_vector(v0, -v1, tol=tolerance_parallel):
                    p0: Point = m_o.vertex_point(fv[(idx - 1) % len(fv)])
                    p1: Point = m_o.vertex_point(fv[idx])
                    p2: Point = m_o.vertex_point(fv[(idx + 1) % len(fv)])
                    v0: Vector = p1 - p0
                    v1: Vector = p1 - p2
                    v0.unitize()
                    v1.unitize()
                    za: Vector = v1.cross(v0)
                    za.unitize()
                    pl: Plane = Plane(p0 + za * vertex_thickness[idx] * 0, za)

            line: Line = face_vertex_directions_0[halfedge]
            result_pl: Point = pl.intersection_with_line(line)
            bottom_points.append(result_pl)

            line = face_vertex_directions_1[halfedge]
            result_pl = pl.intersection_with_line(line)
            bottom_points.append(result_pl)

        # extrados plane from m_o face centroind and its normal
        top_points: list[Point] = []
        thickness_average: float = sum(vertex_thickness) / len(vertex_thickness) * thickness_scale_top
        o: Point = m_o.face_centroid(face)
        pl: Plane = Plane(o + m_o.face_normal(face) * thickness_average, m_o.face_normal(face))

        # We iterated over the face vertices and intersect the normal lines with the plane
        fv: list[int] = m_o.face_vertices(face)
        for idx, halfedge in enumerate(m_o.face_halfedges(face)):
            # If we want to keep have continouos m_o we construct planes at each vertex using their normals:
            if not project_top:
                pl: Plane = Plane(m_o.vertex_point(fv[idx]) + m_o.vertex_normal(fv[idx]) * vertex_thickness[idx] * thickness_scale_top, m_o.vertex_normal(fv[idx]))
                p0: Point = pl.projected_point(m_o.vertex_point(fv[(idx - 1) % len(fv)]))
                p1: Point = pl.projected_point(m_o.vertex_point(fv[idx]))
                p2: Point = pl.projected_point(m_o.vertex_point(fv[(idx + 1) % len(fv)]))
                v0: Vector = p1 - p0
                v1: Vector = p1 - p2
                v0.unitize()
                v1.unitize()

                if not is_parallel_vector_vector(v0, -v1, tol=tolerance_parallel):
                    p0: Point = m_o.vertex_point(fv[(idx - 1) % len(fv)])
                    p1: Point = m_o.vertex_point(fv[idx])
                    p2: Point = m_o.vertex_point(fv[(idx + 1) % len(fv)])
                    v0: Vector = p1 - p0
                    v1: Vector = p1 - p2
                    v0.unitize()
                    v1.unitize()
                    za: Vector = v1.cross(v0)
                    za.unitize()
                    pl: Plane = Plane(p0 + za * vertex_thickness[idx] * thickness_scale_top, za)

            line: Line = face_vertex_directions_0[halfedge]
            result_pl: Point = pl.intersection_with_line(line)
            top_points.append(result_pl)

            line: Line = face_vertex_directions_1[halfedge]
            result_pl: Point = pl.intersection_with_line(line)
            top_points.append(result_pl)

        sides: list[list[int]] = []
        for (a, b), (aa, bb) in zip(pairwise(bottom_points + bottom_points[:1]), pairwise(top_points + top_points[:1])):
            sides.append([a, b, bb, aa])

        polygons: list[list[int]] = [bottom_points[::-1], top_points] + sides

        block: Mesh = Mesh.from_polygons(polygons)
        blocks.append(block)

    return blocks
