from compas_dem.material import Stone
from compas_dem.models import BlockModel
from compas_dem.problem import Problem
from compas_dem.templates import ArchTemplate
from compas_dem.viewer import DEMViewer

# Block Model using compas_dem's Arch Template
template: ArchTemplate = ArchTemplate(rise=4.393, span=21.213, thickness=0.5, depth=3.0, n=100)
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

# Create Contact model and Joint model instances
# -----------------------------------------------

# from compas_dem.interactions import MohrCoulomb  # noqa: E402, I001
# from compas_dem.interactions import JointModel  # noqa: E402

# mohr_columb: MohrCoulomb = MohrCoulomb(phi=30, c=0)  # Mohr Columb is a contact model, thus it inherits from ContactModel, and can be assigned to the interfaces
# # Other contact models can be simply added by inheriting from ContactModel and implementing the required methods/ parameters

# print(f"Contact model properties: phi={mohr_columb.phi}, c={mohr_columb.c}, mu={mohr_columb.mu}")

# joint_a: JointModel = JointModel(kn=10e10, kt=10e7)

# problem.add_contact_model("MohrCoulomb", phi=30, c=0)
# problem.add_joint_model("JointA", kn=10e10, kt=10e7)

# problem.add_contact(contact_model=mohr_columb, joint_model=joint_a)

# Create Contact Properties using the Contact and Joint models
# -------------------------------------------------------------

# from compas_dem.interactions import ContactProperties  # noqa: E402

# contact_type_1 = ContactProperties(contact_model=mohr_columb, joint_model=joint_a)

problem.add_contact_model("MohrCoulomb", phi=30, c=0)
problem.add_joint_model(kn=10e10, kt=10e7)
# contact_1 = model.graph.edge_attribute([0,1],"contact_properties")

# from compas_dem.problem import BoundaryConditions  # noqa: E402

# bc = BoundaryConditions()
# bc.add_point_load(block_index=70, force=[0, 0, -151500],point=[10.606, 10.606, 0])  # Apply a point load at the centroid of block 70
# bc.add_support(block_index=0)
# bc.add_support(block_index=99)

# problem.add_bc(bc)

# Add utlitity script that shows the block indices

# for block in model.blocks():
#     if block.modelgeometry.centroid()[2] < 0.5:
#         problem.add_support(block_index=block.graphnode)

# Select from rhino
# problem.inspect_model()  # This will print the block indices in the console for reference when adding BCs

problem.add_support(block_index=0)
problem.add_support(block_index=99)
# problem.add_displacement(block_index=0, dx=0.8, dy=0, dz=0)
# problem.add_supports()
# problem.add_supports_from_model()
problem.add_point_load(block_index=70, force=[0, 0, -151500])

# keep BC class, but populate into problem directly, then add the data to BC dict inside problem.

# Solve the problem using the LMGC90 solver
# -----------------------------------------

solution = problem.solve(solver="LMGC90", duration=1.0, n_steps=100, urf_threshold=0.001)

# =============================================================================
# Visualize the model in the DEM Native viewer
# =============================================================================

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

# graph = model.graph
# for edge in model.graph.edges():
#     print(
#         f"Edge {edge} attributes: \n Force: {graph.edge_attribute(edge, 'force')}, \n contact_points: {graph.edge_attribute(edge, 'contact_point')},\n contact_polygon: {graph.edge_attribute(edge, 'contact_polygon')}, friction_contact: {graph.edge_attribute(edge, 'friction_contact')}"
#     )

# for block in model.blocks():
#     print(f"Block {block.graphnode} attributes: \n Displacement: {block.displacement.translation_vector}, rotation: {block.displacement.rotation}")


viewer = DEMViewer(model)
viewer.add_solution(solution=solution, solver_name="LMGC90", scale_force=8e-7)
viewer.show()
solution.finalize()
