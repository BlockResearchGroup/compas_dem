#! python3
# venv: brg-csd
# r: compas_model, Tessagon, compas_cgal==0.9.1, compas_libigl==0.7.4

import pathlib
import compas
from compas.datastructures import Mesh
from compas.geometry import Frame
from compas.geometry import Point
from compas.geometry import Vector
from compas.geometry import Transformation
from compas.geometry import Polyhedron
from compas.geometry import Polygon
from compas.scene import MeshObject
from compas.scene import Scene
from compas_libigl.mapping import map_mesh
from compas_cgal.meshing import trimesh_dual
from compas_libigl.parametrisation import trimesh_lsc_mapping
from compas_dem.models import BlockModel
from compas_dem.modifiers.boolean_difference_modifier import BooleanDifferenceModifier
from compas_dem.modifiers.boolean_union_modifier import BooleanUnionModifier
from compas_dem.elements.interface import Interface
import compas_rhino
import Rhino

# =============================================================================
# RhinoVault mesh
# =============================================================================

session = compas.json_load(pathlib.Path(__file__).parent.parent / "data" / "rv_pattern.json")
scene: Scene = session["scene"]
sceneobj: MeshObject = scene.find_by_name("ThrustDiagram")  # type: ignore
mesh: Mesh = sceneobj.mesh.copy()

for face in list(mesh.faces_where(_is_loaded=False)):
    mesh.delete_face(face)

# =============================================================================
# Remesh and Flatten
# =============================================================================

V, F, DV, DF = trimesh_dual(mesh.to_vertices_and_faces(True),1.0,10,0.9,1.0 )
mesh = Mesh.from_vertices_and_faces(V, F)
pattern = Mesh.from_vertices_and_faces(DV, DF)
pattern.unify_cycles()

mv = []
mn = []
for vertex in pattern.vertices():
    mv.append(Vector(*pattern.vertex_point(vertex)))
    mn.append(Vector(*pattern.vertex_normal(vertex)))

# ==============================================================================
# Least-squares conformal map - to see where the pattern is mapped.
# ==============================================================================

uv = trimesh_lsc_mapping((V, F))
mesh_lscm = mesh.copy()
for i in range(mesh.number_of_vertices()):
    mesh_lscm.vertex_attributes(i, "xyz", [uv[i][0], uv[i][1], 0])


# ==============================================================================
# Select Pattern
# ==============================================================================

guids = compas_rhino.objects.select_objects()
polygons = []

for guid in guids:
    obj = compas_rhino.objects.find_object(guid)
    if isinstance(obj, Rhino.DocObjects.CurveObject):
        polyline = compas_rhino.conversions.curve_to_compas_polyline(obj.Geometry)
        polygon = Polygon(polyline.points[:-1])
        polygons.append(polygon)

pattern = Mesh.from_polygons(polygons)

mv, mf, mn, mb, mg = map_mesh((V, F), pattern.to_vertices_and_faces(), clip_boundaries=False, fixed_vertices=[], tolerance=1e-3)
pattern = Mesh.from_vertices_and_faces(mv, mf)
pattern.unify_cycles()

# ===========================================================================
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
    tolerance_parallel=0.5,
    vertex_normals=mn,
)

m_o = pattern.copy()
for v in m_o.vertices():
    n = m_o.vertex_normal(v)
    t = m_o.vertex_attribute(v, "thickness")
    m_o.set_vertex_point(v, m_o.vertex_point(v) + n * t * 0.5)

# =============================================================================
# Modifiers
# model.add_shear_keys(edges_frames, edges_lines, shape0, shape1)
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

scene = Scene()
elements = list(model.elements())
for e in elements:
    if(e.name == "Block"):
        mesh = e.modelgeometry
        scene.add(mesh)

      
scene.draw()
