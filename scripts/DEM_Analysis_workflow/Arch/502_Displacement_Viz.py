import os

import compas
from compas_dem.analysis.resolve import resolve_centroidal_displacements
from compas_dem.problem import Problem
from compas_dem.viewer import DEMViewer

HERE = os.path.dirname(__file__)

model = compas.json_load(os.path.join(HERE, "DEM_model.json"))
problem: Problem = compas.json_load(os.path.join(HERE, "DEM_results.json"))

print(f"Support Horizontal settlement is {resolve_centroidal_displacements(problem.active_boundary_conditions)[0]}")


viewer = DEMViewer(model)
viewer.add_solution(results, scale=0.5)
viewer.show()
