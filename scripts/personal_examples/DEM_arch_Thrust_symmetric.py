from compas_dem.models import BlockModel
from compas_dem.problem import LoadCase
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

lc1 = LoadCase(name="Gravity")
lc2 = LoadCase(name="Displacement")
# lc3 = LoadCase(name="Surface Load")
# lc4 = LoadCase(name="Point Load")

problem.add_loadcase(lc1)
problem.add_loadcase(lc2)
# problem.add_loadcase(lc3)
# problem.add_loadcase(lc4)

problem.add_displacement(block_index=0, displacement=[0.2, 0, 0], loadcase=lc2)

# for b_idx in range(25, 36):
#     problem.add_surface_load(block_index=b_idx, load=(0, 0, -10000), face_index=4, loadcase=lc3)

# problem.add_point_load(block_index=80, force=[0, 0, -100000], loadcase=lc4)

# PATH = pathlib.Path(__file__).parent / "dem_arch.json"
# compas.json_dump(data=problem, fp=PATH)
# problem.inspect_model(model)

# solver: Solver = Solver.LMGC90(dt=0.001, duration=1)
solver: Solver = Solver.BLA(linear=False)
problem.solver(solver)
result = model.solve(problem)

# Viewer
viewer = DEMViewer(model)
# viewer.setup()
viewer.add_solution(result, scale=0.5)
viewer.show()
