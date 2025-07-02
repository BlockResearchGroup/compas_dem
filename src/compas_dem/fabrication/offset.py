from compas.datastructures import Mesh
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Vector
from compas.geometry import distance_point_point
from compas.geometry import distance_point_point_sqrd
from compas.geometry import intersection_line_plane
from compas.geometry import intersection_plane_plane
from compas.geometry import is_parallel_vector_vector
from compas.itertools import pairwise


class OffsetPlanarBlocks(object):
    """
    Offset a mesh to create blocks with planar sides and chamfered corners.

    Attributes
    ----------
    original_mesh : :class:`compas.datastructures.Mesh`
        The original input mesh before any operations.
    mesh : :class:`compas.datastructures.Mesh`
        A working copy of the mesh with offsets applied.
    offset : float
        The offset distance.
    chamfer : float
        The chamfer distance.
    thickness_scale_bottom : float
        The thickness scale for the bottom.
    thickness_scale_top : float
        The thickness scale for the top.
    project_bottom : bool
        True if bottom face should be projected, False otherwise.
    project_top : bool
        True if top face should be projected, False otherwise.
    tolerance_parallel : float
        The tolerance for parallelism.
    vertex_normals : list[:class:`compas.geometry.Vector`]
        The vertex normals of the mesh.
    edge_frames : dict[tuple[int, int], :class:`compas.geometry.Frame`]
        Frames at each edge of the mesh.
    vertex_frames : dict[tuple[int, int], :class:`compas.geometry.Frame`]
        Frames at each vertex of the mesh.
    parallel_edges : dict[tuple[int, int], bool]
        Dictionary mapping edges to boolean indicating if they are parallel.
    face_vertex_directions_0 : dict[tuple[int, int], :class:`compas.geometry.Line`]
        First vertex direction lines for each face.
    face_vertex_directions_1 : dict[tuple[int, int], :class:`compas.geometry.Line`]
        Second vertex direction lines for each face.
    blocks : list[:class:`compas.datastructures.Mesh`]
        The generated block meshes.
    block_frames : list[:class:`compas.geometry.Frame`]
        The frames of the generated blocks.
    """

    def __init__(
        self,
        mesh,
        offset=0.0,
        chamfer=0.05,
        thickness_scale_bottom=0.0,
        thickness_scale_top=1.0,
        project_bottom=True,
        project_top=False,
        tolerance_parallel=0.5,
        vertex_normals=None,
    ):
        self.original_mesh = mesh
        self.mesh = mesh.copy()
        self.offset = offset
        self.chamfer = chamfer
        self.thickness_scale_bottom = thickness_scale_bottom
        self.thickness_scale_top = thickness_scale_top
        self.project_bottom = project_bottom
        self.project_top = project_top
        self.tolerance_parallel = tolerance_parallel
        self.vertex_normals = vertex_normals

        # Results
        self.edge_frames = {}
        self.vertex_frames = {}
        self.parallel_edges = {}
        self.face_vertex_directions_0 = {}
        self.face_vertex_directions_1 = {}
        self.blocks = []
        self.block_frames = []

        self._check_mesh_thickness()
        self._offset_mesh()
        self._compute_edge_frames()
        self._compute_vertex_frames()
        self._get_vertex_lines()
        self._get_blocks()

    def _check_mesh_thickness(self):
        """Check if mesh has thickness values, set them if needed or raise an error.

        If offset is not zero, assigns that value as thickness to all vertices.
        Otherwise, verifies that thickness attributes are present on all vertices.

        Returns
        -------
        bool
            True if thickness values were set or already existed, False otherwise.

        Raises
        ------
        ValueError
            If mesh has no thickness values and offset is zero.
        """
        if self.offset != 0:
            for vertex in self.mesh.vertices():
                self.mesh.vertex_attribute(vertex, "thickness", self.offset)
        elif not self.mesh.vertices_attribute("thickness"):
            raise ValueError("Mesh must have thickness values.")

    def _offset_mesh(self):
        """Apply offset to mesh vertices based on thickness and scale.

        Displaces each vertex along its normal by its thickness value
        multiplied by the thickness_scale_bottom factor.

        Returns
        -------
        :class:`compas.datastructures.Mesh`
            The mesh with offset applied.
        """
        for vertex in self.mesh.vertices():
            normal = self.vertex_normals[vertex]  # self.mesh.vertex_normal(vertex)
            thickness = self.mesh.vertex_attribute(vertex, "thickness")
            self.mesh.set_vertex_point(vertex, self.mesh.vertex_point(vertex) + normal * thickness * self.thickness_scale_bottom)

    def _compute_edge_frames(self):
        """Compute frames at mesh edges."""
        for edge in self.mesh.edges():
            faces = self.mesh.edge_faces(edge)
            origin = (self.mesh.vertex_point(edge[1]) + self.mesh.vertex_point(edge[0])) / 2
            normal0 = self.mesh.face_normal(faces[0]) if faces[0] is not None else Vector(0, 0, 0)
            normal1 = self.mesh.face_normal(faces[1]) if faces[1] is not None else Vector(0, 0, 0)
            normal = (normal0 + normal1) / 2
            direction = self.mesh.edge_direction(edge)
            self.edge_frames[edge] = Frame(origin, normal, direction)
            self.edge_frames[edge[::-1]] = Frame(origin, normal, -direction)

    def _compute_vertex_frames(self):
        """Compute frames at the corners of the block for chamfering."""
        for face in self.mesh.faces():
            halfedges = self.mesh.face_halfedges(face)

            for i in range(len(halfedges)):
                # indexing
                prev_idx = (i - 1) % len(halfedges)
                curr_idx = i
                prev_edge = halfedges[prev_idx]
                curr_edge = halfedges[curr_idx]

                # orientation
                origin = self.mesh.vertex_point(prev_edge[1])
                zaxis_prev = self.edge_frames[prev_edge].zaxis
                zaxis_curr = self.edge_frames[curr_edge].zaxis
                xaxis_prev = self.edge_frames[prev_edge].xaxis
                xaxis_curr = self.edge_frames[curr_edge].xaxis
                self.parallel_edges[curr_edge] = False

                # when frames are parallel: _ _ , construct 90 degrees rotated frame _|_
                if is_parallel_vector_vector(zaxis_prev, zaxis_curr, tol=self.tolerance_parallel):
                    x_vector = zaxis_prev + zaxis_curr
                    y_vector = xaxis_prev + xaxis_curr
                    self.parallel_edges[curr_edge] = True
                # when frames are not parallel: _ / , construct frame from intersection of planes _\/
                else:
                    plane_intersection = intersection_plane_plane(Plane.from_frame(self.edge_frames[prev_edge]), Plane.from_frame(self.edge_frames[curr_edge]))
                    if plane_intersection:
                        x_vector = zaxis_curr - zaxis_prev
                        y_vector = Point(*plane_intersection[1]) - Point(*plane_intersection[0])
                    else:
                        raise Exception("No Plane-Plane intersection in get_corner_frames method.")

                self.vertex_frames[curr_edge] = Frame(origin, x_vector, y_vector)

                # Calculate angle in radians from dot product of unit vectors
                # Map from dot product to chamfer factor:
                # - When dot = -1 (180°), factor = 0
                # - When dot approaches 1 (0°), factor approaches 1
                dot_product = zaxis_prev.dot(zaxis_curr)  # Range: [-1, 1]
                chamfer_factor = (1 - dot_product) / 2  # Range: [0, 1]

                if not self.mesh.is_vertex_on_boundary(curr_edge[0]) and not is_parallel_vector_vector(zaxis_prev, zaxis_curr, tol=self.tolerance_parallel):
                    self.vertex_frames[curr_edge].translate(self.vertex_frames[curr_edge].zaxis * self.chamfer * chamfer_factor)

    def _get_vertex_lines(self):
        """Calculate vertex normal lines for each face.

        Raises
        ------
        Exception
            If plane-plane or line-plane intersections cannot be computed.
        """
        for face in self.mesh.faces():
            halfedges = self.mesh.face_halfedges(face)

            for i in range(len(halfedges)):
                # ._e0_.e1_.
                prev_edge = halfedges[(i - 1) % len(halfedges)]
                curr_edge = halfedges[i]

                # 1. we intersect vertex and edge frames _.\
                plane_intersection = intersection_plane_plane(Plane.from_frame(self.edge_frames[prev_edge]), Plane.from_frame(self.vertex_frames[curr_edge]))

                if not plane_intersection:
                    raise Exception("No Plane-Plane intersection.")

                # create line from intersection
                line = Line(plane_intersection[0], plane_intersection[1])

                # the intersection line is oriented in the same direction as the vertex normal
                p_o = self.mesh.vertex_point(curr_edge[0]) + self.mesh.vertex_normal(curr_edge[0])
                if distance_point_point_sqrd(line[0] - line.vector, p_o) < distance_point_point_sqrd(line[1] + line.vector, p_o):
                    line = Line(line[1], line[0])

                # We cut the line only for vizualization purposes to show the new face normals from approximate vertex position
                pl = Plane(self.mesh.vertex_point(curr_edge[0]), self.mesh.vertex_normal(curr_edge[0]))
                line_plane_intersection = intersection_line_plane(line, pl)

                if not line_plane_intersection:
                    raise Exception("No Line-Plane intersection.")

                self.face_vertex_directions_0[halfedges[i]] = Line(Point(*line_plane_intersection), Point(*line_plane_intersection) + line.vector)

                # 2. Second we intersect vertex and edge frames \./
                plane_intersection = intersection_plane_plane(Plane.from_frame(self.edge_frames[curr_edge]), Plane.from_frame(self.vertex_frames[curr_edge]))

                if not plane_intersection:
                    raise Exception("No Plane-Plane intersection.")

                line = Line(plane_intersection[0], plane_intersection[1])

                # orient line in the direction of the normal
                p_o = self.mesh.vertex_point(curr_edge[0]) + self.mesh.vertex_normal(curr_edge[0])
                if distance_point_point_sqrd(line[0] - line.vector, p_o) < distance_point_point_sqrd(line[1] + line.vector, p_o):
                    line = Line(line[1], line[0])

                # We cut the line only for vizualization purposes to show the new face normals from approximate vertex position
                pl = Plane(self.mesh.vertex_point(curr_edge[0]), self.mesh.vertex_normal(curr_edge[0]))
                line_plane_intersection = intersection_line_plane(line, pl)

                if not line_plane_intersection:
                    raise Exception("No Line-Plane intersection.")

                self.face_vertex_directions_1[halfedges[i]] = Line(Point(*line_plane_intersection), Point(*line_plane_intersection) + line.vector)

    def _get_blocks(self):
        """Generate blocks with planar sides and chamfered corners."""

        for face in self.mesh.faces():
            vertex_thickness = self.mesh.vertices_attribute("thickness", keys=self.mesh.face_vertices(face))

            # intrados plane from mesh face centroid and its normal
            bottom_points = []
            origin = self.mesh.face_centroid(face)
            plane = Plane(origin, self.mesh.face_normal(face))
            face_vertices = self.mesh.face_vertices(face)

            p0 = plane.projected_point(self.mesh.vertex_point(face_vertices[0]))
            p1 = plane.projected_point(self.mesh.vertex_point(face_vertices[1]))
            x = p1 - p0
            y = x.cross(-plane.normal)
            orientation_frame = Frame(origin, x, y)

            # We iterate over the face vertices and intersect the normal lines with the plane
            face_vertices = self.mesh.face_vertices(face)
            for idx, halfedge in enumerate(self.mesh.face_halfedges(face)):
                # If we want to keep a continuous mesh, construct planes at each vertex using their normals
                if not self.project_bottom:
                    plane = Plane(
                        self.mesh.vertex_point(face_vertices[idx]) + self.mesh.vertex_normal(face_vertices[idx]) * vertex_thickness[idx] * 0,
                        self.mesh.vertex_normal(face_vertices[idx]),
                    )
                    p0 = plane.projected_point(self.mesh.vertex_point(face_vertices[(idx - 1) % len(face_vertices)]))
                    p1 = plane.projected_point(self.mesh.vertex_point(face_vertices[idx]))
                    p2 = plane.projected_point(self.mesh.vertex_point(face_vertices[(idx + 1) % len(face_vertices)]))
                    v0 = p1 - p0
                    v1 = p1 - p2
                    v0.unitize()
                    v1.unitize()

                    if not is_parallel_vector_vector(v0, -v1, tol=self.tolerance_parallel):
                        p0 = self.mesh.vertex_point(face_vertices[(idx - 1) % len(face_vertices)])
                        p1 = self.mesh.vertex_point(face_vertices[idx])
                        p2 = self.mesh.vertex_point(face_vertices[(idx + 1) % len(face_vertices)])
                        v0 = p1 - p0
                        v1 = p1 - p2
                        v0.unitize()
                        v1.unitize()
                        za = v1.cross(v0)
                        za.unitize()
                        plane = Plane(p0 + za * vertex_thickness[idx] * 0, za)

                line = self.face_vertex_directions_0[halfedge]
                result_pt = plane.intersection_with_line(line)
                bottom_points.append(result_pt)

                line = self.face_vertex_directions_1[halfedge]
                result_pt = plane.intersection_with_line(line)
                bottom_points.append(result_pt)

            # extrados plane from mesh face centroid and its normal
            top_points = []
            thickness_average = sum(vertex_thickness) / len(vertex_thickness) * self.thickness_scale_top
            origin = self.mesh.face_centroid(face)
            plane = Plane(origin + self.mesh.face_normal(face) * thickness_average, self.mesh.face_normal(face))

            if self.project_top:
                orientation_frame.translate(orientation_frame.zaxis * thickness_average)
                orientation_frame.flip()

            # We iterate over the face vertices and intersect the normal lines with the plane
            face_vertices = self.mesh.face_vertices(face)
            for idx, halfedge in enumerate(self.mesh.face_halfedges(face)):
                # If we want to keep a continuous mesh, construct planes at each vertex using their normals
                if not self.project_top:
                    plane = Plane(
                        self.mesh.vertex_point(face_vertices[idx]) + self.mesh.vertex_normal(face_vertices[idx]) * vertex_thickness[idx] * self.thickness_scale_top,
                        self.mesh.vertex_normal(face_vertices[idx]),
                    )
                    p0 = plane.projected_point(self.mesh.vertex_point(face_vertices[(idx - 1) % len(face_vertices)]))
                    p1 = plane.projected_point(self.mesh.vertex_point(face_vertices[idx]))
                    p2 = plane.projected_point(self.mesh.vertex_point(face_vertices[(idx + 1) % len(face_vertices)]))
                    v0 = p1 - p0
                    v1 = p1 - p2
                    v0.unitize()
                    v1.unitize()

                    if not is_parallel_vector_vector(v0, -v1, tol=self.tolerance_parallel):
                        p0 = self.mesh.vertex_point(face_vertices[(idx - 1) % len(face_vertices)])
                        p1 = self.mesh.vertex_point(face_vertices[idx])
                        p2 = self.mesh.vertex_point(face_vertices[(idx + 1) % len(face_vertices)])
                        v0 = p1 - p0
                        v1 = p1 - p2
                        v0.unitize()
                        v1.unitize()
                        za = v1.cross(v0)
                        za.unitize()
                        plane = Plane(p0 + za * vertex_thickness[idx] * self.thickness_scale_top, za)

                line = self.face_vertex_directions_0[halfedge]
                result_pt = plane.intersection_with_line(line)
                top_points.append(result_pt)

                line = self.face_vertex_directions_1[halfedge]
                result_pt = plane.intersection_with_line(line)
                top_points.append(result_pt)

            sides = []
            for (a, b), (aa, bb) in zip(pairwise(bottom_points + bottom_points[:1]), pairwise(top_points + top_points[:1])):
                sides.append([a, b, bb, aa])

            polygons = [bottom_points[::-1], top_points] + sides

            polygons_no_duplicates = []

            # remove duplicates
            for points in polygons:
                new_points = [points[0]]
                for i in range(1, len(points)):
                    if distance_point_point(points[i], new_points[-1]) > 1e-3:
                        new_points.append(points[i])
                polygons_no_duplicates.append(new_points)

            block = Mesh.from_polygons(polygons_no_duplicates)
            self.blocks.append(block)
            self.block_frames.append(orientation_frame)
