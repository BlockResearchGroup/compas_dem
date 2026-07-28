import pathlib

import compas
from compas_dem.problem import LoadCase
from compas_dem.problem import Problem

FILE = pathlib.Path(__file__).parent / "dem_arch.json"
problem: Problem = compas.json_load(FILE)

load_cases = problem.loadcases
load_case_displacement: LoadCase = load_cases[1]
load_case_surface_load: LoadCase = load_cases[2]
load_case_point_load: LoadCase = load_cases[3]

print("Load Cases:")
print(f"Load Case 1: {load_cases[0].name}")
print(f"Load Case 2: {load_cases[1].name}")
print(f"Load Case 3: {load_cases[2].name}")
print(f"Load Case 4: {load_cases[3].name}")

print("Displacements:")
print(f"Load Case 2 Displacements: {load_case_displacement._displacements}")
print(f"Load Case 3 Surface Loads: {load_case_surface_load._surface_loads}")
print(f"Load Case 4 Point Loads: {load_case_point_load._point_loads}")


contact_properties = problem.contact_properties
print("Contact Properties:")
print(f"Contact Model with Phi: {contact_properties.contact_model.phi}")
print(f"Contact Model with C: {contact_properties.contact_model.c}")
print(f"Joint Model: Kn = {contact_properties.joint_model.kn}, Kt = {contact_properties.joint_model.kt}")
