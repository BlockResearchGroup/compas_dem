import os

import compas

from compas_dem.problem import Solver
from compas_dem.viewer import DEMViewer

# =============================================================================
# Load Problem
# =============================================================================

HERE = os.path.dirname(__file__)
problem = compas.json_load(
    os.path.join(HERE, "DEM_problem.json"),
)

# =============================================================================
# Create Problem
# =============================================================================

# lmgc90 = Solver.LMGC90(duration=1.0, n_steps=100, urf_threshold=0.001)
# problem.solve(lmgc90)

rbe = Solver.RBE()
problem.solve(rbe)

# =============================================================================
# Save results
# =============================================================================

HERE = os.path.dirname(__file__)
compas.json_dump(problem, os.path.join(HERE, "DEM_results.json"))

# # =============================================================================
# # Visualize problem
# # =============================================================================

viewer = DEMViewer(problem.model)
viewer.add_solution(scale=10e-12)
viewer.show()
