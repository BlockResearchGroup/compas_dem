"""Compute the equilibrium of an arch structure using the CRA method.

To run this script, install `compas_dem` and its dependencies using the preconfigured
"dem-dev" environment in the `compas_dem` repo.

    $ conda env create -f environment.yml
    $ conda activate dem-dev

"""

import math
import random

from compas.geometry import Box
from compas_dem.models import BlockModel
from compas_dem.problem import Problem
from compas_dem.problem import Solver
from compas_dem.viewer import DEMViewer
from compas_model.materials import Concrete

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
# Material
# =============================================================================

conc: Concrete = Concrete.from_strength_class("C30")
model.add_material(conc)
model.assign_material(conc, elements=list(model.elements()))

# =============================================================================
# Problem
# =============================================================================

prob: Problem = Problem(model)
prob.add_contact_model("MohrCoulomb", mu=0.5, c=0.0)
prob.add_supports_from_model()

# =============================================================================
# Solver
# =============================================================================

cra: Solver = Solver.CRA()
prob.solve(cra)

# =============================================================================
# Viz
# =============================================================================

viewer = DEMViewer(model)
viewer.add_solution()
viewer.show()
