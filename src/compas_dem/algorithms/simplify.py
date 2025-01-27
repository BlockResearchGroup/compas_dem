# def merge_coplanar_contacts(contacts: list[Contact], tol: float = 1e-6) -> list[Contact]:
#     """Merge coplanar contacts.

#     Parameters
#     ----------
#     contacts : list[:class:`Contact`]
#         A collection of contacts.
#     tol : float, optional
#         The tolerance for coplanarity.

#     Returns
#     -------
#     list[:class:`Contact`]

#     """
#     polygons = []
#     for contact in contacts:
#         points = []
#         for a, b, c in window(contact.points + contact.points[:2], 3):
#             if not is_colinear(a, b, c):
#                 points.append(b)

#         polygons.append(Polygon(points))

#     temp = Mesh.from_polygons(polygons)
#     try:
#         temp.unify_cycles()
#     except Exception:
#         continue

#     reconstruct = False

#     while True:
#         if temp.number_of_faces() < 2:
#             break

#         has_merged = False

#         for face in temp.faces():
#             nbrs = temp.face_neighbors(face)
#             points = temp.face_coordinates(face)
#             vertices = temp.face_vertices(face)

#             for nbr in nbrs:
#                 for vertex in temp.face_vertices(nbr):
#                     if vertex not in vertices:
#                         points.append(temp.vertex_coordinates(vertex))

#                 if is_coplanar(points, tol=tol):
#                     temp.merge_faces([face, nbr])
#                     has_merged = True
#                     reconstruct = True
#                     break

#             if has_merged:
#                 break

#         if not has_merged:
#             break

#     if reconstruct:
#         interfaces = []
#         for face in temp.faces():
#             points = temp.face_coordinates(face)
#             area = temp.face_area(face)
#             frame = Frame.from_plane(Plane(temp.face_centroid(face), temp.face_normal(face)))
#             interface = Contact(
#                 points=points,
#                 frame=frame,
#                 size=area,
#                 mesh=Mesh.from_polygons([points]),
#             )
#             interfaces.append(interface)

#         model.graph.edge_attribute(edge, "interfaces", interfaces)
