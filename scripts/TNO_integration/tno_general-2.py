# This script creates a SurfaceModel from an existing 3D FormDiagram = ThrustNetwoek
# It then applies the thickness and visualizes it using the DEMViewer.
# It will be usefull if we are working from a TNA analysis and constraining it to further analysis.

import json
from compas.datastructures import Mesh
from compas_dem.models import SurfaceModel
from compas_dem.viewer import DEMViewer
from compas_tno.diagrams import FormDiagram

def load_mesh_from_json(json_path):
    with open(json_path, 'r') as f:
        data = json.load(f)
    vertices = data['vertices']
    faces = data['faces']
    return Mesh.from_vertices_and_faces(vertices, faces)

form_json = "./data/crossvault_form.json"

formdiagram = FormDiagram.from_json(form_json)

model = SurfaceModel.from_formdiagram(formdiagram, thickness=0.5)

print("Surface Model:", model)

# =============================================================================
# Viz
# =============================================================================

viewer = DEMViewer(model)

viewer.setup2()
viewer.show()
