import os

import compas
from compas_dem.models import Analysis
from compas_dem.problem import Problem
from compas_dem.problem import Solver
from compas_dem.viewer import DEMViewer

HERE = os.path.dirname(__file__)

# The analysis re-links the model into every problem on load, so the problem can
# be solved straight away — no separate model to load and pass around.

analysis: Analysis = compas.json_load(os.path.join(HERE, "DEM_analysis.json"))
problem: Problem = next(p for p in analysis.problems if p.name == "Self-weight")

lmgc90 = Solver.LMGC90(n_steps=100, dt=0.001)
problem.set_solver(lmgc90)
result = problem.solve()

compas.json_dump(result, os.path.join(HERE, "DEM_results_selfweight.json"))

viewer = DEMViewer(analysis.model)
viewer.add_solution(result, scale=0.5)
viewer.show()
