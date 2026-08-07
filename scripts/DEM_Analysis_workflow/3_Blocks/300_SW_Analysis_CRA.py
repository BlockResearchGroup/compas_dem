import os

import compas
from compas_dem.problem import Solver

HERE = os.path.dirname(__file__)

model = compas.json_load(os.path.join(HERE, "DEM_model.json"))
problem = compas.json_load(os.path.join(HERE, "DEM_problem.json"))

cra = Solver.CRA(verbose=True)
problem.solver(cra)
result = model.solve(problem)

compas.json_dump(result, os.path.join(HERE, "DEM_results.json"))
