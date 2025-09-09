from compas_dem.templates.crossvault import CrossVaultTemplate
from compas_dem.models import SurfaceModel
from compas_dem.viewer import MasonryViewer
from compas_tno.analysis import Analysis
from compas_tno.diagrams import FormDiagram

# =============================================================================
# Template
# =============================================================================

xy_span = [[0.0, 10.0], [0.0, 10.0]]
thk = 0.50
min_lb = 0.0
n = 50

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

# Access as properties
print(f"Volume: {model.volume}")
print(f"Total Selfweight: {model.total_selfweight}")

# =============================================================================
# Diagram
# =============================================================================

form = FormDiagram.create_cross_form(
        # xy_span=[[0.1, 9.9], [0.1, 9.9]],
        xy_span=xy_span,
        discretisation=10,
)
model.formdiagram = form

# model.apply_selfweight()

# for key in model.formdiagram.vertices():
#     print(model.formdiagram.vertex_attribute(key, "pz"))

# User should set the formdiagram themselves

# =============================================================================
# Diagram
# =============================================================================

analysis = Analysis.create_minthrust_analysis(model, printout=True)
analysis.apply_selfweight()
analysis.apply_envelope()
analysis.set_up_optimiser()
analysis.run()

# =============================================================================
# Viz
# =============================================================================

viewer = MasonryViewer(model)

viewer.setup()
viewer.show()
