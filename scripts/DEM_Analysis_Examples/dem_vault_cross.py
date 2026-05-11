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

FILE = pathlib.Path(__file__).parent.parent / "data" / "crossvault.obj"

obj = OBJ(FILE)
obj.read()

meshes = []
for name in obj.objects:  # type: ignore
    vertices, faces = obj.objects[name]  # type: ignore
    mesh: Mesh = Mesh.from_vertices_and_faces(vertices, faces)
    mesh.scale(0.025, 0.025, 0.025)
    mesh.name = name
    meshes.append(mesh)

# =============================================================================
# Model and interactions
# =============================================================================

model = BlockModel.from_boxes(meshes)

model.compute_contacts(tolerance=0.001)


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
problem.add_supports_from_model()
problem.add_contact_model("MohrCoulomb", phi=40, c=0)


# rbe = Solver.RBE()

lmgc90 = Solver.LMGC90(duration=1.0, n_steps=1000)
solution = problem.solve(lmgc90)


# =============================================================================
# Viz
# =============================================================================

viewer = DEMViewer(model)

viewer.add_solution(scale=0.5)
viewer.show()
