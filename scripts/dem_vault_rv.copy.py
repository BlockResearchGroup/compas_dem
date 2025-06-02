#! python3
# venv: brg-csd
# r: compas_model

import pathlib

import compas
from compas.colors import Color
from compas.datastructures import Mesh
from compas.geometry import KDTree
from compas.geometry import Line
from compas.geometry import NurbsCurve
from compas.geometry import Plane
from compas.geometry import bestfit_plane_numpy
from compas.geometry import trimesh_remesh
from compas.itertools import pairwise
from compas.scene import Scene
from compas.tolerance import TOL
from compas_tna.diagrams import FormDiagram
from compas_viewer import Viewer
from compas_viewer.config import Config
from scipy.interpolate import griddata

# from compas.datastructures.mesh.remesh import trimesh_remesh
# from compas.geometry import Line
# from compas.geometry import normal_triangle
# from compas.itertools import remap_values
# from compas_model.geometry import intersection_ray_triangle

IFILE = pathlib.Path(__file__).parent.parent / "data" / "shell_final.json"

rv_session = compas.json_load(IFILE)
rv_scene: Scene = rv_session["scene"]

thrustobject = rv_scene.find_by_name("ThrustDiagram")
thrustdiagram: FormDiagram = thrustobject.mesh

# =============================================================================
# Mesh
# =============================================================================

mesh: Mesh = thrustdiagram.copy(cls=Mesh)

for face in list(mesh.faces_where(_is_loaded=False)):
    mesh.delete_face(face)

length = sum(mesh.edge_length(edge) for edge in mesh.edges()) / mesh.number_of_edges()

# =============================================================================
# Trimesh
# =============================================================================

trimesh: Mesh = mesh.copy()
trimesh.quads_to_triangles()

# =============================================================================
# Trimesh: Remeshing
# =============================================================================

M = trimesh.to_vertices_and_faces()
V, F = trimesh_remesh(M, target_edge_length=0.9 * length, number_of_iterations=100)

trimesh = Mesh.from_vertices_and_faces(V, F)

# vertex_index = {vertex: index for index, vertex in enumerate(trimesh.vertices())}
# vertex_triangles = {vertex_index[vertex]: [trimesh.face_points(face) for face in trimesh.vertex_faces(vertex)] for vertex in trimesh.vertices()}
# vertices = trimesh.vertices_attributes("xyz")
# tree = KDTree(vertices)

# fixed = list(trimesh.vertices_on_boundary())
# free = set(list(trimesh.vertices())) - set(fixed)

# def project(mesh: Mesh, k, args):
#     for vertex in mesh.vertices():
#         if mesh.is_vertex_on_boundary(vertex):
#             continue
#         point = mesh.vertex_point(vertex)
#         _, nbr, _ = tree.nearest_neighbor(point)
#         triangles = vertex_triangles[nbr]
#         for triangle in triangles:
#             normal = normal_triangle(triangle)
#             ray = Line.from_point_direction_length(point, normal, 10)
#             result = intersection_ray_triangle(ray, triangle)
#             if result:
#                 mesh.vertex_attributes(vertex, "xyz", result)
#                 break

# trimesh_remesh(trimesh, length, kmax=300, tol=0.1, allow_boundary_split=False, callback=project)

# =============================================================================
# Dual
# =============================================================================

dual: Mesh = trimesh.dual(include_boundary=True)

dual.update_default_edge_attributes(is_support=False)
dual.update_default_face_attributes(number=None, batch=None)
dual.update_default_vertex_attributes(thickness=0, is_corner=False, is_support=False)

dual.flip_cycles()

# =============================================================================
# Dual: Reconnect corners
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

boundary = dual.vertices_on_boundaries()[0]
if boundary[0] == boundary[-1]:
    del boundary[-1]

corners = list(dual.vertices_where(is_corner=True))
corners = sorted(corners, key=lambda s: boundary.index(s))

borders = []
start = boundary.index(corners[0])
boundary = boundary[start:] + boundary[:start]
for a, b in pairwise(corners):
    start = boundary.index(a)
    end = boundary.index(b)
    borders.append(boundary[start : end + 1])
borders.append(boundary[end:] + boundary[:1])

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
# Thickness: Identify interpolation points
# =============================================================================

supports = list(mesh.vertices_where(is_support=True))
boundary = mesh.vertices_on_boundaries()[0]
supports = sorted(supports, key=lambda s: boundary.index(s))

borders = []
start = boundary.index(supports[0])
boundary = boundary[start:] + boundary[:start]
for a, b in pairwise(supports):
    start = boundary.index(a)
    end = boundary.index(b)
    borders.append(boundary[start : end + 1])
borders.append(boundary[end:])

# =============================================================================
# Thickness: Interpolate
# =============================================================================

points = []
values = []

for support in sorted(supports, key=lambda v: mesh.vertex_attribute(v, "z"))[:4]:
    points.append(mesh.vertex_attributes(support, "xy"))
    values.append(50)

for support in sorted(supports, key=lambda v: mesh.vertex_attribute(v, "z"))[4:]:
    points.append(mesh.vertex_attributes(support, "xy"))
    values.append(30)

for border in borders:
    if len(border) < 4:
        continue
    midspan = border[len(border) // 2]
    points.append(mesh.vertex_attributes(midspan, "xy"))
    values.append(15)

for vertex in sorted(mesh.vertices(), key=lambda v: mesh.vertex_attribute(v, "z"))[-5:]:
    points.append(mesh.vertex_attributes(vertex, "xy"))
    values.append(10)

samples = dual.vertices_attributes("xy")
thickness = griddata(points, values, samples)

for vertex, t in zip(dual.vertices(), thickness):
    dual.vertex_attribute(vertex, "thickness", t)

# =============================================================================
# Supports
# =============================================================================


# =============================================================================
# Blocks
# =============================================================================

blocks = []
for face in dual.faces():
    vertices = dual.face_vertices(face)
    normals = [dual.vertex_normal(vertex) for vertex in vertices]
    thickness = dual.vertices_attribute("thickness", keys=vertices)
    bottom = dual.face_polygon(face)
    top = [point + vector * (0.5 * t) for point, vector, t in zip(bottom, normals, thickness)]
    bottom = [point - vector * (0.5 * t) for point, vector, t in zip(bottom, normals, thickness)]
    plane = Plane(*bestfit_plane_numpy(top))
    flattop = []
    for a, b in zip(bottom, top):
        b = plane.intersection_with_line(Line(a, b))
        flattop.append(b)
    sides = []
    for (a, b), (aa, bb) in zip(pairwise(bottom + bottom[:1]), pairwise(flattop + flattop[:1])):
        sides.append([a, b, bb, aa])
    polygons = [bottom[::-1]] + [flattop] + sides
    blocks.append(Mesh.from_polygons(polygons))

# =============================================================================
# Visualisation
# =============================================================================

config = Config()
config.camera.target = [500, 500, 50]
config.camera.position = [500, -500, 100]
config.camera.near = 1
config.camera.far = 10000
config.renderer.gridsize = (1000, 10, 1000, 10)

viewer = Viewer(config=config)
# viewer.scene.add(mesh, show_faces=False, show_edges=True)
# viewer.scene.add(dual, facecolor={face: Color.red() for face in tocollapse})
viewer.scene.add(blocks)
# viewer.scene.add(curves, linewidth=3)
viewer.show()
