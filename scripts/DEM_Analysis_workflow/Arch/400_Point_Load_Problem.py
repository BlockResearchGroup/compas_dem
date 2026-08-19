import os

import compas
from compas_dem.models import Analysis
from compas_dem.problem import Problem

HERE = os.path.dirname(__file__)
PATH = os.path.join(HERE, "DEM_analysis.json")

analysis: Analysis = compas.json_load(PATH)
model = analysis.model

# A second problem over the same model: the same contact behaviour as the
# self-weight case, plus a point load. One copy of the geometry on disk, and the
# self-weight problem is left untouched.

problem = Problem(model, name="Point load")
problem.set_contact_model("MohrCoulomb", mu=0.5)

point_load = problem.add_boundary_condition("Point load")
problem.add_point_load_at_centroid(block_index=14, force=[0, 0, -50000.0], boundary_condition=point_load)

analysis.problems = [p for p in analysis.problems if p.name != problem.name]
analysis.add_problem(problem)

compas.json_dump(analysis, PATH)

problem.inspect_model()
