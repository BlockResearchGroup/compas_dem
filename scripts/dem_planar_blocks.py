#! python3
# venv: brg-csd
# r: compas_model, Tessagon, compas_cgal==0.9.1, compas_libigl==0.7.4

import pathlib
import compas
from compas.datastructures import Mesh
from compas.geometry import Frame
from compas.geometry import Point
from compas.geometry import Vector
from compas.geometry import Transformation
from compas.geometry import Translation
from compas.scene import MeshObject
from compas.scene import Scene
from compas_libigl.mapping import map_mesh
from compas_cgal.meshing import trimesh_dual
from compas_libigl.parametrisation import trimesh_lsc_mapping
from compas_viewer import Viewer
from compas_dem.models import BlockModel
from compas_dem.modifiers.boolean_difference_modifier import BooleanDifferenceModifier
from compas_dem.modifiers.boolean_union_modifier import BooleanUnionModifier
from compas_dem.elements.interface import Interface
from compas_dem.fabrication.label import Label
from compas.tolerance import TOL

TOL.lineardeflection = 100
is_brep = False
tmin = 0.3
tmax = 0.4
compute_interactions = False

# =============================================================================
# RhinoVault mesh
# =============================================================================

session = compas.json_load(pathlib.Path(__file__).parent.parent / "data" / "rv_pattern.json")
scene: Scene = session["scene"]
sceneobj: MeshObject = scene.find_by_name("ThrustDiagram")  # type: ignore
mesh: Mesh = sceneobj.mesh.copy()

for face in list(mesh.faces_where(_is_loaded=False)):
    mesh.delete_face(face)

# =============================================================================
# Remesh and Flatten
# =============================================================================

V, F, DV, DF = trimesh_dual(mesh.to_vertices_and_faces(True),1.0,10,0.9,1.0 )
mesh = Mesh.from_vertices_and_faces(V, F)
pattern = Mesh.from_vertices_and_faces(DV, DF)
pattern.unify_cycles()

mv = []
mn = []
for vertex in pattern.vertices():
    mv.append(Vector(*pattern.vertex_point(vertex)))
    mn.append(Vector(*pattern.vertex_normal(vertex)))

# ==============================================================================
# Least-squares conformal map - to see where the pattern is mapped.
# ==============================================================================

uv = trimesh_lsc_mapping((V, F))
mesh_lscm = mesh.copy()
for i in range(mesh.number_of_vertices()):
    mesh_lscm.vertex_attributes(i, "xyz", [uv[i][0], uv[i][1], 0])


# ==============================================================================
# Select Pattern and Map
# ==============================================================================

# Rhino
# import Rhino
# import compas_rhino
# guids = compas_rhino.objects.select_objects()
# polygons = []

# for guid in guids:
#     obj = compas_rhino.objects.find_object(guid)
#     if isinstance(obj, Rhino.DocObjects.CurveObject):
#         polyline = compas_rhino.conversions.curve_to_compas_polyline(obj.Geometry)
#         polygon = Polygon(polyline.points[:-1])
#         polygons.append(polygon)

# Session
polygons = compas.json_load(pathlib.Path(__file__).parent.parent / "data" / "2d_pattern_non_parallel.json")
pattern = Mesh.from_polygons(polygons)
mv, mf, mn, mb, mg = map_mesh((V, F), pattern.to_vertices_and_faces(), clip_boundaries=False, fixed_vertices=[], tolerance=1e-3)
pattern = Mesh.from_vertices_and_faces(mv, mf)
pattern.unify_cycles()

# ===========================================================================
# Thickness
# =============================================================================

pattern.update_default_vertex_attributes(thickness=0)

zvalues: list[float] = pattern.vertices_attribute(name="z")  # type: ignore
zmin = min(zvalues)
zmax = max(zvalues)

for vertex in pattern.vertices():
    point = Point(*mv[vertex])
    normal = mn[vertex]
    z = (point.z - zmin) / (zmax - zmin)
    thickness = (1 - z) * (tmax - tmin) + tmin
    pattern.vertex_attribute(vertex, name="thickness", value=thickness)

