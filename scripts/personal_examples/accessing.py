import pathlib

import compas
from compas_dem.models import BlockModel
from compas_dem.problem import BoundaryCondition
from compas_dem.problem import Problem

FILE = pathlib.Path(__file__).parent / "dem_arch.json"
problem: Problem = compas.json_load(FILE)
model: BlockModel = compas.json_load(pathlib.Path(__file__).parent / "dem_arch_model.json")

boundary_conditions = problem.boundary_conditions
boundary_condition_gravity: BoundaryCondition = boundary_conditions[0]
boundary_condition_displacement: BoundaryCondition = boundary_conditions[1]
boundary_condition_surface_load: BoundaryCondition = boundary_conditions[2]
boundary_condition_point_load: BoundaryCondition = boundary_conditions[3]

print("----------------------------------------------------------------")
print("\n")

print(f"Problem: {problem.guid} – Model: {model.guid} – {len(problem.boundary_conditions)} Boundary Conditions")
print("\n")
print("----------------------------------------------------------------")
print("\n")

print("Boundary Conditions:")
print(f"Boundary Condition 1: {boundary_conditions[0].name}")
print(f"Boundary Condition 2: {boundary_conditions[1].name}")
print(f"Boundary Condition 3: {boundary_conditions[2].name}")
print(f"Boundary Condition 4: {boundary_conditions[3].name}")

print("\n")
print("----------------------------------------------------------------")
print("\n")


print(f"Boundary Condition 1 Gravity: {boundary_condition_gravity.g}")
print(f"Boundary Condition 2 Displacements: {boundary_condition_displacement.displacements}")
print(f"Boundary Condition 3 Surface Loads: {boundary_condition_surface_load.surface_loads}")
print(f"Boundary Condition 4 Point Loads: {boundary_condition_point_load.point_loads}")

print("\n")
print("----------------------------------------------------------------")
print("\n")


contact_properties = problem.contact_properties
print("Contact Properties:")
print(f"Contact Model with Phi: {contact_properties.contact_model.phi}")
print(f"Contact Model with C: {contact_properties.contact_model.c}")
print(f"Joint Model: Kn = {contact_properties.joint_model.kn}, Kt = {contact_properties.joint_model.kt}")


from compas_dem.analysis.resolve import resolve_centroidal_displacements
from compas_dem.analysis.resolve import resolve_centroidal_loads


print("\n")
print("----------------------------------------------------------------")
print("\n")

print("Supports set in the problem")
print(f"Supports: {problem.supports}")

print("\n")
print("----------------------------------------------------------------")
print("\n")

print("Centroidal Loads for Boundary Condition 3 (Surface Loads):")
print(resolve_centroidal_loads(problem, model, boundary_condition=boundary_condition_surface_load))

# Returns a dictionary of centroidal loads for each block in the model, based on the specified boundary condition.


print("Centroidal Loads for Boundary Condition 2 (Settlement):")
print(resolve_centroidal_displacements(problem, boundary_condition=boundary_condition_displacement))

# Returns a dictionary of centroidal displacements for each block in the model, based on the specified boundary condition.
