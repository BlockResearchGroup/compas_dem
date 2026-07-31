import pathlib

from compas.datastructures import Mesh
from compas.files import OBJ
from compas_dem.models import BlockModel
from compas_dem.problem import Problem
from compas_dem.problem import Solver
from compas_dem.viewer import DEMViewer
from compas_model.materials import Concrete

# =============================================================================
# Data
# =============================================================================

FILE = pathlib.Path(__file__).parent.parent.parent / "data" / "leo_arch.obj"
print(f"Reading geometry from {FILE}...")
obj = OBJ(FILE)
obj.read()

meshes = []
for name in obj.objects:  # type: ignore
    vertices, faces = obj.objects[name]  # type: ignore
    mesh: Mesh = Mesh.from_vertices_and_faces(vertices, faces)
    # mesh.scale(0.025, 0.025, 0.025)
    mesh.scale(10, 10, 10)

    mesh.name = name
    meshes.append(mesh)

# =============================================================================
# Model and interactions
# =============================================================================

model = BlockModel.from_boxes(meshes)

model.compute_contacts(tolerance=0.01)


# =============================================================================
# Supports
# =============================================================================

for element in model.elements():
    if model.graph.degree(element.graphnode) == 1:
        element.is_support = True

# =============================================================================
# Material
# =============================================================================

conc: Concrete = Concrete.from_strength_class("C30")
model.add_material(conc)
model.assign_material(conc, elements=list(model.elements()))

# =============================================================================
# Problem
# ============================================================================

problem = Problem(model)

# problem.inspect_model()
problem.set_contact_model("MohrCoulomb", mu=0.55, c=0)


# rbe = Solver.RBE()

# lmgc90 = Solver.LMGC90(dt=0.001, n_steps=100)
lmgc90 = Solver.PRD()
problem.set_solver(lmgc90)
solution = problem.solve()


# =============================================================================
# Viz
# =============================================================================

viewer = DEMViewer(model)

viewer.add_solution(solution, scale=0.5)
viewer.show()
