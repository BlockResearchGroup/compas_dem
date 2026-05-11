"""Compute the equilibrium of an arch structure using the LMGC90 solver.

To run this script, install `compas_dem` and its dependencies using the preconfigured
"dem-dev" environment in the `compas_dem` repo.

    $ conda env create -f environment.yml
    $ conda activate dem-dev

"""

from compas_dem.material import Stone
from compas_dem.models import BlockModel
from compas_dem.problem import Problem
from compas_dem.problem import Solver
from compas_dem.templates import BarrelVaultTemplate
from compas_dem.viewer import DEMViewer

# =============================================================================
# Template
# =============================================================================

template = BarrelVaultTemplate(length=3, span=7, rise=0.1, vou_length=13)

# =============================================================================
# Model and interactions
# =============================================================================

model = BlockModel.from_barrelvault(template)

model.compute_contacts(tolerance=0.001)

limestone = Stone.from_predefined_material("LimeStone")
model.add_material(limestone)
limestone.density = 2400
model.assign_material(limestone, elements=list(model.elements()))

# =============================================================================
# Supports
# =============================================================================
for node in model.graph.nodes_where(degree=1):
    model.graph.node_element(node).is_support = True

# =============================================================================
# Problem
# =============================================================================

problem = Problem(model)
problem.add_contact_model("MohrCoulomb", phi=40, c=0)
problem.add_supports_from_model()

# =============================================================================
# Solver
# =============================================================================

rbe = Solver.RBE(verbose=True)
solution = problem.solve(rbe)

# =============================================================================
# Viz
# =============================================================================

viewer = DEMViewer(model)

viewer.setup()
viewer.add_solution(scale=1)
viewer.show()
