"""Showcase of compas_dem 0.5.0 features: predefined materials, contact/joint models, RBE solver."""

from compas_dem.material import Stone
from compas_dem.models import BlockModel
from compas_dem.problem import Problem
from compas_dem.problem import Solver
from compas_dem.templates import ArchTemplate
from compas_dem.viewer import DEMViewer

# =============================================================================
# Model
# =============================================================================

template: ArchTemplate = ArchTemplate(rise=4.393, span=21.213, thickness=0.5, depth=3.0, n=10)
model: BlockModel = BlockModel.from_template(template)
model.compute_contacts()

# =============================================================================
# Material — NEW: predefined material library
# =============================================================================
# Stone.from_predefined_material(name) loads stiffness, Poisson and a default
# density from the built-in catalogue (e.g. "LimeStone", "Generic"). Others can be added as needed.
# Density can be overridden after instantiation.

limestone: Stone = Stone.from_predefined_material("LimeStone")
limestone.density = 2000.0

print(f"Limestone properties: Ecm={limestone.Ecm}, poisson={limestone.poisson}, density={limestone.density}")

model.add_material(limestone)
model.assign_material(limestone, elements=list(model.blocks()))

# =============================================================================
# Problem — NEW: declarative contact / joint / support API
# =============================================================================

problem = Problem(model)

# add_contact_model: string-keyed contact law selection. "MohrCoulomb" expects
# phi (friction angle, degrees) and c (cohesion).
problem.add_contact_model(
    "MohrCoulomb",
    phi=40,
    c=0,
    t_c=2,
)

# add_joint_model: linear normal/tangential joint stiffness (used by 3DEC).
problem.add_joint_model(kn=10e10, kt=10e7)

# add_support: pin a block as fixed by its graph index (use problem.inspect_model()
# to print indices for reference).
problem.add_support(block_index=0)
problem.add_support(block_index=9)

# Alternatively, use add_supports_from_model() to automatically add supports from
# blocks marked as supports in the model.

# =============================================================================
# Solver
# =============================================================================

# Select solver and solve.
# Other solvers include LMGC90 and CRA for now. Others can be added with the provided API.
solver = Solver.RBE(verbose=True)
solution = problem.solve(solver)

# =============================================================================
# Visualize
# =============================================================================

viewer = DEMViewer(model)
viewer.add_solution(scale=0.5)
viewer.show()
