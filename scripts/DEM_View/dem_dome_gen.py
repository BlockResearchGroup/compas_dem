import pathlib

import compas
from compas.datastructures import Mesh
from compas.geometry import SphericalSurface
from compas_dem.elements import Block
from compas_dem.models import BlockModel
from compas_dem.viewer import DEMViewer

# =============================================================================
# Geometry
# =============================================================================

surface = SphericalSurface(radius=5)
patch = surface.to_polyhedron(nu=32, nv=12, du=[0, 1.0], dv=[0.1, 0.5])

blocks = []
for polygon in patch.polygons:
    bottom = polygon.points
    top = []
    for point in bottom:
        vector = point - surface.frame.point
        direction = vector.unitized()
        top.append(point + direction * 0.3)
    vertices = bottom + top
    faces = [[0, 3, 2, 1], [4, 5, 6, 7], [2, 3, 7, 6], [1, 2, 6, 5], [0, 1, 5, 4], [3, 0, 4, 7]]
    blocks.append(Mesh.from_vertices_and_faces(vertices, faces))

# Use individual blocks as bricks (mesh.join() has issues)
bricks = []
for i, block in enumerate(blocks):
    brick: Mesh = block.copy()
    brick.attributes["is_support"] = brick.centroid()[2] < 0.4
    bricks.append(brick)

# =============================================================================
# Model and interactions
# =============================================================================

model = BlockModel()

for brick in bricks:
    element = Block.from_mesh(brick)
    element.is_support = brick.attributes["is_support"]
    model.add_element(element)

# =============================================================================

model.compute_contacts(tolerance=0.001)

# =============================================================================
# Export
# =============================================================================

compas.json_dump(model, pathlib.Path(__file__).parent / "dome.json")

# =============================================================================
# Viz
# =============================================================================

viewer = DEMViewer(model)

viewer.setup()
viewer.show()
