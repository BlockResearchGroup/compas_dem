import os
from pathlib import Path

from compas_dem.material.generic import GenericMaterial
from compas_dem.models import BlockModel
from compas_dem.problem import Problem
from compas_dem.problem import Solver
from compas_dem.templates import ArchTemplate
from compas_dem.viewer import DEMViewer

HERE = Path(__file__).parent
RUNS = HERE / "runs"
EXECUTABLE = os.getenv("COMPAS_3DEC_EXECUTABLE")
VERSION = os.getenv("COMPAS_3DEC_VERSION", "7.0")

arch = ArchTemplate(
    rise=0.5,
    span=5.0,
    thickness=0.3,
    depth=0.3,
    n=10,
)

model = BlockModel()
nodes = [model.add_block_from_mesh(mesh) for mesh in arch.blocks()]
model.add_supports([nodes[0], nodes[-1]])

material = GenericMaterial(Ecm=25e9, density=2500, poisson=0.2, name="Marble")
model.add_material(material)
model.assign_material(material, elements=list(model.elements()))

problem = Problem(model, name="3DEC arch gravity")
problem.add_boundary_condition("gravity").add_gravity()
problem.set_contact_model("MohrCoulomb", phi=35.0)
problem.set_joint_model(kn=1e9, kt=5e8)
problem.set_solver(
    Solver.ThreeDEC(
        version=VERSION,
        executable=EXECUTABLE,
        workspace=RUNS,
        gravity_steps=10,
        suppress_output=True,
        timeout=300,
    )
)

# problem.solve() runs 3DEC and converts its native output to compas_dem.Results.
dem_results = problem.solve()

viewer = DEMViewer(model)
viewer.add_solution(dem_results, name="3DEC gravity", scale=0.5)
viewer.show()
