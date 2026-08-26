import os

import compas
from compas_dem.material import Stone
from compas_dem.models import Analysis
from compas_dem.models import BlockModel
from compas_dem.templates import ArchTemplate
from compas_dem.viewer import DEMViewer

# =============================================================================
# Create a BlockModel from Template
# =============================================================================
template: ArchTemplate = ArchTemplate(rise=4.393, span=21.213, thickness=0.5, depth=3.0, n=30)
model: BlockModel = BlockModel.from_template(template)

# =============================================================================
# Compute contacts to populate the graph
# =============================================================================
model.compute_contacts()


# =============================================================================
# Add material and assign to blocks
# =============================================================================

elements = list(model.elements())

limestone = Stone.from_predefined_material("LimeStone")
model.add_material(limestone)
model.assign_material(limestone, elements=elements)

# =============================================================================
# Add supports
# =============================================================================
# Supports live on the model, so every problem defined over it shares them.

model.add_supports([0, 29])

# =============================================================================
# Save analysis
# =============================================================================
# The analysis holds the model and every problem defined over it. The geometry is
# written once here; the problems added by 200/400/500 are stored alongside it in
# the same file, so no script ever has to load a model and a problem separately.

HERE = os.path.dirname(__file__)

analysis = Analysis(model, name="Arch")
compas.json_dump(analysis, os.path.join(HERE, "DEM_analysis.json"))

# =============================================================================
# Visualise model
# =============================================================================

viewer = DEMViewer(model)
viewer.setup()
viewer.show()
