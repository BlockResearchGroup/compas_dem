"""Showcase of the compas_dem API: materials, model-side supports, boundary conditions,
every load application type, all five solvers, and overlaying their solutions.

Run top to bottom. The solvers each need their own backend installed
(compas_lmgc90, compas_cra, compas_pr3d, compas_bla); the ones that are commented
out below say which.
"""

import pathlib

import compas
from compas_dem.material import Stone
from compas_dem.models import Analysis
from compas_dem.models import BlockModel
from compas_dem.problem import Problem
from compas_dem.problem import Solver
from compas_dem.templates import ArchTemplate
from compas_dem.viewer import DEMViewer

HERE = pathlib.Path(__file__).parent

# =============================================================================
# Model
# =============================================================================

template: ArchTemplate = ArchTemplate(rise=4.393, span=21.213, thickness=0.5, depth=3.0, n=40)
model: BlockModel = BlockModel.from_template(template)

# Contacts are the interfaces the solvers work on; tolerance is the gap below which
# two faces are considered touching, minimum_area discards slivers.
model.compute_contacts(tolerance=0.001, minimum_area=0.01)

CROWN = 20  # blocks run 0..39 along the arch, so this is roughly the crown

# =============================================================================
# Material
# =============================================================================
# Stone.from_predefined_material(name) loads stiffness, Poisson and a default density
# from the built-in catalogue ("LimeStone", "Concrete C20/25"; matched case-insensitively).
# Stone(density=..., fck=..., Ecm=...) builds one from scratch instead.

limestone: Stone = Stone.from_predefined_material("LimeStone")
limestone.density = 2000  # kg/m3 — override the catalogue default

model.add_material(limestone)
# Assign to *every* element, supports included: body forces are mass-scaled, so an
# element without a density raises when the loads are resolved.
model.assign_material(limestone, elements=list(model.elements()))

# =============================================================================
# Supports — supports belong to the model, not to the problem
# =============================================================================
# Every solver reads block.is_support, so the same supports apply to every problem
# defined over this model. Use problem.inspect_model(model) to look up indices.

model.add_supports([0, 39])  # the two springing blocks

# add_support / remove_support / clear_supports flag them one at a time:
model.add_support(1)
model.remove_support(1)

print(f"supports: {[block.graphnode for block in model.supports()]}")
print(f"free blocks: {len(list(model.blocks()))} of {len(list(model.elements()))}")

# =============================================================================
# Problem — contact and joint behaviour
# =============================================================================

problem = Problem(model)

# set_contact_model: string-keyed contact law. "MohrCoulomb" takes either phi
# (friction angle, degrees) or mu (tan phi), plus c (cohesion) and t_c (tension cutoff).
problem.set_contact_model("MohrCoulomb", phi=30, c=0)

# set_joint_model: linear normal/tangential interface stiffness [N/m].
problem.set_joint_model(kn=10e10, kt=10e7)

# =============================================================================
# Boundary conditions — a named group of loads that act together
# =============================================================================
# Register one per load case; every add_* call below is directed at one explicitly.
# At solve time the active boundary conditions are summed into one load case.

live = problem.add_boundary_condition("Live")
fill = problem.add_boundary_condition("Fill")
seismic = problem.add_boundary_condition("Seismic")
settlement = problem.add_boundary_condition("Settlement")

# =============================================================================
# Loads — the four ways to place a point load
# =============================================================================
# Each names *where* the force acts; the equivalent moment about the block centroid
# is worked out from that point when the problem is resolved.

# ...at the block centroid, so no induced moment:
problem.add_point_load_at_centroid(block_index=CROWN, force=[0, 0, -151500], boundary_condition=live)

# ...at one vertex of the block mesh (eccentric, so it induces a moment):
problem.add_point_load_at_vertex(block_index=12, vertex_index=0, force=[0, 0, -25000], boundary_condition=live)

# ...at the centre of one face:
problem.add_point_load_at_face(block_index=14, face_index=4, force=[0, 0, -25000], boundary_condition=live)

# ...at an arbitrary point in space, here 0.2 m above a block's centroid:
crown_point = model.graph.node_element(16).point
problem.add_point_load_at_point(
    block_index=16,
    point=[crown_point.x, crown_point.y, crown_point.z + 0.2],
    force=[0, 0, -25000],
    boundary_condition=live,
)

# A couple about the centroid, with no net force:
problem.add_moment(block_index=CROWN, moment=[0, 5000, 0], boundary_condition=live)

# =============================================================================
# Loads — pressure, body force, prescribed movement
# =============================================================================

# A traction [N/m2] over one face; multiplied by the face area when resolved.
for index in range(8, 14):
    problem.add_surface_load(block_index=index, face_index=4, load=[0, 0, -10000], boundary_condition=fill)

# An acceleration [m/s2] applied to every block, mass-scaled into a force. 0.3 g
# sideways is the usual way to assess lateral capacity. loading_type="instantaneous"
# applies it at t=0 and releases it at the end, instead of ramping up and holding.
problem.add_global_body_force(0.3 * 9.81, 0, 0, loading_type="instantaneous", boundary_condition=seismic)

