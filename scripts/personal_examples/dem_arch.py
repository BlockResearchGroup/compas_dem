import pathlib

import compas

from compas_dem.material import Stone
from compas_dem.models import BlockModel
from compas_dem.problem import BoundaryCondition
from compas_dem.problem import Problem
from compas_dem.problem import Solver
from compas_dem.templates import ArchTemplate
from compas_dem.viewer import DEMViewer

# =============================================================================
# Template
# =============================================================================

template = ArchTemplate(rise=4.393, span=21.213, thickness=0.5, depth=3.0, n=100)

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
# Problem
# =============================================================================
compas.json_dump(data=model, fp=pathlib.Path(__file__).parent / "dem_arch_model.json")
problem = Problem(model)
problem.add_contact_model("MohrCoulomb", phi=35, c=0.0)
problem.add_supports_from_model(model)
problem.add_joint_model(kn=1e9, kt=5e8)

bc1 = BoundaryCondition(name="Gravity")
bc2 = BoundaryCondition(name="Displacement")
bc3 = BoundaryCondition(name="Surface Load")
bc4 = BoundaryCondition(name="Point Load")

problem.add_boundary_condition(bc1)
problem.add_boundary_condition(bc2)
problem.add_boundary_condition(bc3)
problem.add_boundary_condition(bc4)

problem.add_displacement(block_index=0, displacement=[0.5, 0, 0], boundary_condition=bc2)

for b_idx in range(25, 36):
    problem.add_surface_load(block_index=b_idx, load=(0, 0, -10000), face_index=4, boundary_condition=bc3)

problem.add_point_load(block_index=80, force=[0, 0, -100000], boundary_condition=bc4)

PATH = pathlib.Path(__file__).parent / "dem_arch.json"
compas.json_dump(data=problem, fp=PATH)
# problem.inspect_model(model)
# solver: Solver = Solver.LMGC90(dt=0.001, duration=1)
solver: Solver = Solver.BLA(n_steps=1, associative=False)
cra: Solver = Solver.CRA(d_bnd=0.001, eps=0.0001)
lmgc90: Solver = Solver.LMGC90(dt=0.001, duration=1)
problem.solver(solver)
result = model.solve(problem)
compas.json_dump(data=result, fp=pathlib.Path(__file__).parent / "dem_arch_result.json")

# Viewer
viewer = DEMViewer(model)
# viewer.setup()
viewer.add_solution(result, scale=0.5)
viewer.show()
