import pathlib

import compas
from compas.datastructures import Mesh

from compas_dem.models import BlockModel
from compas_dem.viewer import DEMViewer

# =============================================================================
# ThrustDiagram
# =============================================================================

filepath = pathlib.Path(__file__).parent.parent / "data" / "ThrustDiagram.json"

mesh: Mesh = compas.json_load(filepath)  # type: ignore

# =============================================================================
# Model and interactions
# =============================================================================

model = BlockModel.from_triangulation_dual(mesh, lengthfactor=0.5, tmin=0.05, tmax=0.3)

# model.compute_contacts(tolerance=0.001)

# =============================================================================
# Viz
# =============================================================================

viewer = DEMViewer(model)
viewer.scene.add(mesh)
viewer.setup()
viewer.show()
