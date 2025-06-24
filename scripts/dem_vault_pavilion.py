import pathlib

import compas
from compas.geometry import Scale

from compas_dem.models import BlockModel
from compas_dem.viewer import DEMViewer

# =============================================================================
# Data
# =============================================================================

BLOCKS = pathlib.Path(__file__).parent.parent / "data" / "pavillionvault" / "blocks.json"
SUPPORTS = pathlib.Path(__file__).parent.parent / "data" / "pavillionvault" / "supports.json"

blocks = compas.json_load(BLOCKS)
supports = compas.json_load(SUPPORTS)

# =============================================================================
# Model and interactions
# =============================================================================

model = BlockModel()

for mesh in blocks:
    for part in mesh:
        model.add_block_from_mesh(part)

for mesh in supports:
    for part in mesh:
        model.add_support_from_mesh(part)


model.transform(Scale.from_factors([20, 20, 20]))

model.compute_contacts(tolerance=0.01)

# =============================================================================
# Viz
# =============================================================================

viewer = DEMViewer(model)

viewer.setup()
viewer.show()
