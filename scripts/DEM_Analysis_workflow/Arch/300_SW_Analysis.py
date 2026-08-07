import os

import compas
from compas_dem.models import BlockModel
from compas_dem.problem import Problem
from compas_dem.problem import Solver
from compas_dem.viewer import DEMViewer

HERE = os.path.dirname(__file__)

model: BlockModel = compas.json_load(os.path.join(HERE, "DEM_model.json"))
problem: Problem = compas.json_load(os.path.join(HERE, "DEM_problem.json"))

# lmgc90 = Solver.LMGC90(duration=1.0, n_steps=100, urf_threshold=0.001)
# problem.solve(lmgc90, model)

lmgc90 = Solver.LMGC90(n_steps=100, dt=0.001)
problem.solver(lmgc90)
result = model.solve(problem)

compas.json_dump(result, os.path.join(HERE, "DEM_results.json"))

viewer = DEMViewer(model)
viewer.add_solution(result, scale=0.5)
viewer.show()
