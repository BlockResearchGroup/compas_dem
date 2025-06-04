import pathlib

from compas.colors import Color
from compas.datastructures import Mesh
from compas.files import OBJ
from compas.geometry import Line
from compas_viewer import Viewer

from compas_dem.models import BlockModel

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

color_support = Color.red()
color_contact = Color.cyan()

viewer = Viewer()

group = viewer.scene.add_group(name="Supports")
group.add_from_list(
    [element.modelgeometry for element in model.supports()],
    facecolor=color_support,  # type: ignore
    linecolor=color_support.contrast,
    opacity=0.5,  # type: ignore
)

group = viewer.scene.add_group(name="Blocks")
group.add_from_list(
    [element.modelgeometry for element in model.blocks()],
    show_faces=True,  # type: ignore
    opacity=0.5,  # type: ignore
)

group = viewer.scene.add_group(name="Contacts")
group.add_from_list(
    [contact.polygon for contact in model.contacts()],
    surfacecolor=color_contact,  # type: ignore
    linecolor=color_contact.contrast,
    show_lines=False,  # type: ignore
    opacity=1.0,  # type: ignore
)

# interaction graph

node_point = {node: model.graph.node_element(node).point for node in model.graph.nodes()}  # type: ignore
points = list(node_point.values())
lines = [Line(node_point[u], node_point[v]) for u, v in model.graph.edges()]

group = viewer.scene.add_group(name="Interaction Graph")
nodegroup = viewer.scene.add_group(name="Graph Nodes", parent=group)
edgegroup = viewer.scene.add_group(name="Graph Edges", parent=group)
nodegroup.add_from_list(points, pointsize=10)  # type: ignore
nodegroup.add_from_list(lines)  # type: ignore

viewer.show()
