#! python3
# venv: brg-csd
# r: compas_model, Tessagon, compas_cgal==0.9.1, compas_libigl==0.7.4

import pathlib
import compas
from compas.datastructures import Mesh
from compas.geometry import Vector
from compas.geometry import Polygon
from compas.scene import MeshObject
from compas.scene import Scene
from compas_libigl.mapping import map_mesh
from compas_cgal.meshing import trimesh_dual
from compas_libigl.parametrisation import trimesh_lsc_mapping
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

mv, mf, mn, mb, mg = map_mesh((V, F), pattern.to_vertices_and_faces(), clip_boundaries=True, fixed_vertices=[], tolerance=1e-3)
pattern = Mesh.from_vertices_and_faces(mv, mf)
pattern.unify_cycles()

# =============================================================================
# Vizualize
# =============================================================================

scene = Scene()
scene.add(pattern)
scene.add(mesh_lscm)
scene.draw()
