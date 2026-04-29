import matplotlib.pyplot as plt
import numpy as np
from compas_model.materials import Concrete

# import a compas_dem specific material
from compas_dem.material import Stone
from compas_dem.models import BlockModel
from compas_dem.problem import Problem
from compas_dem.templates import ArchTemplate

# Block Model using compas_dem's Arch Template
template: ArchTemplate = ArchTemplate(rise=4.393, span=21.213, thickness=0.5, depth=3.0, n=10)
model: BlockModel = BlockModel.from_template(template)

# Compute contacts to populate the graph with contact properties for each interface.
model.compute_contacts()

# Instantiate materials and add to the model
# conc: Concrete = Concrete.from_strength_class("C30")
# conc.density = 2000.0
# model.add_material(conc)

limestone: Stone = Stone.from_predefined_material("LimeStone")
limestone.density = 2000.0
model.add_material(limestone)

# Print some properties to check everything is working
print(f"Limestone properties: Ecm={limestone.Ecm}, poisson={limestone.poisson}, density={limestone.density}")

model.assign_material(limestone, elements=list(model.blocks()))
# Assign materials to blocks based on centroid z-coordinate
# for element in model.blocks():
#     if element.modelgeometry.centroid()[2] > 0.5:
#         model.assign_material(conc, element)
#     else:
#         model.assign_material(limestone, element)

# =============================================================================
# Create a problem instance
# =============================================================================


problem = Problem(model)

problem.add_contact_model("MohrCoulomb", phi=30, c=0)
problem.add_joint_model(kn=10e10, kt=10e7)

# problem.inspect_model()  # This will print the block indices in the console for reference when adding BCs
problem.add_support(block_index=0)
problem.add_support(block_index=9)

# Solve the problem using the CRA solver
# -----------------------------------------
# from compas_dem.analysis.solvers import SolverCRA  # noqa: E402

# solver = SolverCRA()

solution = problem.solve("cra", method="rbe")

# =============================================================================
# Visualize the model in the DEM Native viewer
# =============================================================================

# for block in model.blocks():
#     print(f"Block {block.graphnode} transformation: {block.result_transformation.translation}, {block.result_transformation.rotation}")

# for edge in model.graph.edges():
#     print(f"Force in edge {edge}: {model.graph.edge_attribute(edge, 'gap')}")
# force_time = solution.force_time
# mean_forces = [np.mean(f) if len(f) > 0 else 0.0 for f in force_time]

# plt.figure(figsize=(10, 5))
# plt.plot(mean_forces)
# plt.xlabel("Time step")
# plt.ylabel("Mean contact force magnitude")
# plt.title("Contact force magnitudes over time")
# plt.tight_layout()
# plt.show()

from compas_dem.viewer import DEMViewer  # noqa: E402

viewer = DEMViewer(model)
viewer.add_solution(solution=solution, scale_force=1e-5)
viewer.show()
