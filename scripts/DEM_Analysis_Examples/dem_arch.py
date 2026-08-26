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
# viewer = DEMViewer(model)
# viewer.setup()
# viewer.config.renderer.show_grid = False
# viewer.show()
# raise
generic: Stone = Stone(density=2750)
model.add_material(generic)
model.assign_material(generic, elements=list(model.elements()))

# =============================================================================
# Problem
# =============================================================================

problem = Problem(model)
problem.set_contact_model("MohrCoulomb", phi=35, c=0.0)

# bc = problem.add_boundary_condition("Live")
# problem.add_point_load_at_centroid(block_index=16, force=[0, 0, -100000], boundary_condition=bc)
# lmgc90_1: Solver = Solver.LMGC90(dt=0.00056, duration=10.0, urf_threshold=1e-3, theta=0.7)
# lmgc90_2: Solver = Solver.LMGC90(dt=0.001, duration=1.0, urf_threshold=1e-3, theta=0.7)
lmgc90: Solver = Solver.LMGC90(dt=0.0005, duration=2.5)
prd: Solver = Solver.BLA()
cra: Solver = Solver.CRA()
# Solve using either lmgc90_1 or lmgc90_2; same solver, with different parameters.
problem.set_solver(prd)
result_bla = problem.solve()
problem.set_solver(lmgc90)
result_lmgc90 = problem.solve()
problem.set_solver(cra)
result_cra = problem.solve()
# =============================================================================
# Viz
# =============================================================================

viewer = DEMViewer(model)

viewer.add_solution(result_bla, name="PRD", scale=0.5)
viewer.add_solution(result_lmgc90, name="LMGC90", scale=0.5)
viewer.add_solution(result_cra, name="CRA", scale=0.5)

viewer.show()
