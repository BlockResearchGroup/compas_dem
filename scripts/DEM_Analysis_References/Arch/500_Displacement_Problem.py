import os

import compas
from compas_dem.problem import Problem
from compas_dem.viewer import DEMViewer

# =============================================================================
# Load model
# =============================================================================

HERE = os.path.dirname(__file__)
model = compas.json_load(
    os.path.join(HERE, "DEM_model.json"),
)

# =============================================================================
# Create Problem
# =============================================================================

problem = Problem(model)

# =============================================================================
# Add supports
# =============================================================================

problem.add_support(block_index=29)

# =============================================================================
# Add displacement to problem
# =============================================================================

problem.add_displacement(block_index=0, dx=-0.05)

# =============================================================================
# Add contact properties
# =============================================================================

problem.add_contact_model("MohrCoulomb", mu=0.5)

# =============================================================================
# Save problem
# =============================================================================

HERE = os.path.dirname(__file__)
compas.json_dump(problem, os.path.join(HERE, "DEM_problem_updated.json"))

viewer = DEMViewer(problem.model)
viewer.setup()
viewer.show()
