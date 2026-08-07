# COMPAS DEM — Geometry Data Structures Guide

A reference for understanding how blocks are created, what data lives inside them, and how to parse and work with that data. Written for agents and developers who are new to COMPAS.

---

## The Big Picture

Everything in COMPAS DEM is built on one idea: **a block is a closed 3D mesh**. That mesh knows its vertices, faces, normals, and any custom attributes you attach. A collection of blocks with their contacts is a `BlockModel`. The geometry layer (`compas.datastructures.Mesh`) is completely separate from the structural model layer (`BlockModel`), which is why you can swap them independently.

```
Shape (Box / Polyhedron / custom Mesh)
        ↓
    Block  (wraps a Mesh, adds is_support flag)
        ↓
  BlockModel  (graph of Blocks + Contacts)
        ↓
  compute_contacts()
        ↓
  FrictionContact  (interface polygon + forces)
```

---

## 1. The Mesh — COMPAS's Core Geometry Container

`compas.datastructures.Mesh` is a half-edge data structure. Think of it as a dictionary of vertices and faces with built-in geometry helpers.

### What is stored

| Concept | What it is | How it's indexed |
|---------|-----------|-----------------|
| Vertex | A 3D point `(x, y, z)` | Integer ID |
| Face | An ordered list of vertex IDs | Integer ID |
| Edge | Pair of vertex IDs `(u, v)` | Derived, not stored explicitly |
| Attributes | Arbitrary key-value data | Per-vertex or per-face |

### Creating a Mesh

```python
from compas.datastructures import Mesh
from compas.geometry import Box

# From a Box shape
box = Box(xsize=1.0, ysize=1.0, zsize=0.5)
mesh = Mesh.from_shape(box)          # 8 vertices, 6 quad faces

# From explicit vertex/face lists
vertices = [[0,0,0], [1,0,0], [1,1,0], [0,1,0]]
faces    = [[0, 1, 2, 3]]
mesh = Mesh.from_vertices_and_faces(vertices, faces)

# From polygon list
from compas.geometry import Polygon
polygons = [Polygon([[0,0,0],[1,0,0],[1,1,0],[0,1,0]])]
mesh = Mesh.from_polygons(polygons)
```

### Reading vertex data

```python
for vid in mesh.vertices():
    pt  = mesh.vertex_point(vid)          # compas.geometry.Point
    n   = mesh.vertex_normal(vid)         # compas.geometry.Vector
    x   = mesh.vertex_attribute(vid, "x") # float
    all_attrs = mesh.vertex_attributes(vid)  # {"x":..., "y":..., "z":...}

# Bulk
V, F = mesh.to_vertices_and_faces()
# V → list of [x, y, z]     e.g. [[0,0,0], [1,0,0], ...]
# F → list of face indices   e.g. [[0,1,2,3], [4,5,6,7], ...]
```

### Reading face data

```python
for fid in mesh.faces():
    vids   = mesh.face_vertices(fid)   # [0, 1, 2, 3]
    normal = mesh.face_normal(fid)     # Vector
    area   = mesh.face_area(fid)       # float (m²)
    center = mesh.face_center(fid)     # Point (geometric center)

    # Get the actual points
    pts = mesh.vertices_points(vids)   # [Point, Point, ...]
```

### Mesh-level queries

```python
mesh.centroid()            # [x, y, z]  — average of all vertex positions
mesh.aabb()                # Box         — axis-aligned bounding box
mesh.obb()                 # Box         — oriented bounding box
mesh.number_of_vertices()  # int
mesh.number_of_faces()     # int
mesh.number_of_edges()     # int
```

### Custom attributes

You can attach arbitrary data to any vertex or face:

```python
# Set defaults first (good practice)
mesh.update_default_vertex_attributes(thickness=0.0, label="")
mesh.update_default_face_attributes(is_boundary=False)

# Write per-vertex / per-face
mesh.vertex_attribute(vid, "thickness", 0.25)
mesh.face_attribute(fid, "is_boundary", True)

# Read back
t = mesh.vertex_attribute(vid, "thickness")          # 0.25
all_thick = mesh.vertices_attribute("thickness")     # list for all vertices
```

---

## 2. The Block — A Mesh with Structural Meaning

**File:** [src/compas_dem/elements/block.py](../src/compas_dem/elements/block.py)

`Block` inherits from `compas_model.elements.Element`. It wraps a `Mesh` and adds:

- `is_support` — marks the block as a boundary condition
- `elementgeometry` — the mesh in local (element) coordinates
- `modelgeometry` — the mesh transformed into world/model coordinates
- `graphnode` — the integer index of this block inside the `BlockModel` graph

### Creating a Block

```python
from compas_dem.elements import Block
from compas.geometry import Box
from compas.datastructures import Mesh

# From a Box
block = Block.from_box(Box(xsize=1, ysize=1, zsize=0.5))

# From a Polyhedron
from compas.geometry import Polyhedron
block = Block.from_polyhedron(Polyhedron.from_platonicsolid(4))

# From any Mesh (makes a deep copy)
block = Block.from_mesh(some_mesh)

# Mark as support
block.is_support = True
```

