#! python3
# venv: brg-csd
# r: compas_model

import pathlib

import compas
from compas.colors import Color
from compas.datastructures import Mesh
from compas.geometry import Frame
from compas.geometry import KDTree
from compas.geometry import Line
from compas.geometry import NurbsCurve
from compas.geometry import Plane
from compas.geometry import Transformation
from compas.geometry import Vector
from compas.geometry import bestfit_frame_numpy
from compas.geometry import centroid_points_weighted
from compas.geometry import offset_polygon
from compas.geometry import trimesh_remesh
from compas.itertools import pairwise
from compas.scene import Scene
from compas.tolerance import TOL
from compas_viewer import Viewer
from scipy.interpolate import griddata


def break_boundary(mesh: Mesh, breakpoints: list[int]) -> tuple[list[list[int]], list[int]]:
    boundary: list[int] = mesh.vertices_on_boundaries()[0]
    if boundary[0] == boundary[-1]:
        del boundary[-1]

    breakpoints = sorted(breakpoints, key=lambda s: boundary.index(s))

    start = boundary.index(breakpoints[0])
    boundary = boundary[start:] + boundary[:start]

    borders = []
    for a, b in pairwise(breakpoints):
        start = boundary.index(a)
        end = boundary.index(b)
        borders.append(boundary[start : end + 1])
    borders.append(boundary[end:] + boundary[:1])  # type: ignore

    return borders, breakpoints


def make_block(basemesh: Mesh, idos: Mesh, face: int) -> Mesh:
    vertices = basemesh.face_vertices(face)
    normals = [basemesh.vertex_normal(vertex) for vertex in vertices]
    thickness = basemesh.vertices_attribute("thickness", keys=vertices)

    bottom = idos.vertices_points(vertices)
    top = [point + vector * t for point, vector, t in zip(bottom, normals, thickness)]  # type: ignore

    frame = Frame(*bestfit_frame_numpy(top))
    plane = Plane.from_frame(frame)

    flattop = []
    for a, b in zip(bottom, top):
        b = plane.intersection_with_line(Line(a, b))
        flattop.append(b)

    sides = []
    for (a, b), (aa, bb) in zip(pairwise(bottom + bottom[:1]), pairwise(flattop + flattop[:1])):
        sides.append([a, b, bb, aa])

    polygons = [bottom[::-1], flattop] + sides

    block: Mesh = Mesh.from_polygons(polygons)
    block.update_default_face_attributes(is_support=False, is_interface=False)
    block.attributes["frame"] = frame
    block.attributes["is_support"] = False

    return block


def make_block_referenced(basemesh: Mesh, idos: Mesh, face: int) -> Mesh:
    N = basemesh._max_vertex + 1

    vertices = basemesh.face_vertices(face)
    normals = [basemesh.vertex_normal(vertex) for vertex in vertices]
    thickness = basemesh.vertices_attribute("thickness", keys=vertices)

    bottom = idos.vertices_points(vertices)
    top = [point + vector * t for point, vector, t in zip(bottom, normals, thickness)]  # type: ignore

    frame = Frame(*bestfit_frame_numpy(top))
    plane = Plane.from_frame(frame)

    flattop = []
    for a, b in zip(bottom, top):
        b = plane.intersection_with_line(Line(a, b))
        flattop.append(b)

    block: Mesh = Mesh()

    for vertex, point in zip(vertices, bottom):
        # use the same identifiers for the vertices of the bottom face
        key = vertex
        block.add_vertex(key=key, x=point[0], y=point[1], z=point[2])

    for vertex, point in zip(vertices, flattop):
        # offset the identifiers of the top face by "N"
        key = vertex + N
        block.add_vertex(key=key, x=point[0], y=point[1], z=point[2])

    block.add_face(vertices[::-1])
    block.add_face([vertex + N for vertex in vertices])

    for u, v in pairwise(vertices + vertices[:1]):
        block.add_face([u, v, v + N, u + N])

    block.update_default_face_attributes(is_support=False, is_interface=False)

    block.attributes["n"] = N
    block.attributes["frame"] = frame
    block.attributes["is_support"] = False

    return block


# =============================================================================
# Load data
# =============================================================================

IFILE = pathlib.Path(__file__).parent.parent / "data" / "shell_final.json"

rv_session = compas.json_load(IFILE)
rv_scene: Scene = rv_session["scene"]

thrustobject = rv_scene.find_by_name("ThrustDiagram")
thrustdiagram: Mesh = thrustobject.mesh  # type: ignore

# =============================================================================
# Global Parameters
# =============================================================================

THICKNESS_SUPPORTS1 = 30
THICKNESS_SUPPORTS2 = 20
THICKNESS_BORDER = 10
THICKNESS_TOP = 10

