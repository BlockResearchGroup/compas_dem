import pathlib

import compas
from compas.colors import Color
from compas.geometry import Line
from compas.geometry import Scale
from compas_viewer import Viewer

from compas_dem.models import BlockModel

# =============================================================================
# Data
# =============================================================================

BLOCKS = pathlib.Path(__file__).parent.parent.parent / "data" / "pavillionvault" / "blocks.json"
SUPPORTS = pathlib.Path(__file__).parent.parent.parent / "data" / "pavillionvault" / "supports.json"

blocks = compas.json_load(BLOCKS)
supports = compas.json_load(SUPPORTS)

# =============================================================================
# Model and interactions
# =============================================================================

model = BlockModel()

for mesh in blocks:
    for part in mesh:
        model.add_block_from_mesh(part)

for mesh in supports:
    for part in mesh:
        model.add_support_from_mesh(part)


model.transform(Scale.from_factors([20, 20, 20]))

model.compute_contacts(tolerance=0.01)

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
    opacity=0.8,
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
