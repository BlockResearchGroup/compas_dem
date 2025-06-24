import math
import random

from compas.geometry import Box

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

next(model.blocks()).is_support = True

model.compute_contacts()

# =============================================================================
# Viz
# =============================================================================

viewer = DEMViewer(model)

viewer.setup()
viewer.show()
