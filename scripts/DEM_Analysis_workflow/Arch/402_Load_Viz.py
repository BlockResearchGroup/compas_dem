import os

import compas
from compas_dem.models import Analysis
from compas_dem.viewer import DEMViewer

HERE = os.path.dirname(__file__)

analysis: Analysis = compas.json_load(os.path.join(HERE, "DEM_analysis.json"))
results = compas.json_load(os.path.join(HERE, "DEM_results_pointload.json"))


viewer = DEMViewer(analysis.model)
viewer.add_solution(results, scale=0.5)
viewer.show()