LENGTH_FACTOR = 0.9

MAX_CHAMFER_ANGLE = 145
CHAMFER_OFFSET = 2

SUPPORT_PADDING = 5
SUPPORT_DEPTH = 70

NOTCH_RADIUS = 2

# =============================================================================
# Mesh
#
# - make a copy of the thrustdiagram
# - remove the "TNA" faces cooresponding to boundary openings
# - compute the average edge length for remeshing
# =============================================================================

mesh: Mesh = thrustdiagram.copy(cls=Mesh)

for face in list(mesh.faces_where(_is_loaded=False)):
    mesh.delete_face(face)

average_length = sum(mesh.edge_length(edge) for edge in mesh.edges()) / mesh.number_of_edges()

# =============================================================================
# Mesh: Borders
# =============================================================================

supports = list(mesh.vertices_where(is_support=True))
borders, supports = break_boundary(mesh, supports)  # type: ignore

mesh.attributes["supports"] = supports
mesh.attributes["borders"] = borders

# =============================================================================
# Trimesh
#
# - convert a copy of the mesh to a trimesh using "quads to triangles"
# - note that this doesn't work for other patterns
# =============================================================================

trimesh: Mesh = mesh.copy()
trimesh.quads_to_triangles()

# =============================================================================
# Trimesh: Remeshing
#
# - remesh using CGAL
# - use a percentage of the average edge length of the original mesh as target length
# =============================================================================

target_edge_length = LENGTH_FACTOR * average_length

V, F = trimesh_remesh(
    trimesh.to_vertices_and_faces(),
    target_edge_length=target_edge_length,
    number_of_iterations=100,
)  # type: ignore

trimesh = Mesh.from_vertices_and_faces(V, F)

# =============================================================================
# Dual
#
# - construct a dual
# - update default attributes
# - flip the cycles because a dual has opposite cycles compared to the original
# =============================================================================

dual: Mesh = trimesh.dual(include_boundary=True)

dual.update_default_edge_attributes(is_support=False, is_interface=False)
dual.update_default_face_attributes(number=None, batch=None, block=None)
dual.update_default_vertex_attributes(thickness=0, is_corner=False, is_support=False)

dual.flip_cycles()

# =============================================================================
# Dual: Reconnect corners
#
# - construct a KD tree for nearest neighbour search
# - find the neares neighbours in the dual to the supports of the original
# - snap the dual vertices to the location of the supports
# - mark the corresponding vertices as "corners"
# =============================================================================

vertices = dual.vertices_attributes("xyz")
vertex_index = {vertex: index for index, vertex in enumerate(dual.vertices())}
index_vertex = {index: vertex for index, vertex in enumerate(dual.vertices())}
tree = KDTree(vertices)

for vertex in mesh.vertices_where(is_support=True):
    point = mesh.vertex_point(vertex)
    closest, nnbr, distance = tree.nearest_neighbor(point)
    dual_vertex = index_vertex[nnbr]
    if distance > 5:
        dual.vertex_attributes(dual_vertex, names="xyz", values=point)
    dual.vertex_attribute(dual_vertex, name="is_corner", value=True)

# =============================================================================
# Dual: Collapse 2-valent boundary edges
# =============================================================================

tofix = []

for vertex in dual.vertices_on_boundary():
    if dual.vertex_degree(vertex) > 2:
        continue
    tofix.append(vertex)

for vertex in tofix:
    nbrs = dual.vertex_neighbors(vertex)
    v0 = dual.edge_vector((vertex, nbrs[0]))
    v1 = dual.edge_vector((vertex, nbrs[1]))
    angle = v0.angle(v1, degrees=True)

    if abs(angle - 180) > 30:
        continue

    if dual.has_edge((vertex, nbrs[0])):
        is_corner = dual.vertex_attribute(nbrs[0], name="is_corner")
        dual.collapse_edge((vertex, nbrs[0]), t=1, allow_boundary=True)
    else:
        is_corner = dual.vertex_attribute(nbrs[1], name="is_corner")
        dual.collapse_edge((vertex, nbrs[1]), t=1, allow_boundary=True)

    if is_corner:
        dual.vertex_attribute(vertex, name="is_corner", value=True)

# =============================================================================
# Dual: Boundary smoothing
# =============================================================================

corners = list(dual.vertices_where(is_corner=True))
borders, corners = break_boundary(dual, corners)  # type: ignore

curves: list[NurbsCurve] = []
for border in borders:
    vertices = border[::2] if len(border) > 4 else border
    points = dual.vertices_points(vertices=vertices)
    curve: NurbsCurve = NurbsCurve.from_interpolation(points, precision=1)
    curves.append(curve)

