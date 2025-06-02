import pathlib
import time

from compas.colors import Color
from compas.datastructures import Mesh
from compas.files import OBJ
from compas.geometry import Line
from compas_viewer import Viewer

from compas_dem.models import BlockModel

# =============================================================================
# Data
# =============================================================================

FILE = pathlib.Path(__file__).parent.parent.parent / "data" / "crossvault.obj"

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

t0 = time.time()

model.compute_contacts(tolerance=0.001)

print(time.time() - t0)

# =============================================================================
# Supports
# =============================================================================

for element in model.elements():
    if model.graph.degree(element.graphnode) == 1:
        element.is_support = True

# =============================================================================
# Viz
# =============================================================================

color_support = Color.red()
color_contact = Color.cyan()

viewer = Viewer()

viewer.scene.add(
    [element.modelgeometry for element in model.supports()],
    facecolor=color_support,
    linecolor=color_support.contrast,
    name="Supports",
    opacity=0.5,
)

viewer.scene.add(
    [element.modelgeometry for element in model.blocks()],
    show_faces=True,
    name="Blocks",
    opacity=0.5,
)

viewer.scene.add(
    [contact.polygon for contact in model.contacts()],
    facecolor=color_contact,
    linecolor=color_contact.contrast,
    show_lines=False,
    name="Contacts",
    opacity=1.0,
)

# interaction graph

node_point = {node: model.graph.node_element(node).point for node in model.graph.nodes()}  # type: ignore

points = list(node_point.values())
lines = [Line(node_point[u], node_point[v]) for u, v in model.graph.edges()]

viewer.scene.add(
    [
        (points, {"pointsize": 10, "name": "Graph Nodes"}),
        (lines, {"linewidth": 3, "name": "Graph Edges"}),
    ],
    name="Interaction Graph",
)

viewer.show()
