import os

import compas
from compas_dem.problem import Problem

HERE = os.path.dirname(__file__)

model = compas.json_load(os.path.join(HERE, "DEM_model.json"))
problem: Problem = compas.json_load(os.path.join(HERE, "DEM_problem.json"))

problem.add_point_load(block_index=14, force=[0, 0, -50000.0])

compas.json_dump(problem, os.path.join(HERE, "DEM_problem_updated.json"))

problem.inspect_model(model)

# viewer = DEMViewer(model)
# viewer.add_solution(scale=10e-12)
# viewer.show()
