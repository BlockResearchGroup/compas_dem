import pathlib

import compas
from compas.datastructures import Mesh
from compas.datastructures import mesh_conway_ambo
from compas_viewer.viewer import Viewer

# =============================================================================
# ThrustDiagram
# =============================================================================

filepath = pathlib.Path(__file__).parent.parent / "data" / "ThrustDiagram.json"

mesh: Mesh = compas.json_load(filepath)  # type: ignore

# =============================================================================
# Model and interactions
# =============================================================================

conway = mesh_conway_ambo(mesh)
# conway = mesh_conway_bevel(mesh)
# conway = mesh_conway_dual(mesh)
# conway = mesh_conway_expand(mesh)
# conway = mesh_conway_gyro(mesh)
# conway = mesh_conway_join(mesh)
# conway = mesh_conway_kis(mesh)
# conway = mesh_conway_meta(mesh)
# conway = mesh_conway_needle(mesh)

# =============================================================================
# Viz
# =============================================================================

viewer = Viewer()
viewer.scene.add(conway)
viewer.show()
