import pathlib

import compas
from compas.datastructures import Mesh
from compas.datastructures import mesh_conway_ambo
from compas.datastructures import mesh_conway_bevel
from compas.datastructures import mesh_conway_dual
from compas.datastructures import mesh_conway_expand
from compas.datastructures import mesh_conway_gyro
from compas.datastructures import mesh_conway_join
from compas.datastructures import mesh_conway_kis
from compas.datastructures import mesh_conway_meta
from compas.datastructures import mesh_conway_needle
from compas.datastructures import mesh_conway_ortho
from compas.datastructures import mesh_conway_snub
from compas.datastructures import mesh_conway_truncate
from compas.datastructures import mesh_conway_zip
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
