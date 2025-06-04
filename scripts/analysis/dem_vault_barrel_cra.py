from compas.colors import Color

from compas_dem.analysis import cra_penalty_solve
from compas_dem.analysis import rbe_solve
from compas_dem.models import BlockModel
from compas_dem.templates import BarrelVaultTemplate
from compas_dem.viewers import BlockModelViewer

# =============================================================================
# Template
# =============================================================================

template = BarrelVaultTemplate()

# =============================================================================
# Model and interactions
# =============================================================================

model = BlockModel.from_barrelvault(template)

model.compute_contacts(k=6)

# =============================================================================
# Equilibrium
# =============================================================================

# rbe_solve(model)
cra_penalty_solve(model)

# =============================================================================
# Viz
# =============================================================================

viewer = BlockModelViewer(model)
viewer.show()
