from compas_dem.templates.crossvault import CrossVaultTemplate
from compas_dem.models import SurfaceModel
from compas_dem.viewer import DEMViewer
from compas_tno.analysis import Analysis
from compas_tno.diagrams import FormDiagram

# =============================================================================
# Template
# =============================================================================

xy_span = [[0.0, 10.0], [0.0, 10.0]]
thk = 0.50
min_lb = 0.0
n = 20


template = CrossVaultTemplate(
        xy_span=xy_span,
        thk=thk,
        min_lb=min_lb,
        n=n
)

# =============================================================================
# Model
# =============================================================================

model = SurfaceModel.from_template(template)

# =============================================================================
# Diagram
# =============================================================================

form = FormDiagram.create_cross_form(xy_span=xy_span, discretisation=n)
model.formdiagram = form

# User should set the formdiagram themselves

# =============================================================================
# Diagram
# =============================================================================

analysis = Analysis.create_minthrust_analysis(model, printout=True)

# In the future this will work on the TNO side, receiving only the SurfaceModel object with the formdiagram and the intra/extrados
# analysis.apply_selfweight()
# analysis.apply_envelope()
# analysis.set_up_optimiser()
# analysis.run()

# =============================================================================
# Viz
# =============================================================================

viewer = DEMViewer(model, form)

viewer.setup2()
viewer.show()
