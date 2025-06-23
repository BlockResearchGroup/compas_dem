import pathlib

import compas
from compas.colors import Color
from compas.datastructures import Mesh
from compas_viewer import Viewer

from compas_dem.models import BlockModel

# =============================================================================
# ThrustDiagram
# =============================================================================

filepath = pathlib.Path(__file__).parent.parent / "data" / "ThrustDiagram.json"

mesh: Mesh = compas.json_load(filepath)  # type: ignore

# =============================================================================
# Model and interactions
# =============================================================================

model = BlockModel.from_meshdual(mesh, tmin=0.03, tmax=0.3)

# model.compute_contacts(tolerance=0.001)

# =============================================================================
# Viz
# =============================================================================

viewer = Viewer()

for element in model.elements():
    viewer.scene.add(element.modelgeometry, show_faces=True)

for contact in model.contacts():
    viewer.scene.add(contact.polygon, facecolor=Color.green())

viewer.show()
