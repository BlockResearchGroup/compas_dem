from compas_dem.material import Stone
from compas_dem.models import BlockModel
from compas_dem.problem import Problem
from compas_dem.problem import Solver
from compas_dem.templates import ArchTemplate
from compas_dem.viewer import DEMViewer

# =============================================================================
# Template
# =============================================================================

template = ArchTemplate(rise=4.393, span=21.213, thickness=0.5, depth=3.0, n=100)

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

# ============================================================================
# Material
# ============================================================================

generic: Stone = Stone(density=2000)
model.add_material(generic)
model.assign_material(generic, elements=list(model.elements()))

# =============================================================================
# Problem
# =============================================================================

problem = Problem(model)
problem.add_contact_model("MohrCoulomb", phi=25, c=0.0)
problem.add_supports_from_model()
problem.add_point_load(block_index=67, force=[0, 0, -170000])
lmgc90_1: Solver = Solver.LMGC90(dt=0.00056, duration=10.0, urf_threshold=1e-3, theta=0.7)
lmgc90_2: Solver = Solver.LMGC90(dt=0.001, duration=1.0, urf_threshold=1e-3, theta=0.7)

# Solve using either lmgc90_1 or lmgc90_2; same solver, with different parameters.
problem.solve(lmgc90_2)

# =============================================================================
# Viz
# =============================================================================

viewer = DEMViewer(model)

viewer.add_solution(scale=0.5)
viewer.show()
