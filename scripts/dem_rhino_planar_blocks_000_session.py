#! python3
# venv: brg-csd
# r: compas_model, Tessagon, compas_cgal==0.9.1, compas_libigl==0.7.4

import pathlib
import compas
from compas.datastructures import Mesh
from compas.scene import MeshObject
from compas.scene import Scene

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
# Vizualize
# =============================================================================

scene = Scene()
scene.add(sceneobj.mesh)
scene.add(mesh)
scene.draw()
