"""Showcase of compas_dem 0.5.0 features: predefined materials, contact/joint models, point loads, LMGC90 solver."""

from compas_dem.material import Stone
from compas_dem.models import BlockModel
from compas_dem.problem import Problem
from compas_dem.problem import Solver
from compas_dem.templates import ArchTemplate
from compas_dem.viewer import DEMViewer

# =============================================================================
# Model
# =============================================================================

template: ArchTemplate = ArchTemplate(rise=4.393, span=21.213, thickness=0.5, depth=3.0, n=100)
model: BlockModel = BlockModel.from_template(template)
model.compute_contacts()

# =============================================================================
# Material — NEW: predefined material library
# =============================================================================
# Stone.from_predefined_material(name) loads stiffness, Poisson and a default
# density from the built-in catalogue (e.g. "LimeStone", "SandStone", "Granite").

limestone: Stone = Stone.from_predefined_material("LimeStone")
model.add_material(limestone)
model.assign_material(limestone, elements=list(model.blocks()))

# =============================================================================
# Problem — NEW: declarative contact / joint / support / load API
# =============================================================================

problem = Problem(model)

# add_contact_model: string-keyed contact law. "MohrCoulomb" expects
# phi (friction angle, degrees) and c (cohesion).
problem.add_contact_model("MohrCoulomb", phi=30, c=0)

# add_joint_model: linear normal/tangential interface stiffness.
problem.add_joint_model(kn=10e10, kt=10e7)

# add_support: pin a block as fixed by its graph index (use problem.inspect_model()
# to print indices for reference).
problem.add_support(block_index=0)
problem.add_support(block_index=99)

# add_point_load: apply a force vector [Fx, Fy, Fz] (Newtons) to a block by index.
problem.add_point_load(block_index=70, force=[0, 0, -151500])

# =============================================================================
# Solve — NEW: LMGC90 solver factory
# =============================================================================

lmgc90 = Solver.LMGC90(dt=0.001, n_steps=1000)
solution = problem.solve(lmgc90)

# =============================================================================
# Visualize
# =============================================================================

viewer = DEMViewer(model)
viewer.add_solution(scale=0.5)
viewer.show()
