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
# Supports come from the model (see 100_init.py), so the problem itself only
# carries the contact behaviour and the boundary conditions.

problem = Problem(model, name="Self-weight")

# =============================================================================
# Add contact properties
# =============================================================================

problem.set_contact_model("MohrCoulomb", mu=0.5)

# =============================================================================
# Save problem into the analysis
# =============================================================================
# Dropping a problem of the same name first keeps this script re-runnable.

analysis.problems = [p for p in analysis.problems if p.name != problem.name]
analysis.add_problem(problem)

compas.json_dump(analysis, PATH)

# =============================================================================
# Visualize problem
# =============================================================================

viewer = DEMViewer(model)
viewer.setup()
viewer.show()
