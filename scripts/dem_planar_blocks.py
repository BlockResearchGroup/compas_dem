#! python3
# venv: brg-csd
# r: compas_model, Tessagon

import pathlib
import compas
from compas.datastructures import Mesh
from compas.geometry import Frame
from compas.geometry import Point
from compas.geometry import Transformation
from compas.geometry import Polyhedron
from compas.scene import MeshObject
from compas.scene import Scene
from compas_libigl.mapping import map_mesh
from compas_cgal.meshing import mesh_remesh
from compas_viewer import Viewer
from compas_dem.models import BlockModel
from compas_dem.modifiers.boolean_difference_modifier import BooleanDifferenceModifier
from compas_dem.modifiers.boolean_union_modifier import BooleanUnionModifier
from compas_dem.elements.interface import Interface

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

mv, mf, mn, mb, mg = map_mesh(trimesh.to_vertices_and_faces(), pattern.to_vertices_and_faces(), clip_boundaries=False, fixed_vertices=fixed_vertices, tolerance=1e-3)
pattern = Mesh.from_vertices_and_faces(mv, mf)
pattern.unify_cycles() # Unify the winding of polygons since user pattern winding might be inconsistent
pattern.flip_cycles()
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
viewer.scene.add(pattern.copy(), name="Pattern")


# =============================================================================
# Model
# =============================================================================

model = BlockModel.from_mesh_with_planar_faces(
    mesh=pattern,
    offset=0,
    chamfer=0.1,
    thickness_scale_bottom=-0.5,
    thickness_scale_top=1,
    project_bottom=False,
    project_top=True,
    tolerance_parallel=0.5
)


# =============================================================================
# Modifiers
# =============================================================================
elements = list(model.elements())

radius0 = 0.03
radius1 = 0.031
modifier_pairs = []

for edge in model.graph.edges():
    edge_attrs = model.graph.edge_attributes(edge)
    frame = edge_attrs["frame"]
    line = edge_attrs["line"]
    
    # Get two points along each edge
    points = [line.point_at(0.25), line.point_at(0.75)]
    
    for point in points:
        # Create frame for transformation
        frame_shear_key = Frame(point, frame.xaxis, frame.yaxis)
        xform = Transformation.from_frame(frame_shear_key)
        
        # Create and transform polyhedrons
        polyhedron0 = Polyhedron.from_platonicsolid(20).to_mesh().scaled(radius0)
        polyhedron1 = Polyhedron.from_platonicsolid(20).to_mesh().scaled(radius1)
        polyhedron0.transform(xform)
        polyhedron1.transform(xform)
        
        # Create interface elements
        interface0 = Interface(polyhedron0)
        interface1 = Interface(polyhedron1)
        
        # Store with connected elements
        modifier_pairs.append([interface0, interface1, elements[edge[0]], elements[edge[1]]])

# Add elements and modifiers in one loop
for interface0, interface1, elem0, elem1 in modifier_pairs:
    model.add_element(interface0)
    model.add_element(interface1)
    model.add_modifier(interface0, elem0, BooleanUnionModifier())
    model.add_modifier(interface1, elem1, BooleanDifferenceModifier())

# =============================================================================
# Vizualize
# =============================================================================

o = Point(5,5,0)
for block in model.elements():
    if block.name != "Interface":
        geometry = block.modelgeometry
        geometry.centroid()
        v = (o-geometry.centroid())*-0.05
        viewer.scene.add(geometry.translated(v), show_faces=True)
        viewer.scene.add(geometry.attributes["orientation_frame"].translated(v))

viewer.show()