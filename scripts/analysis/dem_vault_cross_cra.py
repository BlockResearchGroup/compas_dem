import pathlib
import time

from compas.colors import Color
from compas.datastructures import Mesh
from compas.files import OBJ
from compas_viewer import Viewer

from compas_dem.elements import BlockElement
from compas_dem.models import BlockModel

# =============================================================================
# Data
# =============================================================================

FILE = pathlib.Path(__file__).parent.parent / "data" / "crossvault.obj"

obj = OBJ(FILE)
obj.read()

meshes = []
for name in obj.objects:
    vertices, faces = obj.objects[name]
    mesh: Mesh = Mesh.from_vertices_and_faces(vertices, faces)
    mesh.scale(0.025, 0.025, 0.025)
    mesh.name = name
    meshes.append(mesh)

# =============================================================================
# Model and interactions
# =============================================================================

model = BlockModel.from_boxes(meshes)

t0 = time.time()

model.compute_contacts(tolerance=1e-3, minimum_area=1e-2, k=7)

print(time.time() - t0)

# =============================================================================
# Supports
# =============================================================================

element: BlockElement

for element in model.elements():
    if model.graph.degree(element.graphnode) == 1:
        element.is_support = True

# =============================================================================
# Viz
# =============================================================================

color_support = Color.red()
color_contact = Color.green()

viewer = Viewer()

viewer.scene.add(
    [element.modelgeometry for element in model.supports()],
    facecolor=color_support,
    linecolor=color_support.contrast,
    name="Supports",
)

viewer.scene.add(
    [element.modelgeometry for element in model.blocks()],
    show_faces=False,
    name="Blocks",
)

viewer.scene.add(
    [contact.polygon for contact in model.contacts()],
    facecolor=color_contact,
    linecolor=color_contact.contrast,
    show_lines=False,
    name="Contacts",
)

viewer.show()
