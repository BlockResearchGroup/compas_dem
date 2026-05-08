from compas_dem.material import Stone
from compas_dem.models import BlockModel
from compas_dem.problem import Problem
from compas_dem.problem import Solver
from compas_dem.templates import ArchTemplate
from compas_dem.viewer import DEMViewer

# =============================================================================
# Template
# =============================================================================

template = ArchTemplate(rise=3, span=10, thickness=0.5, depth=0.5, n=50)

# =============================================================================
# Model
# =============================================================================

model = BlockModel.from_template(template)

# =============================================================================
# Interactions
# =============================================================================

model.compute_contacts(tolerance=0.001)

# =============================================================================
# Supports
# =============================================================================

for node in model.graph.nodes_where(degree=1):
    model.graph.node_element(node).is_support = True  # type: ignore

# =============================================================================
# Material
# =============================================================================
limestone = Stone.from_predefined_material("LimeStone")
model.add_material(limestone)
limestone.density = 2000
model.assign_material(limestone, elements=list(model.elements()))

# =============================================================================
# Problem
# =============================================================================
problem = Problem(model)
problem.add_contact_model("MohrCoulomb", phi=40, c=0)
problem.add_support(49)

problem.add_displacement(block_index=0, displacement=[-0.1, 0, 0], rotation=[0, 0, 0])
lmgc90 = Solver.LMGC90(n_steps=100, dt=0.01)
solution = problem.solve(lmgc90)
# =============================================================================
# Viz
# =============================================================================

viewer = DEMViewer(model)

viewer.setup()
viewer.add_solution(scale=0.5)
viewer.show()