# A prescribed movement. On a support block it overrides the fixity per component,
# which is how a settlement analysis is set up.
problem.add_displacement(block_index=0, displacement=[0.02, 0, 0], boundary_condition=settlement)
problem.add_rotation(block_index=0, rotation=[0, 0.001, 0], boundary_condition=settlement)

# =============================================================================
# Solve order
# =============================================================================
# Reordering never drops anything: whatever is left out keeps its relative order
# behind the boundary conditions named here.

problem.set_solve_order(["Live", "Fill"])
print(f"solve order: {[bc.name for bc in problem.boundary_conditions]}")

# Draw the model with its indices, loads and supports before committing to a solve.
# Note this halts the script when the viewer closes unless you pass kill=False.
# problem.inspect_model(model, show_blocks=True)

# =============================================================================
# Solvers — every backend is configured the same way, through Solver.<NAME>()
# =============================================================================

# Time-stepping dynamics. Give exactly two of duration / n_steps / dt; the third
# is derived. urf_threshold stops early once the unbalanced force ratio settles.
lmgc90 = Solver.LMGC90(duration=1, dt=0.001)

# Rigid block equilibrium, and its contact-relaxation refinement.
rbe = Solver.RBE(verbose=False)
cra = Solver.CRA(penalty=False, verbose=False)

# Limit analysis and piecewise rigid displacement. n_steps=1 runs the one-shot LP;
# n_steps>1 runs the incremental solve with open_tol as the contact opening tolerance.
bla = Solver.BLA(n_steps=1, associative=True, open_tol=1e-3, solver="CLARABEL")
prd = Solver.PRD(n_steps=1, open_tol=1e-3, solver="CLARABEL")

# =============================================================================
# Solve — the same problem, once per solver
# =============================================================================
# set_solver then solve; the model comes from the problem, so solve() takes no arguments.
# Each call returns its own Results object, so they can be compared and overlaid.

solutions = {}

problem.set_solver(bla)
solutions["BLA"] = problem.solve()

problem.set_solver(rbe)
solutions["RBE"] = problem.solve()

problem.set_solver(lmgc90)
solutions["LMGC90"] = problem.solve()

# problem.set_solver(cra)  # needs compas_cra + IPOPT; slowest of the five
# solutions["CRA"] = problem.solve()

problem.set_solver(prd)  # needs compas_pr3d
solutions["PRD"] = problem.solve()

# =============================================================================
# Results
# =============================================================================
# Results are standalone: keyed by block index and contact edge, serializable on
# their own, and they never write back into the model.

for name, result in solutions.items():
    print(f"\n{name}: {result.metadata.get('solver_status', 'n/a')}  mu={result.metadata.get('mu')}")
    for edge in result.edges():
        print(f"  contact {edge}: |F| = {result.force_magnitude(edge):.1f} N")
        print(f"  resultant {edge}: {result.resultant_global(edge)}")
        break
    for block in model.supports():
        print(f"  support {block.graphnode} displacement: {result.displacement(block.graphnode)}")

compas.json_dump(data=solutions["BLA"], fp=HERE / "dem_new_features_result.json")

# =============================================================================
# Analysis — one model, its problems, serialized together
# =============================================================================
# A problem keeps only its model's id, never the geometry, so dumping problems on
# their own would leave them without a model. Analysis is the container that holds
# the model alongside them: the geometry is written once, and on load it is fed
# back into every problem so each one can solve straight away.

analysis = Analysis(name="arch study")
analysis.set_model(model)
analysis.add_problem(problem)

# A second problem over the same model — still only one copy of the geometry on disk.
settlement_only = Problem(model, name="settlement only")
settlement_only.set_contact_model("MohrCoulomb", phi=30, c=0)
support_movement = settlement_only.add_boundary_condition("Settlement")
settlement_only.add_displacement(block_index=0, displacement=[0.05, 0, 0], boundary_condition=support_movement)
settlement_only.set_solver(Solver.BLA(n_steps=50))
analysis.add_problem(settlement_only)

PATH = HERE / "dem_new_features_analysis.json"
compas.json_dump(data=analysis, fp=PATH)

# =============================================================================
# ...and load it back
# =============================================================================

reloaded: Analysis = compas.json_load(PATH)

print(f"\nanalysis '{reloaded.name}': {len(reloaded.problems)} problems")
print(f"  model: {len(list(reloaded.model.elements()))} blocks, {len(list(reloaded.model.supports()))} supports")

for reloaded_problem in reloaded.problems:
    # .model resolves because Analysis re-linked it on load — no load_model() needed.
    linked = reloaded_problem.model is reloaded.model
    print(f"  '{reloaded_problem.name}': {len(reloaded_problem.boundary_conditions)} BCs, model linked = {linked}")

# So the reloaded problem is immediately solvable:
# result = reloaded.problems[0].solve()

# =============================================================================
# Visualize — overlay every solution in one scene
# =============================================================================
# Each solution becomes its own toggleable group. The force scale is computed from
# the first one and reused, so arrow lengths stay comparable between solvers.

viewer = DEMViewer(model)
viewer.setup()

for name, result in solutions.items():
    result.displacement_scale = 1.0  # amplify the deformed shape without touching the stored values
    viewer.add_solution(result, name=name, scale=0.5)

viewer.show()
