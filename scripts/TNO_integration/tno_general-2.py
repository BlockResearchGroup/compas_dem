# This script creates a SurfaceModel from an existing 3D FormDiagram = ThrustNetwoek
# It then applies the thickness and visualizes it using the DEMViewer.
# It will be usefull if we are working from a TNA analysis and constraining it to further analysis.

import json
from compas.datastructures import Mesh
from compas_dem.models import SurfaceModel
from compas_dem.viewer import MasonryViewer
from compas_tno.analysis import Analysis
from compas_tno.diagrams import FormDiagram

# form_json = "./data/crossvault_form.json"
form_json = "./data/fan_form.json"

formdiagram = FormDiagram.from_json(form_json)
surfacemodel = SurfaceModel.from_formdiagram(formdiagram, thickness=0.75)

# =============================================================================
# Analysis
# =============================================================================

analysis = Analysis.create_minthrust_analysis(surfacemodel, printout=True)
analysis.apply_selfweight()
analysis.apply_envelope()
analysis.set_up_optimiser()
analysis.run()

# =============================================================================
# Viz
# =============================================================================

viewer = MasonryViewer(surfacemodel)
viewer.setup()
viewer.show()