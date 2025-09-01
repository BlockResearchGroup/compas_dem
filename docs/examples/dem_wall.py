import pathlib

from compas.datastructures import Mesh
from compas.files import OBJ

from compas_dem.elements import Block
from compas_dem.models import BlockModel
from compas_dem.viewer import DEMViewer

# =============================================================================
# Data
# =============================================================================

FILE = pathlib.Path(__file__).parent.parent.parent / "data" / "wall.obj"

obj = OBJ(FILE)
obj.read()

meshes = []
for name in obj.objects:  # type: ignore
    vertices, faces = obj.objects[name]  # type: ignore
    mesh: Mesh = Mesh.from_vertices_and_faces(vertices, faces)
    mesh.scale(2, 2, 2)
    mesh.name = name
    meshes.append(mesh)

# =============================================================================
# Model and interactions
# =============================================================================

model = BlockModel()
for mesh in meshes:
    element = Block.from_mesh(mesh)
    model.add_element(element)

model.compute_contacts(tolerance=0.001)

# =============================================================================
# Supports
# =============================================================================

for element in model.elements():
    centroid = element.modelgeometry.centroid()
    if centroid[2] < 0.5:
        element.is_support = True

# Get Supports and Blocks Elements
blocks = list(model.blocks())
supports = list(model.supports())


# =============================================================================
# Save model to json
# =============================================================================

model.to_json(pathlib.Path(__file__).parent.parent.parent / "data" / "dem_crossvault.json")

# =============================================================================
# Viz
# =============================================================================

viewer = DEMViewer(model)

viewer.setup()
viewer.show()
