import os

import compas
import compas.geometry as cg

from compas_dem.material import Stone
from compas_dem.models import BlockModel

# =============================================================================
# Block Geometry
# =============================================================================

block_w = 1.0
block_h = 1.0
gap = 0.1

total_w = 2 * block_w + gap

# Base Plate
Pl = cg.Box.from_corner_corner_height([0, 0, -0.1], [total_w, block_w, -0.1], 0.1)

base_left = cg.Box.from_corner_corner_height([0, 0, 0], [block_w, block_w, 0], block_h)
base_right = cg.Box.from_corner_corner_height([block_w + gap, 0, 0], [total_w, block_w, 0], block_h)
top_x = (total_w - block_w) / 2
top = cg.Box.from_corner_corner_height([top_x, 0, block_h], [top_x + block_w, block_w, block_h], block_h)

blocks: list[cg.Box] = [Pl, base_left, base_right, top]


model = BlockModel.from_boxes(blocks)

# =============================================================================
# Compute contacts and supports
# =============================================================================
model.compute_contacts()
for block in model.elements():
    if block.point.z < 0.1:
        block.is_support = True

# =============================================================================
# Add material and assign to blocks
# =============================================================================

limestone = Stone.from_predefined_material("LimeStone")
model.add_material(limestone)
limestone.density = 2000
model.assign_material(limestone, elements=list(model.elements()))

# =============================================================================
# Json Dump
# =============================================================================

HERE = os.path.dirname(__file__)
compas.json_dump(model, os.path.join(HERE, "DEM_model.json"))
