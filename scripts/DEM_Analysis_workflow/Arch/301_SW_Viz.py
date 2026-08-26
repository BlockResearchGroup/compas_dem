import os

import compas
from compas_dem.models import Analysis
from compas_dem.viewer import DEMViewer

HERE = os.path.dirname(__file__)

analysis: Analysis = compas.json_load(os.path.join(HERE, "DEM_analysis.json"))
results_lmgc90 = compas.json_load(os.path.join(HERE, "DEM_results_selfweight.json"))
results_cra = compas.json_load(os.path.join(HERE, "DEM_results_selfweight_cra.json"))

viewer = DEMViewer(analysis.model)
viewer.add_solution(results_lmgc90, scale=0.5)
viewer.add_solution(results_cra, scale=0.5)
viewer.show()