### What's inside a Block

```python
block.modelgeometry        # Mesh in world coordinates  ← most useful
block.elementgeometry      # Mesh in local coordinates
block.is_support           # bool
block.graphnode            # int (index in BlockModel graph)
block.guid                 # str (UUID)
block.name                 # str
block.point                # Point — centroid in world coordinates
block.aabb                 # Box — world-space bounding box
block.obb                  # Box — oriented bounding box
block.transformation       # Transformation (4x4 matrix)
```

### Accessing block geometry

```python
mesh = block.modelgeometry

# Same Mesh API as above applies:
V, F = mesh.to_vertices_and_faces()
centroid = mesh.centroid()

for fid in mesh.faces():
    n = mesh.face_normal(fid)
    a = mesh.face_area(fid)
```

---

## 3. The BlockModel — Graph of Blocks

**File:** [src/compas_dem/models/blockmodel.py](../src/compas_dem/models/blockmodel.py)

`BlockModel` is the main container. It stores blocks in a graph where edges represent block pairs that are in contact.

### Creating a BlockModel

```python
from compas_dem.models import BlockModel

# From boxes
boxes = [Box(...), Box(...)]
model = BlockModel.from_boxes(boxes)

# From polyhedrons
model = BlockModel.from_polyhedrons([Polyhedron(...), ...])

# From a template (arch, vault, dome, etc.)
from compas_dem.templates import ArchTemplate
template = ArchTemplate(rise=4.4, span=21.2, thickness=0.5, depth=3.0, n=100)
model = BlockModel.from_template(template)

# From a BarrelVault template (meshes with is_support attribute)
from compas_dem.templates import BarrelVaultTemplate
template = BarrelVaultTemplate(span=6.0, length=6.0, thickness=0.25, rise=0.6, vou_span=9, vou_length=6)
model = BlockModel.from_barrelvault(template)

# Manually, one mesh at a time
model = BlockModel()
node_id = model.add_block_from_mesh(some_mesh)       # regular block
node_id = model.add_support_from_mesh(support_mesh)  # support block
```

### Iterating blocks

```python
# All elements (blocks + supports)
for block in model.elements():
    print(block.graphnode, block.is_support)

# Only regular blocks
for block in model.blocks():
    mesh = block.modelgeometry
    ...

# Only supports
for block in model.supports():
    ...

# Find supports by graph degree (degree-1 nodes are endpoints in an arch)
for node in model.graph.nodes_where(degree=1):
    model.graph.node_element(node).is_support = True
```

### The internal graph

```python
model.graph.nodes()                     # all block indices
model.graph.edges()                     # all contact pairs (u, v)
model.graph.node_element(node_id)       # Block at that index
model.graph.node_attribute(node, name)  # any stored attribute
model.graph.edge_attribute((u, v), name)  # e.g. "contacts"
```

---

## 4. Contacts — Where Blocks Touch

**File:** [src/compas_dem/interactions/contact.py](../src/compas_dem/interactions/contact.py)

### Computing contacts

```python
model.compute_contacts(
    tolerance=0.001,     # distance tolerance for overlap detection
    minimum_area=0.01,   # ignore contacts smaller than this (m²)
)
```

This detects face-to-face overlaps between every pair of blocks, computes the intersection polygon, and stores a `FrictionContact` object on each graph edge.

### What's inside a FrictionContact

```python
contact.points    # list[Point]   — polygon corner points
contact.polygon   # Polygon       — contact interface
contact.frame     # Frame         — local coordinate system at the interface
  # frame.point   → contact centroid
  # frame.xaxis   → tangential direction u
  # frame.yaxis   → tangential direction v
  # frame.zaxis   → contact normal (pointing block A → block B)

contact.forces    # list[dict]    — one dict per corner point (empty until solved)
  # Each dict: {"c_np": float,   # normal compression (positive = contact)
  #             "c_nn": float,   # normal tension
  #             "c_u":  float,   # tangential force in u direction
  #             "c_v":  float}   # tangential force in v direction

# Derived from forces (available after solving):
contact.normalforces       # list[Line]
contact.compressionforces  # list[Line]
contact.tensionforces      # list[Line]
contact.frictionforces     # list[Line]
contact.resultantforce     # list[Line]  (single element)
contact.resultantpoint     # Point
```

### Iterating contacts

```python
# Via model (all contacts)
for contact in model.contacts():
    print(contact.polygon, contact.frame)

# Via graph (knowing which blocks are in contact)
for u, v in model.graph.edges():
    contacts = model.graph.edge_attribute((u, v), name="contacts")
    for contact in contacts:
        normal = contact.frame.zaxis
        area   = contact.polygon.area
```

---

## 5. Full Workflow Example

