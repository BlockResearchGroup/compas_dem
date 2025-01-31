import math
import random

from compas.geometry import Box
from compas.geometry import Rotation
from compas.geometry import Transformation
from compas.geometry import Translation

from compas_dem.analysis import cra_penalty_solve
from compas_dem.elements import BlockElement
from compas_dem.models import BlockModel
from compas_dem.viewers import BlockModelViewer

# =============================================================================
# Block Geometry
# =============================================================================

box = Box.from_corner_corner_height([0, 0, 0], [1, 1, 0], 1)

transformations: list[Transformation] = []
for i in range(10):
    T = Translation.from_vector(
        [
            random.choice([-0.1, +0.1]) * random.random(),
            random.choice([-0.1, +0.1]) * random.random(),
            i * box.zsize,
        ]
    )
    R = Rotation.from_axis_and_angle(box.frame.zaxis, angle=math.radians(random.choice([-5, +5])))
    X = T * R
    transformations.append(X)

# =============================================================================
# Block Model
# =============================================================================

model = BlockModel()
for X in transformations:
    block = BlockElement.from_box(box)
    block.transformation = X
    model.add_element(block)

# =============================================================================
# Contacts
# =============================================================================

model.compute_contacts()

# =============================================================================
# Supports
# =============================================================================

bottom: BlockElement = sorted(model.elements(), key=lambda e: e.point.z)[0]
bottom.is_support = True

# =============================================================================
# Equilibrium
# =============================================================================

cra_penalty_solve(model)

# =============================================================================
# Viz
# =============================================================================

viewer = BlockModelViewer(model)
viewer.show()
