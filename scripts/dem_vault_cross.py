import pathlib

from compas.datastructures import Mesh
from compas.files import OBJ

from compas_dem.models import BlockModel
from compas_dem.viewer import DEMViewer

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
# Viz
# =============================================================================

viewer = DEMViewer(model)

viewer.setup()
viewer.show()
