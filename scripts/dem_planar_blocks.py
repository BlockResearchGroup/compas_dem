#! python3
# venv: brg-csd
# r: compas_model, Tessagon

import pathlib
import compas
from compas.colors import Color
from compas.datastructures import Mesh
from compas.geometry import Point
from compas.scene import MeshObject
from compas.scene import Scene
from compas_libigl.mapping import map_mesh
from compas_cgal.meshing import mesh_remesh
from compas_viewer import Viewer
from compas_dem.models import BlockModel
from compas_dem.fabrication.offset import offset_planar_blocks

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
pattern.unify_cycles() # Unify the winding of polygons since user pattern winding might be inconsistent

temp_polygons = pattern.to_polygons()

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

viewer = Viewer()
viewer.scene.add(pattern, name="Pattern", opacity=0.5)
blocks = offset_planar_blocks(
    pattern, 
    offset=0.0,
    chamfer=0.1, 
    thickness_scale_bottom=0.5, 
    thickness_scale_top=1.0, 
    project_bottom=True, 
    project_top=False,
    tolerance_parallel=0.5)

# =============================================================================
# Model
# =============================================================================
    
model = BlockModel()

for block in blocks:
    model.add_block_from_mesh(block)

model.compute_contacts()

for block in blocks:
    viewer.scene.add(block, show_faces=True)

for contact in model.contacts():
    viewer.scene.add(contact.polygon, surfacecolor=Color.cyan())

viewer.show()