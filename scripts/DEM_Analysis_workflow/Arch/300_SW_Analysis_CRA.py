import os

import compas
from compas_dem.models import Analysis
from compas_dem.problem import Problem
from compas_dem.problem import Solver

HERE = os.path.dirname(__file__)

analysis: Analysis = compas.json_load(os.path.join(HERE, "DEM_analysis.json"))
problem: Problem = next(p for p in analysis.problems if p.name == "Self-weight")

cra = Solver.CRA(verbose=True)
problem.set_solver(cra)
result = problem.solve()

compas.json_dump(result, os.path.join(HERE, "DEM_results_selfweight_cra.json"))
