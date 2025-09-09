"""Compute the equilibrium of an arch structure using the CRA method.

To run this script, install `compas_dem` and its dependencies using the preconfigured
"dem-dev" environment in the `compas_dem` repo.

    $ conda env create -f environment.yml
    $ conda activate dem-dev

To generate the input file, run the `dem_dome.py` script first.

"""

import pathlib

import compas

# from compas_dem.analysis.cra import cra_penalty_solve
from compas_dem.analysis.cra import rbe_solve
from compas_dem.elements import Block
from compas_dem.models import BlockModel
from compas_dem.viewer import DEMViewer

# =============================================================================
# Import
# =============================================================================

model: BlockModel = compas.json_load(pathlib.Path(__file__).parent / "dome.json")  # type: ignore

# =============================================================================
# Supports
# =============================================================================

bottom: list[Block] = sorted(model.elements(), key=lambda e: e.point.z)[:16]
for block in bottom:
    block.is_support = True

# =============================================================================
# Equilibrium
# =============================================================================

# cra_penalty_solve(model)
rbe_solve(model)

# =============================================================================
# Viz
# =============================================================================

viewer = DEMViewer(model)
viewer.setup()
viewer.show()
