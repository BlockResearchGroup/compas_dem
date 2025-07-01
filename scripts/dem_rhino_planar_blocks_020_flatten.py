#! python3
# venv: brg-csd
# r: compas_model, Tessagon, compas_cgal==0.9.1, compas_libigl==0.7.4

import pathlib
import compas
from compas.datastructures import Mesh
from compas.geometry import Vector
from compas.scene import MeshObject
from compas.scene import Scene
from compas_cgal.meshing import trimesh_dual
from compas_libigl.parametrisation import trimesh_lsc_mapping


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

V, F, DV, DF = trimesh_dual(mesh.to_vertices_and_faces(True),1.0,10,0.9,0.0 )
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

# =============================================================================
# Vizualize
# =============================================================================

scene = Scene()
scene.add(mesh)
scene.add(mesh_lscm)
scene.draw()
