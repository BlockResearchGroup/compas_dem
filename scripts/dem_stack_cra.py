"""Compute the equilibrium of an arch structure using the CRA method.

To run this script, install `compas_dem` and its dependencies using the preconfigured
"dem-dev" environment in the `compas_dem` repo.

    $ conda env create -f environment.yml
    $ conda activate dem-dev

"""

import math
import random

from compas.geometry import Box

from compas_dem.analysis.cra import cra_penalty_solve
from compas_dem.models import BlockModel
from compas_dem.viewer import DEMViewer

# =============================================================================
# Block Geometry
# =============================================================================

box = Box.from_corner_corner_height([0, 0, 0], [1, 1, 0], 1)

blocks: list[Box] = []
for i in range(10):
    block: Box = box.copy()
    block.translate(
        [
            random.choice([-0.1, +0.1]) * random.random(),
            random.choice([-0.1, +0.1]) * random.random(),
            i * box.zsize,
        ]
    )
    block.rotate(math.radians(random.choice([-5, +5])), box.frame.zaxis, box.frame.point)
    blocks.append(block)

# =============================================================================
# Model and interactions
# =============================================================================

model = BlockModel.from_boxes(blocks)

model.compute_contacts()

# =============================================================================
# Supports
# =============================================================================

bottom = sorted(model.elements(), key=lambda e: e.point.z)[0]
bottom.is_support = True

# =============================================================================
# Equilibrium
# =============================================================================

cra_penalty_solve(model)

for contact in model.contacts():
    print(contact.forces)

# =============================================================================
# Viz
# =============================================================================

viewer = DEMViewer(model)
viewer.setup()
viewer.show()