for border, curve in zip(borders, curves):
    for vertex in border[1:-1]:
        nbrs = dual.vertex_neighbors(vertex)
        for nbr in nbrs:
            if nbr not in border:
                point = dual.vertex_point(nbr)
                closest = curve.closest_point(point)
                dual.vertex_attributes(vertex, "xyz", closest)
                break

# =============================================================================
# Dual: Edge collapse
# =============================================================================

tocollapse = []

for u, v in dual.edges_on_boundary():
    if dual.vertex_attribute(u, "is_corner") or dual.vertex_attribute(v, "is_corner"):
        continue
    face = dual.halfedge_face((v, u))
    vertices = dual.face_vertices(face)
    if len(vertices) == 4:
        vv = dual.face_vertex_ancestor(face, v)
        uu = dual.face_vertex_descendant(face, u)
        tocollapse.append((u, v))
        tocollapse.append((uu, vv))

for u, v in tocollapse:
    dual.collapse_edge((u, v), allow_boundary=True)

# =============================================================================
# Dual: Support edges
# =============================================================================

corners = list(dual.vertices_where(is_corner=True))
borders, corners = break_boundary(dual, corners)  # type: ignore
dual.attributes["borders"] = borders

for border in borders:
    if len(border) < 5:
        dual.vertices_attribute(name="is_support", value=True)
        for edge in pairwise(border):
            dual.edge_attribute(edge, name="is_support", value=True)

# =============================================================================
# Dual: Interface edges
# =============================================================================

for edge in dual.edges():
    if not dual.is_edge_on_boundary(edge):
        dual.edge_attribute(edge, name="is_interface", value=True)

# =============================================================================
# Blocks: Thickness interpolation griddata
# =============================================================================

points = []
values = []

supports_by_height = sorted(mesh.attributes["supports"], key=lambda v: mesh.vertex_attribute(v, "z"))  # type: ignore

for support in supports_by_height[:4]:
    points.append(mesh.vertex_attributes(support, "xy"))
    values.append(THICKNESS_SUPPORTS1)

for support in supports_by_height[4:]:
    points.append(mesh.vertex_attributes(support, "xy"))
    values.append(THICKNESS_SUPPORTS2)

