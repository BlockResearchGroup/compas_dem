import pathlib

import compas

from compas_dem.analysis import cra_penalty_solve
from compas_dem.analysis import rbe_solve
from compas_dem.elements import Block
from compas_dem.models import BlockModel
from compas_dem.viewers import BlockModelViewer

# =============================================================================
# Import
# =============================================================================

model: BlockModel = compas.json_load(pathlib.Path(__file__).parent / "dome.json")

# =============================================================================
# Supports
# =============================================================================

bottom: list[Block] = sorted(model.elements(), key=lambda e: e.point.z)[:16]
for block in bottom:
    block.is_support = True

# =============================================================================
# Equilibrium
# =============================================================================

rbe_solve(model, return_model=True)

# =============================================================================
# Viz
# =============================================================================

viewer = BlockModelViewer(model)
viewer.show()
