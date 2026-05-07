import os

import compas

from compas_dem.problem import Solver

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

cra = Solver.CRA(verbose=True)
problem.solve(cra)

# =============================================================================
# Save results
# =============================================================================

HERE = os.path.dirname(__file__)
compas.json_dump(problem, os.path.join(HERE, "DEM_results.json"))
