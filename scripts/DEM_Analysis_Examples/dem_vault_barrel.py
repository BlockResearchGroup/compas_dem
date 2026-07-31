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

template = BarrelVaultTemplate(length=3, span=5, rise=1.0, vou_length=13)

# =============================================================================
# Model and interactions
# =============================================================================

model = BlockModel.from_barrelvault(template)

model.compute_contacts(tolerance=0.001)

limestone = Stone.from_predefined_material("LimeStone")
limestone.density = 2400
model.add_material(limestone)
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
problem.set_contact_model("MohrCoulomb", mu=0.6, c=0)
lmgc90 = Solver.LMGC90(duration=0.2, n_steps=100, urf_threshold=1e-3, theta=0.7)
prd = Solver.PRD()
bla = Solver.BLA()
cra = Solver.CRA()
rbe = Solver.RBE()

problem.set_solver(bla)
solution_bla = problem.solve().copy()

problem.set_solver(lmgc90)
solution_lmgc90 = problem.solve().copy()

problem.set_solver(rbe)
solution_rbe = problem.solve().copy()


# problem.set_solver(cra)
# solution_cra = problem.solve().copy()

# =============================================================================
# Viz
# =============================================================================

viewer = DEMViewer(model)

viewer.setup()
viewer.add_solution(solution_bla, name="BLA", scale=1)
viewer.add_solution(solution_lmgc90, name="LMGC90", scale=1)
viewer.add_solution(solution_rbe, name="RBE", scale=1)
# viewer.add_solution(solution_cra, name="CRA", scale=1)
viewer.show()
