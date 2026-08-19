import os

import compas
from compas_dem.analysis.resolve import resolve_centroidal_displacements
from compas_dem.models import Analysis
from compas_dem.problem import Problem
from compas_dem.viewer import DEMViewer

HERE = os.path.dirname(__file__)

analysis: Analysis = compas.json_load(os.path.join(HERE, "DEM_analysis.json"))
problem: Problem = next(p for p in analysis.problems if p.name == "Settlement")
results = compas.json_load(os.path.join(HERE, "DEM_results_settlement.json"))

print(f"Support Horizontal settlement is {resolve_centroidal_displacements(problem.boundary_conditions)[0]}")


viewer = DEMViewer(analysis.model)
viewer.add_solution(results, scale=0.5)
viewer.show()