# =============================================================================
# Model
# =============================================================================

model = BlockModel.from_mesh_with_planar_faces(
    mesh=pattern,
    offset=0,
    chamfer=0.1,
    thickness_scale_bottom=-0.5,
    thickness_scale_top=1,
    project_bottom=False,
    project_top=True,
    tolerance_parallel=0.5,
    vertex_normals=mn,
    is_brep=is_brep,
)

# =============================================================================
# Modifiers
# model.add_shear_keys(edges_frames, edges_lines, shape0, shape1)
# =============================================================================

if compute_interactions:
    elements = list(model.elements())
    modifier_pairs = []

    for edge in model.graph.edges():
        edge_attrs = model.graph.edge_attributes(edge)
        frame = edge_attrs["frame"]
        line = edge_attrs["line"]
        length = line.length
        interface0 = Interface.from_box(frame, length*0.6, 0.07, 0.1, is_brep=is_brep)
        interface1 = Interface.from_box(frame, length*0.65, 0.1, 0.1, is_brep=is_brep)
        modifier_pairs.append([interface0, interface1, elements[edge[0]], elements[edge[1]]])

    # Add elements and modifiers
    for interface0, interface1, elem0, elem1 in modifier_pairs:
        model.add_element(interface0)
        model.add_element(interface1)
        model.add_modifier(interface0, elem0, BooleanUnionModifier())
        model.add_modifier(interface1, elem1, BooleanDifferenceModifier())

# =============================================================================
# Labels
# =============================================================================

labels = []

for id, block in enumerate(model.elements()):
    if block.name == "Block":
        frame = model.graph.node_attribute(id, "frame")
        labels.append(Label.from_string(str(id), frame.flipped(), 0.1))


# =============================================================================
# Vizualize
# =============================================================================
viewer = Viewer()
# scene = Scene()

for polygon in polygons:
    viewer.scene.add(polygon, name="user_2d_pattern")
    # scene.add(polygon, name="user_2d_pattern")

#viewer.scene.add(mesh_lscm, name="Mesh", show_points=True)
# scene.add(mesh_lscm, name="Mesh", show_points=True)
viewer.scene.add(pattern, name="Pattern", show_points=True)

# 3D Blocks
o = Point(5,5,0)
for id, block in enumerate(model.elements()):
    if block.name != "Block":
        continue

    geometry = block.modelgeometry

    # Add meshes
    viewer.scene.add(geometry, show_lines=True)
    # scene.add(geometry, show_lines=True)

    # Add frame
    # viewer.scene.add(model.graph.node_attribute(id, "frame"))
    
    # Add each polyline from the label instead of the label object itself
    transformed_label = labels[id]
    for polyline in transformed_label.polylines:
        viewer.scene.add(polyline, color=(255, 0, 0))
        # scene.add(polyline, color=(255, 0, 0))

# 2D Blocks
x = 0
offset_x = 1
offset_y = -5
for id, block in enumerate(model.elements()):
    if block.name == "Block":

        geometry = block.modelgeometry.copy()
        frame = model.graph.node_attribute(id, "frame")

        # Orient mesh to xy frame and move it to the left
        O = Transformation.from_frame_to_frame(frame, Frame.worldXY())
        geometry.transform(O)
        box = geometry.aabb() if isinstance(geometry, Mesh) else geometry.aabb
        xmin, width = abs(box.xmin), box.xsize
        T = Translation.from_vector([x+xmin, offset_y, 0])
        geometry.transform(T)

        # Add geometry
        viewer.scene.add(geometry)
        # scene.add(geometry)

        # Add frame
        for polyline in labels[id].transformed(T*O).polylines:
            viewer.scene.add(polyline, color=(255, 0, 0))
            # scene.add(polyline, color=(255, 0, 0))

        # Update x position
        x += width+offset_x*0

viewer.show()
