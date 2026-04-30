import os

import compas

from compas_dem.viewer import DEMViewer

# =============================================================================
# Load Problem
# =============================================================================

HERE = os.path.dirname(__file__)
problem = compas.json_load(
    os.path.join(HERE, "DEM_results.json"),
)

# =============================================================================
# Visualize block results
# =============================================================================
# for block in model.elements():
#     print(blo)


# # =============================================================================
# # Visualize problem
# # =============================================================================

viewer = DEMViewer(problem.model)
viewer.add_solution(scale=10e-5)
viewer.show()
