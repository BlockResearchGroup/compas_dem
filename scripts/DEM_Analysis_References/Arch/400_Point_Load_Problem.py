import os

import compas

from compas_dem.problem import Problem

# =============================================================================
# Load Problem
# =============================================================================

HERE = os.path.dirname(__file__)
problem: Problem = compas.json_load(
    os.path.join(HERE, "DEM_problem.json"),
)

# =============================================================================
# Add point load to problem
# =============================================================================

problem.add_point_load(block_index=14, force=[0, 0, -500000.0])

# =============================================================================
# Save results
# =============================================================================
problem.inspect_model()

HERE = os.path.dirname(__file__)
compas.json_dump(problem, os.path.join(HERE, "DEM_problem_updated.json"))

# =============================================================================
# Visualize problem
# =============================================================================

# viewer = DEMViewer(problem.model)
# viewer.add_solution(scale=10e-12)
# viewer.show()
