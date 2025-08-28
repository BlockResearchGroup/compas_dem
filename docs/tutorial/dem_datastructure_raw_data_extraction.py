from compas_dem.templates import ArchTemplate
from compas_dem.models import BlockModel
import numpy as np
from typing import List, Tuple

# Model
template: ArchTemplate = ArchTemplate(rise=3, span=10, thickness=0.5, depth=0.5, n=50)
model: BlockModel = BlockModel.from_template(template)
elements: List = list(model.elements())
model.compute_contacts(tolerance=0.001)

# Meshes to Numpy Arrays
numpy_vertices: List[np.ndarray] = []
numpy_faces: List[np.ndarray] = []
for element in elements:
    V, F = element.modelgeometry.to_vertices_and_faces()
    numpy_vertices.append(np.asarray(V, dtype=np.float64))
    numpy_faces.append(np.asarray(F, dtype=np.int32))

# Centroids
centroids: List = []
for element in elements:
    centroids.append(element.modelgeometry.centroid())
numpy_centroids: np.ndarray = np.asarray(centroids, dtype=np.float64)

# Contact Polygons
numpy_contact_polygons: List[np.ndarray] = []
for contact in model.contacts():
    numpy_contact_polygons.append(np.asarray(contact.polygon, dtype=np.float64))

# Contact Indices
contact_indices: List[Tuple[int, int]] = []
for edge in model.graph.edges():
    contacts = model.graph.edge_attribute(edge, name="contacts")
    if contacts:
        contact_indices.append(edge)
numpy_contact_indices: np.ndarray = np.asarray(contact_indices, dtype=np.int32)
