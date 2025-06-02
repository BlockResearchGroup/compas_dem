from compas.colors import Color
from compas_viewer import Viewer

from compas_dem.models import BlockModel
from compas_dem.templates import BarrelVaultTemplate

# =============================================================================
# Template
# =============================================================================

template = BarrelVaultTemplate()

# =============================================================================
# Model and interactions
# =============================================================================

model = BlockModel.from_barrelvault(template)

model.compute_contacts(tolerance=0.001)

# =============================================================================
# Viz
# =============================================================================

viewer = Viewer()

for element in model.elements():
    viewer.scene.add(element.modelgeometry, show_faces=False)

for contact in model.contacts():
    viewer.scene.add(contact.polygon, facecolor=Color.green())

viewer.show()
