import os

import compas
from compas_dem.viewer import DEMViewer

HERE = os.path.dirname(__file__)

model = compas.json_load(os.path.join(HERE, "DEM_model.json"))
results = compas.json_load(os.path.join(HERE, "DEM_results.json"))


viewer = DEMViewer(model)
viewer.add_solution(results, scale=0.5)
viewer.show()
