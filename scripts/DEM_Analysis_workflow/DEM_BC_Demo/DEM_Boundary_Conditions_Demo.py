import pathlib

import compas
from compas_dem.material import Stone
from compas_dem.models import BlockModel
from compas_dem.problem import Problem
from compas_dem.problem import Solver
from compas_dem.templates import ArchTemplate
from compas_dem.viewer import DEMViewer

# =============================================================================
# Template
# =============================================================================

template = ArchTemplate(rise=4.393, span=21.213, thickness=0.5, depth=3.0, n=15)

# =============================================================================
# Model
# =============================================================================

model = BlockModel.from_template(template)

# =============================================================================
# Interactions
# =============================================================================

model.compute_contacts(tolerance=0.001)

# =============================================================================
# Supports
# =============================================================================

for node in model.graph.nodes_where(degree=1):
    model.graph.node_element(node).is_support = True  # type: ignore

# ============================================================================
# Material
# ============================================================================

generic: Stone = Stone(density=2000)
model.add_material(generic)
model.assign_material(generic, elements=list(model.elements()))

# =============================================================================
# Dump Model
# =============================================================================

compas.json_dump(data=model, fp=pathlib.Path(__file__).parent / "dem_arch_model.json")

# =============================================================================
# Problem
# =============================================================================

problem = Problem(model)
problem.set_contact_model("MohrCoulomb", phi=35, c=0.0)
problem.set_joint_model(kn=1e9, kt=5e8)

bc1 = problem.add_boundary_condition("Gravity")
bc2 = problem.add_boundary_condition("Displacement")
bc3 = problem.add_boundary_condition("Surface Load")
bc4 = problem.add_boundary_condition("Point Load")

problem.add_displacement(block_index=0, displacement=[0.5, 0, 0], boundary_condition=bc2)

for b_idx in range(3, 6):
    problem.add_surface_load(block_index=b_idx, load=(0, 0, -10000), face_index=4, boundary_condition=bc3)

problem.add_point_load_at_centroid(block_index=10, force=[0, 0, -100000], boundary_condition=bc4)

# problem.set_solve_order([0])
# oder
# problem.set_solve_order(["Gravity", "Displacement", "Surface Load", "Point Load"])

PATH = pathlib.Path(__file__).parent / "dem_arch.json"
compas.json_dump(data=problem, fp=PATH)

# problem.inspect_model(model)

bla: Solver = Solver.BLA(n_steps=1, associative=False)
cra: Solver = Solver.CRA()
lmgc90: Solver = Solver.LMGC90(duration=10.0, dt=0.001, verbose=100)

problem.set_solver(cra)

result_cra = problem.solve()

problem.set_solver(lmgc90)

result_lmgc90 = problem.solve()

# Dump results
compas.json_dump(data=result_cra, fp=pathlib.Path(__file__).parent / "dem_arch_result.json")

# Viewer
viewer = DEMViewer(model)
# viewer.setup()
viewer.add_solution(result_cra, name="CRA", scale=0.5)
viewer.add_solution(result_lmgc90, name="LMGC90", scale=0.5)
viewer.show()
