from compas.datastructures import Mesh
from compas_dem.models import SurfaceModel
from compas_dem.viewer import MasonryViewer
from compas_tno.analysis import Analysis
from compas_tno.diagrams import FormDiagram

intrados_json = "./data/intrados_mesh.json"
extrados_json = "./data/extrados_mesh.json"

intrados_mesh = Mesh.from_json(intrados_json)
extrados_mesh = Mesh.from_json(extrados_json)

model = SurfaceModel.from_meshes(intrados_mesh, extrados_mesh)

# =============================================================================
# Diagram
# =============================================================================

xy_span = [[0.0, 10.0], [0.0, 10.0]]
form = FormDiagram.create_cross_form(xy_span=xy_span, discretisation=10)
model.formdiagram = form

print(model.thickness)

model.apply_selfweight()

# Users should set the formdiagram themselves

# =============================================================================
# Analysis
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
