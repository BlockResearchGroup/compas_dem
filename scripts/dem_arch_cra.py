"""Compute the equilibrium of an arch structure using the CRA method.

To run this script, install `compas_dem` and its dependencies using the preconfigured
"dem-dev" environment in the `compas_dem` repo.

    $ conda env create -f environment.yml
    $ conda activate dem-dev

"""

from compas_dem.analysis.cra import cra_penalty_solve
from compas_dem.models import BlockModel
from compas_dem.templates import ArchTemplate
from compas_dem.viewer import DEMViewer

# =============================================================================
# Template
# =============================================================================

template = ArchTemplate(rise=3, span=10, thickness=0.25, depth=0.5, n=50)

# =============================================================================
# Model and interactions
# =============================================================================

model = BlockModel.from_template(template)

model.compute_contacts(tolerance=0.001)

# =============================================================================
# Supports
# =============================================================================

for element in model.elements():
    if model.graph.degree(element.graphnode) == 1:
        element.is_support = True

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
