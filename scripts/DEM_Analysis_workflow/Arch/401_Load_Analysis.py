import os

import compas
from compas_dem.analysis.resolve import resolve_centroidal_loads
from compas_dem.problem import Problem
from compas_dem.problem import Solver

HERE = os.path.dirname(__file__)

model = compas.json_load(os.path.join(HERE, "DEM_model.json"))
problem: Problem = compas.json_load(os.path.join(HERE, "DEM_problem_updated.json"))

print(f"Problem loaded with {resolve_centroidal_loads(model, problem.active_boundary_conditions)[14]}")

lmgc90 = Solver.LMGC90(duration=1.0, n_steps=100, urf_threshold=0.001)
problem.solver(lmgc90)
result = model.solve(problem)

compas.json_dump(result, os.path.join(HERE, "DEM_results.json"))
