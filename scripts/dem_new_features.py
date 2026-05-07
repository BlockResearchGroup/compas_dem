from compas_dem.material import Stone
from compas_dem.models import BlockModel
from compas_dem.problem import Problem
from compas_dem.problem import Solver
from compas_dem.templates import ArchTemplate
from compas_dem.viewer import DEMViewer

# Block Model using compas_dem's Arch Template
template: ArchTemplate = ArchTemplate(rise=4.393, span=21.213, thickness=0.5, depth=3.0, n=100)
model: BlockModel = BlockModel.from_template(template)

# Compute contacts to populate the graph with contact properties for each interface.
model.compute_contacts()

# Instantiate materials and add to the model
limestone: Stone = Stone.from_predefined_material("LimeStone")
model.add_material(limestone)
model.assign_material(limestone, elements=list(model.blocks()))

# =============================================================================
# Create a problem instance
# =============================================================================

problem = Problem(model)

# -----------------------------------------------

problem.add_contact_model("MohrCoulomb", phi=30, c=0)
problem.add_joint_model(kn=10e10, kt=10e7)
problem.add_support(block_index=0)
problem.add_support(block_index=99)
problem.add_point_load(block_index=70, force=[0, 0, -151500])

# keep BC class, but populate into problem directly, then add the data to BC dict inside problem.

# Solve the problem using the LMGC90 solver
# -----------------------------------------
cra = Solver.CRA(verbose=True)
# lmgc90 = Solver.LMGC90(duration=1.0, n_steps=100, urf_threshold=0.001)
solution = problem.solve(cra)

# =============================================================================
# Visualize the model in the DEM Native viewer
# =============================================================================

viewer = DEMViewer(model)
viewer.add_solution(scale=0.5)
viewer.show()
