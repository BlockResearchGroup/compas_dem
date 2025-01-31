from typing import Optional

import numpy as np
import pythreejs as three
from compas.colors import Color
from compas.datastructures import Mesh
from compas.geometry import Polygon
from compas.geometry import earclip_polygon


def mesh_to_edgesbuffer(mesh: Mesh, color: Color) -> tuple[list[list[float]], list[Color]]:
    positions = []
    colors = []

    for u, v in mesh.edges():
        positions.append(mesh.vertex_coordinates(u))
        positions.append(mesh.vertex_coordinates(v))
        colors.append(color)
        colors.append(color)

    return positions, colors


def meshes_to_edgesbuffer(
    meshes: list[Mesh],
    color: Color,
    material: Optional[three.LineBasicMaterial] = None,
) -> three.LineSegments:
    positions = []
    colors = []

    for mesh in meshes:
        buffer = mesh_to_edgesbuffer(mesh, color)
        positions += buffer[0]
        colors += buffer[1]

    positions = np.array(positions, dtype=np.float32)
    colors = np.array(colors, dtype=np.float32)

    geometry = three.BufferGeometry(
        attributes={
            "position": three.BufferAttribute(positions, normalized=False),
            "color": three.BufferAttribute(colors, normalized=False, itemSize=3),
        }
    )

    if not material:
        material = three.LineBasicMaterial(vertexColors="VertexColors")

    return three.LineSegments(geometry, material)


def mesh_to_facesbuffer(mesh: Mesh, color: Color) -> tuple[list[list[float]], list[Color]]:
    positions = []
    colors = []

    for face in mesh.faces():
        vertices = mesh.face_vertices(face)

        if len(vertices) == 3:
            positions.append(mesh.vertex_coordinates(vertices[0]))
            positions.append(mesh.vertex_coordinates(vertices[1]))
            positions.append(mesh.vertex_coordinates(vertices[2]))
            colors.append(color)
            colors.append(color)
            colors.append(color)

        elif len(vertices) == 4:
            positions.append(mesh.vertex_coordinates(vertices[0]))
            positions.append(mesh.vertex_coordinates(vertices[1]))
            positions.append(mesh.vertex_coordinates(vertices[2]))
            colors.append(color)
            colors.append(color)
            colors.append(color)
            positions.append(mesh.vertex_coordinates(vertices[0]))
            positions.append(mesh.vertex_coordinates(vertices[2]))
            positions.append(mesh.vertex_coordinates(vertices[3]))
            colors.append(color)
            colors.append(color)
            colors.append(color)

        else:
            ears = earclip_polygon(Polygon([mesh.vertex_coordinates(v) for v in vertices]))
            for ear in ears:
                positions.append(mesh.vertex_coordinates(vertices[ear[0]]))
                positions.append(mesh.vertex_coordinates(vertices[ear[1]]))
                positions.append(mesh.vertex_coordinates(vertices[ear[2]]))
                colors.append(color)
                colors.append(color)
                colors.append(color)

    return positions, colors


def meshes_to_facesbuffer(
    meshes: list[Mesh],
    color: Color,
    material: Optional[three.MeshBasicMaterial] = None,
) -> three.Mesh:
    positions = []
    colors = []

    for mesh in meshes:
        buffer = mesh_to_facesbuffer(mesh, color)
        positions += buffer[0]
        colors += buffer[1]

    positions = np.array(positions, dtype=np.float32)
    colors = np.array(colors, dtype=np.float32)

    geometry = three.BufferGeometry(
        attributes={
            "position": three.BufferAttribute(positions, normalized=False),
            "color": three.BufferAttribute(colors, normalized=False, itemSize=3),
        }
    )

    if not material:
        material = three.MeshBasicMaterial(
            side="DoubleSide",
            vertexColors="VertexColors",
        )

    return three.Mesh(geometry, material)
