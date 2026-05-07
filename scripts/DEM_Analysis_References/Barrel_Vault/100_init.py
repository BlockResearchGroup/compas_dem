import os

import compas
from compas_dem.material import Stone
from compas_dem.models import BlockModel
from compas_dem.templates import BarrelVaultTemplate

# =============================================================================
# Template
# =============================================================================

template = BarrelVaultTemplate(length=3, span=7, rise=0.1, vou_length=13)

# =============================================================================
# Block model
# =============================================================================

model = BlockModel.from_barrelvault(template)

# =============================================================================
# Compute contacts and supports
# =============================================================================
model.compute_contacts()
for node in model.graph.nodes_where(degree=1):
    model.graph.node_element(node).is_support = True  # type: ignore

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
