# This script creates a SurfaceModel from two meshes (intrados and extrados)
# and visualizes it using the DEMViewer.
# It will be usefull if we are working with a pointcloud and need to create the analysis

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

intrados_json = "./data/intrados_mesh.json"
extrados_json = "./data/extrados_mesh.json"

intrados_mesh = Mesh.from_json(intrados_json)
extrados_mesh = Mesh.from_json(extrados_json)

model = SurfaceModel.from_meshes(intrados_mesh, extrados_mesh)

# =============================================================================
# Diagram
# =============================================================================

xy_span = [[0.0, 10.0], [0.0, 10.0]]
form = FormDiagram.create_cross_form(xy_span=xy_span, discretisation=10)
model.formdiagram = form

# Users should set the formdiagram themselves

# =============================================================================
# Viz
# =============================================================================

viewer = DEMViewer(model)

viewer.setup2()
viewer.show()