for border in mesh.attributes["borders"]:
    if len(border) > 4:
        midspan = border[len(border) // 2]
        points.append(mesh.vertex_attributes(midspan, "xy"))
        values.append(THICKNESS_BORDER)

vertices_by_height = sorted(mesh.vertices(), key=lambda v: mesh.vertex_attribute(v, "z"))  # type: ignore

for vertex in vertices_by_height[-5:]:
    points.append(mesh.vertex_attributes(vertex, "xy"))
    values.append(THICKNESS_TOP)

# =============================================================================
# Blocks: Thickness interpolation sampling
# =============================================================================

samples = dual.vertices_attributes("xy")
thickness = griddata(points, values, samples)

for vertex, t in zip(dual.vertices(), thickness):
    dual.vertex_attribute(vertex, "thickness", t)

# =============================================================================
# Blocks: Idos
# =============================================================================

idos: Mesh = dual.copy()
for vertex in idos.vertices():
    point = dual.vertex_point(vertex)
    normal = dual.vertex_normal(vertex)
    thickness = dual.vertex_attribute(vertex, name="thickness")
    idos.vertex_attributes(vertex, names="xyz", values=point - normal * (0.5 * thickness))  # type: ignore

# =============================================================================
# Blocks
# =============================================================================

blocks: list[Mesh] = []

for face in dual.faces():
    block = make_block(dual, idos, face)  # type: ignore
    dual.face_attribute(face, name="block", value=block)

    # identify support faces and interfaces
    vertices = dual.face_vertices(face)
    for index, (u, v) in enumerate(pairwise(vertices + vertices[:1])):
        # the first two faces are bottom and top
        # then come the side faces in same order as the cycle of pairwise vertices
        # => face = index + 2
        face = index + 2

        is_support = dual.edge_attribute((u, v), name="is_support")
        is_interface = dual.edge_attribute((u, v), name="is_interface")

        block.face_attribute(face, name="is_support", value=is_support)
        block.face_attribute(face, name="is_interface", value=is_interface)

        block.attributes["is_support"] = True

    blocks.append(block)

# =============================================================================
# Block: Chamfering
# =============================================================================

face_block = {face: dual.face_attribute(face, "block").copy() for face in dual.faces()}  # type: ignore

for vertex in dual.vertices():
    if dual.is_vertex_on_boundary(vertex):
        continue

    point = dual.vertex_point(vertex)
    normal = dual.vertex_normal(vertex)
    plane = Plane(point, normal)

    nbrs = dual.vertex_neighbors(vertex, ordered=True)

    for index, nbr in enumerate(nbrs):
        ancestor = nbrs[index - 1]

        left = plane.projected_point(dual.vertex_point(ancestor))
        right = plane.projected_point(dual.vertex_point(nbr))

        v1 = (left - plane.point).unitized()  # type: ignore
        v2 = (right - plane.point).unitized()  # type: ignore

        if v1.angle(v2, degrees=True) > MAX_CHAMFER_ANGLE:
            continue

        direction = (v1 + v2).unitized()
        cutter = Plane(plane.point, direction).offset(CHAMFER_OFFSET)

        face = dual.halfedge_face((vertex, nbr))
        temp: Mesh = face_block[face]
        a, b = temp.slice(cutter)  # type: ignore
        face_block[face] = a

# =============================================================================
# Blocks: Fabrication data
# =============================================================================

# printblocks: list[Mesh] = []

# for block in blocks:
#     frame: Frame = block.attributes["frame"]
#     transformation = Transformation.from_frame_to_frame(frame.flipped(), Frame.worldXY())
#     printblocks.append(block.transformed(transformation))

# =============================================================================
# Supports (this is independent from the blocks)
# =============================================================================

gkey_reaction: dict[str, Vector] = {}
for vertex in mesh.vertices_where(is_support=True):
    gkey = TOL.geometric_key(mesh.vertex_point(vertex), 1)
    rx, ry, rz = mesh.vertex_attributes(vertex, names=["_rx", "_ry", "_rz"])  # type: ignore
    gkey_reaction[gkey] = Vector(rx, ry, rz)

supports = []

for border in dual.attributes["borders"]:
    if len(border) < 5:
        P0 = dual.vertex_point(border[0])
        P1 = dual.vertex_point(border[-1])

        R0 = gkey_reaction[TOL.geometric_key(P0, 1)]
        R1 = gkey_reaction[TOL.geometric_key(P1, 1)]

        point = centroid_points_weighted([P0, P1], [R0.length, R1.length])
        xaxis = P0 - P1
        zaxis = R0 + R1
        yaxis = zaxis.cross(xaxis)
        frame = Frame(point, xaxis, yaxis)
        plane = Plane.from_frame(frame)
        offset = plane.offset(SUPPORT_DEPTH)

        t0 = dual.vertex_attribute(border[0], name="thickness")
        t1 = dual.vertex_attribute(border[-1], name="thickness")

        v0 = dual.vertex_normal(border[0]) * 0.5 * t0
        v1 = dual.vertex_normal(border[-1]) * 0.5 * t1

        bottom = [P0 + v0, P1 + v1, P1 - v1, P0 - v0]
        bottom = offset_polygon(bottom, -SUPPORT_PADDING)

        top = [
            offset.intersection_with_line(Line.from_point_and_vector(bottom[0], R0)),
            offset.intersection_with_line(Line.from_point_and_vector(bottom[1], R1)),
            offset.intersection_with_line(Line.from_point_and_vector(bottom[2], R1)),
            offset.intersection_with_line(Line.from_point_and_vector(bottom[3], R0)),
        ]

        sides = []
        for (a, b), (aa, bb) in zip(pairwise(bottom + bottom[:1]), pairwise(top + top[:1])):
            sides.append([a, b, bb, aa])

        polygons = [bottom[::-1]] + [top] + sides
        support = Mesh.from_polygons(polygons)
        supports.append(support)

# =============================================================================
# Visualisation
# =============================================================================

TOL.lineardeflection = 1
TOL.angulardeflection = 0.5

viewer = Viewer()
viewer.unit = "cm"

# =============================================================================
# Viz: Reactions
# =============================================================================

reactions = []
for vertex in mesh.vertices_where(is_support=True):
    point = mesh.vertex_point(vertex)
    residual = Vector(*mesh.vertex_attributes(vertex, names=["_rx", "_ry", "_rz"]))  # type: ignore
    reaction = Line.from_point_and_vector(point, residual * 0.001)
    reactions.append(reaction)

group = viewer.scene.add_group(name="Reactions")
group.add_from_list(reactions, linewidth=5, linecolor=Color.green())  # type: ignore

# =============================================================================
# Viz: Supports
# =============================================================================

group = viewer.scene.add_group(name="Supports")
group.add_from_list(supports, facecolor=Color.blue())  # type: ignore

# =============================================================================
# Viz: Cut blocks
# =============================================================================

group = viewer.scene.add_group(name="Chamfered Blocks")
group.add_from_list(list(face_block.values()), show_faces=True, show_lines=True)  # type: ignore

# =============================================================================
# Viz: Show
# =============================================================================

viewer.show()
