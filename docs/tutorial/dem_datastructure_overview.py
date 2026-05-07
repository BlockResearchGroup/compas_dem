from compas.geometry import Transformation
from compas_dem.elements import Block
from compas_dem.models import BlockModel
from compas_dem.templates import ArchTemplate
from compas_dem.viewer import DEMViewer

# Data
template = ArchTemplate(rise=3, span=10, thickness=0.5, depth=0.5, n=50)

# Model
model = BlockModel()
for mesh in template.blocks():
    element = Block.from_mesh(mesh)
    model.add_element(element)

elements = list(model.elements())

# Supports
for element in model.elements():
    centroid = element.modelgeometry.centroid()
    if centroid[2] < 0.3:
        element.is_support = True

# Transformation
elements[25].transformation = Transformation.from_matrix(
    [
        [1, 0, 0, 0.0],
        [0, 1, 0, 0.0],
        [0, 0, 1, 1.0],
        [0, 0, 0, 1],
    ]
)

# Centroids
centroids = []
for el in elements:
    coords = el.modelgeometry.centroid()
    centroids.append(coords)

# Vertices
highlight = 40
vertices = []
mesh = elements[highlight].modelgeometry
vertices, faces = mesh.to_vertices_and_faces()

# Contacts
model.compute_contacts(tolerance=0.001)

contact_polygons = []
for contact in model.contacts():
    polygon = contact.polygon
    contact_polygons.append(polygon)

    for point in polygon:
        print(point)

# Interaction
edge = model.add_interaction(elements[0], elements[1])

# Visualization
viewer = DEMViewer(model)
viewer.setup()
viewer.show()
