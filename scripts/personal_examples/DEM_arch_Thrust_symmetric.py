from compas_dem.models import BlockModel
from compas_dem.problem import BoundaryCondition
from compas_dem.problem import Problem
from compas_dem.problem import Solver
from compas_dem.templates import ArchTemplate
from compas_dem.viewer import DEMViewer
from compas_model.materials import Concrete

arch = ArchTemplate(rise=2.0, span=8.0, depth=0.8, thickness=0.5, n=14)

model = BlockModel.from_template(arch)

for block in model.elements():
    if block.modelgeometry.centroid()[2] < 0.3:
        block.is_support = True
model.compute_contacts()


for node in model.graph.nodes_where(degree=1):
    model.graph.node_element(node).is_support = True  # type: ignore

conc = Concrete.from_strength_class("C30")
model.add_material(material=conc)
model.assign_material(conc, elements=list(model.elements()))


for block in model.elements():
    block.material = conc


problem = Problem(model)
problem.add_contact_model("MohrCoulomb", phi=35, c=0.0)
problem.add_supports_from_model(model)
problem.add_joint_model(kn=1e9, kt=5e8)

bc1 = BoundaryCondition(name="Gravity")
bc2 = BoundaryCondition(name="Displacement")

problem.add_boundary_condition(bc1)
problem.add_boundary_condition(bc2)

problem.add_displacement(block_index=0, displacement=[0.5, 0, 0], boundary_condition=bc2)
