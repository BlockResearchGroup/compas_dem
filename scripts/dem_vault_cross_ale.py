import pathlib

import compas
from compas.colors import Color
from compas.geometry import Scale
from compas_viewer import Viewer

from compas_dem.models import BlockModel

# =============================================================================
# Data
# =============================================================================

BLOCKS = pathlib.Path(__file__).parent.parent / "data" / "pavillionvault" / "blocks.json"
SUPPORTS = pathlib.Path(__file__).parent.parent / "data" / "pavillionvault" / "supports.json"

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

# model.compute_collisions() => better than compute_interactions (intention is more explicit)
model.compute_contacts(tolerance=5 * 1e-3, minimum_area=1e-3, k=15)  # option: use_existing_interactions=False

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
