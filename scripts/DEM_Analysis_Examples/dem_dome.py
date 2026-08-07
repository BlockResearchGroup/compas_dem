"""Compute the equilibrium of an arch structure using the CRA method.

To run this script, install `compas_dem` and its dependencies using the preconfigured
"dem-dev" environment in the `compas_dem` repo.

    $ conda env create -f environment.yml
    $ conda activate dem-dev

To generate the input file, run the `dem_dome.py` script first.

"""

import pathlib

import compas
from compas_dem.material import Stone
from compas_dem.models import BlockModel
from compas_dem.problem import Problem
from compas_dem.problem import Solver
from compas_dem.viewer import DEMViewer

# =============================================================================
# Import
# =============================================================================

model: BlockModel = compas.json_load(pathlib.Path(__file__).parent.parent.parent / "data" / "dome.json")  # type: ignore

# =============================================================================
# Material
# =============================================================================

stone: Stone = Stone.from_predefined_material("LimeStone")
stone.density = 2000  # Overwrite default density for limestone
model.add_material(stone)
model.assign_material(stone, elements=list(model.elements()))

# =============================================================================
# Problem setup and solve
# =============================================================================

problem = Problem(model)
problem.set_contact_model("MohrCoulomb", mu=0.5, c=0.0)
rbe_solver = Solver.LMGC90(duration=0.2, n_steps=100, urf_threshold=1e-3, theta=0.7)
problem.set_solver(rbe_solver)
solution = problem.solve()

# =============================================================================
# Viz
# =============================================================================

viewer = DEMViewer(model)
viewer.add_solution(solution)
viewer.show()
