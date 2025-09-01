import pathlib

import compas
from compas.colors import Color
from compas_viewer import Viewer

from compas_dem.models import BlockModel
from compas_dem.templates import ArchTemplate

# Model
template = ArchTemplate(rise=5, span=10, thickness=0.5, depth=0.5, n=20)
model = BlockModel.from_template(template)
model.compute_contacts(tolerance=0.001)

# Load results
results = compas.json_load(pathlib.Path(__file__).parent.parent.parent / "data" / "dem_results.json")

# Store results in contacts
for idx, contact in enumerate(model.contacts()):
    contact.forces = {
        "resultant_compression_by_interface": results["resultant_compression_by_interface"][idx],
        "resultant_tension_by_interface": results["resultant_tension_by_interface"][idx],
        "nodal_normal_compression_by_interface": results["nodal_normal_compression_by_interface"][idx],
        "nodal_normal_tension_by_interface": results["nodal_normal_tension_by_interface"][idx],
        "nodal_tangential_by_interface": results["nodal_tangential_by_interface"][idx],
    }

# Visualization
viewer = Viewer()

# Add elements
for element in model.elements():
    viewer.scene.add(element.modelgeometry, show_faces=False)

# Add contacts and forces
force_types = [
    ("resultant_compression_by_interface", 3, Color(0, 0.3, 0)),
    ("resultant_tension_by_interface", 8, Color(0.8, 0, 0)),
    ("nodal_normal_compression_by_interface", 3, Color.from_hex("#00468b")),
    ("nodal_normal_tension_by_interface", 5, Color(1, 0, 0)),
    ("nodal_tangential_by_interface", 5, Color(1.0, 0.5, 0.0)),
]

for contact in model.contacts():
    viewer.scene.add(contact.polygon, facecolor=Color.cyan().lightened(50))

    for force_type, linewidth, color in force_types:
        group = viewer.scene.add_group(force_type)
        for line in contact.forces[force_type]:
            group.add(line, linewidth=linewidth, linecolor=color)

viewer.show()
