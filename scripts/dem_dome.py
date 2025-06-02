import pathlib

import compas
from compas.colors import Color
from compas.datastructures import Mesh
from compas.geometry import SphericalSurface

# from compas.tolerance import TOL
from compas_viewer import Viewer

from compas_dem.elements import Block
from compas_dem.models import BlockModel

# TOL.precision = 6

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

columns = [blocks[i : i + 12] for i in range(0, len(blocks), 12)]
rows = list(zip(*columns))

bricks = []
for i in range(len(rows)):
    for j in range(0, len(rows[0]), 2):
        if i % 2 == 0:
            a: Mesh = rows[i][j]
            b: Mesh = rows[i][j + 1]
        else:
            a: Mesh = rows[i][j - 1]
            b: Mesh = rows[i][j]
        brick: Mesh = a.copy()
        brick.join(b, True)
        bricks.append(brick)

# =============================================================================
# Model and interactions
# =============================================================================

model = BlockModel()

for brick in bricks:
    element = Block.from_mesh(brick)
    model.add_element(element)

model.compute_contacts(tolerance=0.001)

# =============================================================================
# Export
# =============================================================================

compas.json_dump(model, pathlib.Path(__file__).parent / "dome.json")

# =============================================================================
# Viz
# =============================================================================

viewer = Viewer()

viewer.scene.add(
    [block.modelgeometry for block in model.blocks()],
    show_faces=False,
    name="Blocks",
)
viewer.scene.add(
    [contact.polygon for contact in model.contacts()],
    facecolor=Color.cyan(),
    name="Contacts",
)

viewer.show()
