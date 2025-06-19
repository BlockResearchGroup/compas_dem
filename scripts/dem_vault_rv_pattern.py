#! python3
# venv: brg-csd
# r: compas_model, Tessagon

import pathlib

import compas
from compas.colors import Color
from compas.datastructures import Mesh
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import bestfit_frame_numpy
from compas.itertools import pairwise
from compas.scene import MeshObject
from compas.scene import Scene
from compas_libigl.mapping import map_mesh
from compas_cgal.meshing import mesh_remesh
from compas_viewer import Viewer

# =============================================================================
# Session data
# =============================================================================

HERE = pathlib.Path(__file__).parent.parent
DATA = HERE / "data"
SESSION = DATA / "rv_pattern.json"
session = compas.json_load(SESSION)

# =============================================================================
# User Defined Pattern
# =============================================================================

SESSION = DATA / "user_2d_patterns.json"
user_2d_patterns = compas.json_load(SESSION)
user_2d_pattern = user_2d_patterns[3]

# =============================================================================
# RV mesh
# =============================================================================

scene: Scene = session["scene"]
sceneobj: MeshObject = scene.find_by_name("ThrustDiagram")  # type: ignore
mesh: Mesh = sceneobj.mesh

for face in list(mesh.faces_where(_is_loaded=False)):
    mesh.delete_face(face)

# =============================================================================
# Remeshed triangle mesh
# =============================================================================

trimesh: Mesh = mesh.copy()
trimesh.quads_to_triangles()

average_length = sum(mesh.edge_length(edge) for edge in mesh.edges()) / mesh.number_of_edges()
target_edge_length = 1 * average_length

V, F = mesh_remesh(trimesh.to_vertices_and_faces(), target_edge_length, 1000)
trimesh = Mesh.from_vertices_and_faces(V, F)

# ==============================================================================
# Get Lowest and Highest points
# ==============================================================================

aabb = mesh.aabb()
fixed_vertices = []


for vertex in mesh.vertices():
    x, y, z = mesh.vertex_attributes(vertex, "xyz")  # type: ignore
    if abs(z-aabb.zmin) < 1e-3:
        fixed_vertices.append(vertex)

# =============================================================================
# Select a pattern
# =============================================================================

pattern = Mesh.from_polygons(user_2d_pattern)

mv, mf, mn, mb, mg = map_mesh(trimesh.to_vertices_and_faces(), pattern.to_vertices_and_faces(), clip_boundaries=True, fixed_vertices=fixed_vertices, tolerance=1e-3)
pattern = Mesh.from_vertices_and_faces(mv, mf)

# =============================================================================
# Thickness
# =============================================================================

pattern.update_default_vertex_attributes(thickness=0)

zvalues: list[float] = pattern.vertices_attribute(name="z")  # type: ignore
zmin = min(zvalues)
zmax = max(zvalues)

tmin = 0.3
tmax = 0.4

for vertex in pattern.vertices():
    point = Point(*mv[vertex])
    normal = mn[vertex]
    z = (point.z - zmin) / (zmax - zmin)
    thickness = (1 - z) * (tmax - tmin) + tmin
    pattern.vertex_attribute(vertex, name="thickness", value=thickness)

# =============================================================================
# Intrados
# =============================================================================

idos: Mesh = pattern.copy()

for vertex in idos.vertices():
    point = Point(*mv[vertex])
    normal = mn[vertex]
    thickness = pattern.vertex_attribute(vertex, name="thickness")
    idos.vertex_attributes(vertex, names="xyz", values=point - normal * (0.5 * thickness))  # type: ignore

# =============================================================================
# blocks
# =============================================================================

blocks: list[Mesh] = []

for face in pattern.faces():
    vertices = pattern.face_vertices(face)
    normals = [mn[vertex] for vertex in vertices]
    thickness = pattern.vertices_attribute("thickness", keys=vertices)

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
    blocks.append(block)

# =============================================================================
# Viz
# =============================================================================

viewer = Viewer()
scene = viewer.scene

for polygons in user_2d_patterns:
    group = scene.add_group(name="Pattern")
    for polygon in polygons:
        group.add(polygon, name="Pattern", facecolor=Color.red(), opacity=0.5)

# scene.add(trimesh, name="TriMesh")
scene.add(pattern, name="Pattern", opacity=0.5)

for block in blocks:
    scene.add(block)

group = scene.add_group(name="Normals")
for face in pattern.faces():
    point = pattern.face_centroid(face)
    normal = pattern.face_normal(face)
    line = Line.from_point_direction_length(point, normal, 0.3)
    group.add(line, linecolor=Color.blue())  # type: ignore

group = scene.add_group(name="Blocks")
group.add_from_list(blocks, show_faces=True, opacity=0.5)  # type: ignore

viewer.show()