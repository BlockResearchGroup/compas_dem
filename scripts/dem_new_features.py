import matplotlib.pyplot as plt
import numpy as np

from compas_dem.models import BlockModel
from compas_dem.templates import ArchTemplate

# Block Model using compas_dem's Arch Template
template: ArchTemplate = ArchTemplate(rise=4.393, span=21.213, thickness=0.5, depth=3.0, n=100)
model: BlockModel = BlockModel.from_template(template)

# Compute contacts to populate the graph with contact properties for each interface.
model.compute_contacts()

# import a compas_model material
from compas_model.materials import Concrete  # noqa: E402

# import a compas_dem specific material
from compas_dem.material import Stone  # noqa: E402

# Instantiate materials and add to the model
conc: Concrete = Concrete.from_strength_class("C30")
conc.density = 2000.0
model.add_material(conc)

limestone: Stone = Stone.from_predefined_material("LimeStone")
limestone.density = 2000.0
model.add_material(limestone)

# Print some properties to check everything is working
print(f"Limestone properties: Ecm={limestone.Ecm}, poisson={limestone.poisson}, density={limestone.density}")

# Assign materials to blocks based on centroid z-coordinate
for element in model.blocks():
    if element.modelgeometry.centroid()[2] > 0.5:
        model.assign_material(conc, element)
    else:
        model.assign_material(limestone, element)

# =============================================================================
# Create a problem instance
# =============================================================================

from compas_dem.problem import Problem  # noqa: E402

problem = Problem(model)


# Create Contact model and Joint model instances
# -----------------------------------------------

from compas_dem.interactions import MohrCoulomb  # noqa: E402
from compas_dem.interactions import JointModel

mohr_columb: MohrCoulomb = MohrCoulomb(phi=30, c=0)  # Mohr Columb is a contact model, thus it inherits from ContactModel, and can be assigned to the interfaces
# Other contact models can be simply added by inheriting from ContactModel and implementing the required methods/ parameters

print(f"Contact model properties: phi={mohr_columb.phi}, c={mohr_columb.c}, mu={mohr_columb.mu}")

joint_a: JointModel = JointModel(kn=10e10, kt=10e7)


# Create Contact Properties using the Contact and Joint models
# -------------------------------------------------------------

from compas_dem.interactions import ContactProperties  # noqa: E402

contact_type_1 = ContactProperties(contact_model=mohr_columb, joint_model=joint_a)


from compas_dem.problem import BoundaryConditions  # noqa: E402

bc = BoundaryConditions()
bc.add_point_load(block_index=70, force=[0, 0, -151500])
bc.add_fixed(block_index=0)
bc.add_fixed(block_index=99)

problem.apply_bc(bc)
problem.add_contact(contact_type_1)

# Solve the problem using the LMGC90 solver
# -----------------------------------------

solution = problem.solve(solver="LMGC90", duration=1.0, n_steps=3000)

# =============================================================================
# Visualize the model in the DEM Native viewer
# =============================================================================

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
viewer.add_solution("LMGC90", solution, scale_force=10e-7, scale_normal=0.0000001)  # Passing the scale KWARGS specific to LMGC90
viewer.show()
solution.finalize()
