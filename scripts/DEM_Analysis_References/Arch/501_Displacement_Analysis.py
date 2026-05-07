import os

import compas

from compas_dem.problem import Problem
from compas_dem.problem import Solver

# =============================================================================
# Load Problem
# =============================================================================

HERE = os.path.dirname(__file__)
problem: Problem = compas.json_load(
    os.path.join(HERE, "DEM_problem_updated.json"),
)

print(f"Problem loaded with {problem.centroidal_displacements[0]}")
# =============================================================================
# Create Problem
# =============================================================================
lmgc90 = Solver.LMGC90(duration=1.0, n_steps=100, urf_threshold=0.001)
problem.solve(lmgc90)


# =============================================================================
# Save results
# =============================================================================

HERE = os.path.dirname(__file__)
compas.json_dump(problem, os.path.join(HERE, "DEM_results.json"))
