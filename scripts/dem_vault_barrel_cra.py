"""Compute the equilibrium of an arch structure using the CRA method.

To run this script, install `compas_dem` and its dependencies using the preconfigured
"dem-dev" environment in the `compas_dem` repo.

    $ conda env create -f environment.yml
    $ conda activate dem-dev

"""

from compas_dem.analysis.cra import cra_penalty_solve
from compas_dem.models import BlockModel
from compas_dem.templates import BarrelVaultTemplate
from compas_dem.viewer import DEMViewer

# =============================================================================
# Template
# =============================================================================

template = BarrelVaultTemplate()

# =============================================================================
# Model and interactions
# =============================================================================

model = BlockModel.from_barrelvault(template)

model.compute_contacts(tolerance=0.001)

# =============================================================================
# Equilibrium
# =============================================================================

cra_penalty_solve(model)

# =============================================================================
# Viz
# =============================================================================

viewer = DEMViewer(model)

viewer.setup()
viewer.show()
