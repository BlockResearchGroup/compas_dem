from compas.colors import Color
from compas_viewer import Viewer

from compas_dem.models import BlockModel
from compas_dem.templates import ArchTemplate

# =============================================================================
# Template
# =============================================================================

template = ArchTemplate(rise=3, span=10, thickness=0.5, depth=0.5, n=200)

# =============================================================================
# Model and interactions
# =============================================================================

model = BlockModel.from_template(template)

model.compute_contacts(tolerance=0.001)

# =============================================================================
# Viz
# =============================================================================

viewer = Viewer()

for element in model.elements():
    viewer.scene.add(element.modelgeometry, show_faces=False)

for contact in model.contacts():
    viewer.scene.add(contact.polygon, facecolor=Color.cyan())

viewer.show()
