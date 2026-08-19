import os

import compas
from compas_dem.models import Analysis
from compas_dem.problem import Problem
from compas_dem.viewer import DEMViewer

# =============================================================================
# Load analysis
# =============================================================================

HERE = os.path.dirname(__file__)
PATH = os.path.join(HERE, "DEM_analysis.json")

analysis: Analysis = compas.json_load(PATH)
model = analysis.model

# =============================================================================
# Create Problem
# =============================================================================

problem = Problem(model, name="Settlement")

# =============================================================================
# Add displacement to problem
# =============================================================================
# Block 0 is a support (see 100_init.py); a prescribed displacement on a support
# overrides its fixity component by component, which is the settlement idiom.

settlement = problem.add_boundary_condition("Settlement")
problem.add_displacement(block_index=0, displacement=[-0.05, 0, 0], boundary_condition=settlement)

# =============================================================================
# Add contact properties
# =============================================================================

problem.set_contact_model("MohrCoulomb", mu=0.5)

# =============================================================================
# Save problem into the analysis
# =============================================================================

analysis.problems = [p for p in analysis.problems if p.name != problem.name]
analysis.add_problem(problem)

compas.json_dump(analysis, PATH)

viewer = DEMViewer(model)
viewer.setup()
viewer.show()
