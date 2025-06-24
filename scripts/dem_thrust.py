import pathlib
import random

import compas
from compas.datastructures import Mesh
from compas_libigl.mapping import TESSAGON_TYPES

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

patternname = random.choice(list(TESSAGON_TYPES.keys()))

model = BlockModel.from_meshpattern(mesh, patternname, tmin=0.05, tmax=0.3)

model.compute_contacts(tolerance=0.001)

# =============================================================================
# Viz
# =============================================================================

viewer = DEMViewer(model)

viewer.setup()
viewer.show()
