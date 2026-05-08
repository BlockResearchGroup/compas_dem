"""Compute the equilibrium of an arch structure using the CRA method.

To run this script, install `compas_dem` and its dependencies using the preconfigured
"dem-dev" environment in the `compas_dem` repo.

    $ conda env create -f environment.yml
    $ conda activate dem-dev

"""

from compas_dem.material import Stone
from compas_dem.models import BlockModel
from compas_dem.problem import Problem
from compas_dem.problem import Solver
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
# Material
# =============================================================================

generic_stone = Stone.from_predefined_material("Generic")
generic_stone.density = 2000
model.add_material(generic_stone)
model.assign_material(generic_stone, elements=list(model.elements()))

# =============================================================================
# Problem setup and solve
# =============================================================================

problem = Problem(model)
problem.add_contact_model("MohrCoulomb", mu=0.5, c=0.0)
problem.add_supports_from_model()
cra_solver = Solver.CRA()
solution = problem.solve(cra_solver)

# =============================================================================
# Viz
# =============================================================================

viewer = DEMViewer(model)
viewer.add_solution()
viewer.show()