```python
from compas.geometry import Box
from compas_dem.models import BlockModel
from compas_dem.material import Stone
from compas_dem.problem import Problem, Solver

# 1. Build geometry — three stacked blocks
b0 = Box(xsize=1, ysize=1, zsize=0.3)
b1 = Box(xsize=1, ysize=1, zsize=0.3)
b2 = Box(xsize=1, ysize=1, zsize=0.3)
# translate b1 and b2 upward (pseudo-code, use Transformation in practice)

model = BlockModel.from_boxes([b0, b1, b2])

# 2. Mark supports
list(model.elements())[0].is_support = True

# 3. Detect contacts
model.compute_contacts(tolerance=0.001)

# 4. Inspect raw geometry
for block in model.elements():
    mesh = block.modelgeometry
    V, F = mesh.to_vertices_and_faces()
    print(f"Block {block.graphnode}: {len(V)} vertices, {len(F)} faces")
    print(f"  centroid: {mesh.centroid()}")
    for fid in mesh.faces():
        print(f"  face {fid}: normal={mesh.face_normal(fid)}, area={mesh.face_area(fid):.4f}")

# 5. Inspect contacts
for u, v in model.graph.edges():
    contacts = model.graph.edge_attribute((u, v), name="contacts")
    for contact in contacts:
        print(f"  Contact {u}↔{v}: area={contact.polygon.area:.4f}")
        print(f"    normal: {contact.frame.zaxis}")

# 6. Material + solver
stone = Stone(density=2000)
model.add_material(stone)
model.assign_material(stone, elements=list(model.elements()))

problem = Problem(model)
problem.add_contact_model("MohrCoulomb", phi=25, c=0.0)
problem.add_supports_from_model()
problem.solve(Solver.PR3D())

# 7. Read forces
for contact in model.contacts():
    for f in contact.forces:
        print(f["c_np"], f["c_u"], f["c_v"])
```

---

## 6. Parsing / Extracting Data for External Use

### Dump all block geometry to plain Python dicts

```python
def dump_blocks(model):
    out = []
    for block in model.elements():
        mesh = block.modelgeometry
        V, F = mesh.to_vertices_and_faces()
        out.append({
            "id":         block.graphnode,
            "is_support": block.is_support,
            "centroid":   mesh.centroid(),     # [x, y, z]
            "vertices":   V,                   # [[x,y,z], ...]
            "faces":      F,                   # [[v0,v1,v2,...], ...]
            "n_vertices": mesh.number_of_vertices(),
            "n_faces":    mesh.number_of_faces(),
        })
    return out
```

### Dump all contacts to plain Python dicts

```python
def dump_contacts(model):
    out = []
    for u, v in model.graph.edges():
        contacts = model.graph.edge_attribute((u, v), name="contacts")
        for contact in contacts:
            out.append({
                "block_a":  u,
                "block_b":  v,
                "points":   [[p.x, p.y, p.z] for p in contact.points],
                "normal":   list(contact.frame.zaxis),   # [nx, ny, nz]
                "area":     contact.polygon.area,
                "forces":   contact.forces,              # list of dicts
            })
    return out
```

### JSON serialization (COMPAS built-in)

```python
import compas.json as cjson

# Serialize
cjson.dump(model, "model.json")

# Deserialize
model = cjson.load("model.json")  # returns a BlockModel
```

COMPAS's JSON round-trip preserves the full graph, all blocks, all contacts, and all force data.

---

## 7. Key Types at a Glance

| Type | Module | Role |
|------|--------|------|
| `Mesh` | `compas.datastructures` | 3D geometry with vertices + faces |
| `Block` | `compas_dem.elements` | Mesh wrapped as a structural element |
| `BlockModel` | `compas_dem.models` | Graph of Blocks + Contacts |
| `FrictionContact` | `compas_dem.interactions` | Surface contact interface + forces |
| `EdgeContact` | `compas_dem.interactions` | Edge-edge contact after displacement |
| `Frame` | `compas.geometry` | Origin + 3 axes (local coordinate system) |
| `Transformation` | `compas.geometry` | 4×4 rigid body transform |
| `Point`, `Vector` | `compas.geometry` | 3D position and direction |
| `Polygon` | `compas.geometry` | Planar polygon (contact interface) |
| `Box` | `compas.geometry` | Cuboid shape (input or bounding box) |
| `Stone` | `compas_dem.material` | Material with density |
| `Problem` | `compas_dem.problem` | Solver setup (loads, BCs, contact law) |

---

## 8. File Map

| What | Where |
|------|-------|
| Block class | [src/compas_dem/elements/block.py](../src/compas_dem/elements/block.py) |
| BlockModel class | [src/compas_dem/models/blockmodel.py](../src/compas_dem/models/blockmodel.py) |
| FrictionContact + EdgeContact | [src/compas_dem/interactions/contact.py](../src/compas_dem/interactions/contact.py) |
| ContactProperties / MohrCoulomb | [src/compas_dem/interactions/](../src/compas_dem/interactions/) |
| Templates (arch, vault, dome…) | [src/compas_dem/templates/](../src/compas_dem/templates/) |
| Problem + Solver | [src/compas_dem/problem/](../src/compas_dem/problem/) |
| Arch example | [scripts/DEM_Analysis_Examples/dem_arch.py](../scripts/DEM_Analysis_Examples/dem_arch.py) |
| Dome example | [scripts/DEM_Analysis_Examples/dem_dome.py](../scripts/DEM_Analysis_Examples/dem_dome.py) |
