from compas_dem.templates import ArchTemplate
from compas_dem.models import SurfaceModel
from compas_dem.viewer import DEMViewer

# =============================================================================
# Template
# =============================================================================

template = ArchTemplate(rise=3, span=10, thickness=0.5, depth=2.5, n=50)

# =============================================================================
# Model
# =============================================================================

model = SurfaceModel.from_template(template)

# =============================================================================
# Viz
# =============================================================================

viewer = DEMViewer(model)

viewer.setup2()
viewer.show()
