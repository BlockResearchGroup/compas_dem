from compas_dem.models import BlockModel
from compas_dem.problem import Problem
from compas_dem.problem import Solver
from compas_dem.templates import ArchTemplate
from compas_dem.viewer import DEMViewer
from compas_model.materials import Concrete

# =============================================================================
# Template
# =============================================================================

template = ArchTemplate(rise=3, span=10, thickness=0.5, depth=0.5, n=50)

# =============================================================================
# Model
# =============================================================================

model = BlockModel.from_template(template)

# =============================================================================
# Interactions
# =============================================================================

model.compute_contacts(tolerance=0.001)

# =============================================================================
# Supports
# =============================================================================

for node in model.graph.nodes_where(degree=1):
    model.graph.node_element(node).is_support = True  # type: ignore

# ============================================================================
# Material
# ============================================================================

conc: Concrete = Concrete.from_strength_class("C30")
model.add_material(conc)
model.assign_material(conc, elements=list(model.elements()))

# =============================================================================
# Problem
# =============================================================================

problem = Problem(model)
problem.add_contact_model("MohrCoulomb", mu=0.5, c=0.0)
problem.add_supports_from_model()

lmgc90: Solver = Solver.LMGC90(dt=0.01, n_steps=100)
problem.solve(lmgc90)

# =============================================================================
# Viz
# =============================================================================

viewer = DEMViewer(model)

viewer.add_solution()
viewer.show()
