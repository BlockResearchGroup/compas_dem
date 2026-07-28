from compas_dem.material import Stone
from compas_dem.models import BlockModel
from compas_dem.problem import Problem
from compas_dem.problem import Solver
from compas_dem.templates import ArchTemplate
from compas_dem.utilities import find_load_multiplier
from compas_dem.utilities import plot_safety_diagram
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
generic: Stone = Stone(density=2000)
model.add_material(generic)
model.assign_material(generic, elements=list(model.elements()))

# =============================================================================
# Problem
# =============================================================================

problem = Problem(model)
problem.add_contact_model("MohrCoulomb", phi=35, c=0.0)
problem.add_supports_from_model(model)

# problem.add_point_load(block_index=16, force=[0, 0, -100000])
# lmgc90_1: Solver = Solver.LMGC90(dt=0.00056, duration=10.0, urf_threshold=1e-3, theta=0.7)
# lmgc90_2: Solver = Solver.LMGC90(dt=0.001, duration=1.0, urf_threshold=1e-3, theta=0.7)
prd: Solver = Solver.BLA()
# Solve using either lmgc90_1 or lmgc90_2; same solver, with different parameters.
problem.solver(prd)
result = model.solve(problem)
result_prd = result.copy()
# =============================================================================
# Viz
# =============================================================================

lam, result_max = find_load_multiplier(problem, model, prd, live_loads=[[20, [0, 0, -1]]], lam_start=150000.0, tol=1e-3, max_iter=30, verbose=True)
plot_safety_diagram(result_max, show=True)
viewer = DEMViewer(model)

viewer.add_solution(result_prd, name="PRD", scale=0.5)
viewer.add_solution(result_max, name="max_load", scale=0.5)
viewer.show()
