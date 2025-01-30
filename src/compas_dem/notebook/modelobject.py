from typing import Optional

import numpy
import pythreejs as three
from compas.colors import Color
from compas.datastructures import Mesh
from compas.geometry import Polygon
from compas.geometry import earclip_polygon
from compas_notebook.scene import ThreeSceneObject

from compas_dem.models import BlockModel


def mesh_to_edgesbuffer(mesh: Mesh, color: Color):
    positions = []
    colors = []

    for u, v in mesh.edges():
        positions.append(mesh.vertex_coordinates(u))
        positions.append(mesh.vertex_coordinates(v))
        colors.append(color)
        colors.append(color)

    return positions, colors


def mesh_to_facesbuffer(mesh: Mesh, color: Color):
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


class ThreeBlockModelObject(ThreeSceneObject):
    """Scene object for drawing mesh."""

    def __init__(
        self,
        show_blocks: Optional[bool] = True,
        show_supports: Optional[bool] = True,
        show_contacts: Optional[bool] = True,
        show_blockfaces: Optional[bool] = False,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)

        self.show_blocks = show_blocks
        self.show_supports = show_supports
        self.show_contacts = show_contacts
        self.show_blockfaces = show_blockfaces

    # @property
    # def settings(self) -> dict:
    #     settings = super().settings
    #     return settings

    @property
    def model(self) -> BlockModel:
        return self.item

    @model.setter
    def model(self, model: BlockModel) -> None:
        self._item = model
        self._transformation = None

    def draw(self):
        """Draw the mesh associated with the scene object.

        Returns
        -------
        list[three.Mesh, three.LineSegments]
            List of pythreejs objects created.

        """
        self._guids = []

        if self.show_blocks:
            if self.show_blockfaces:
                self._guids.append(self.draw_blockfaces())
            self._guids.append(self.draw_blockedges())

        if self.show_supports:
            self._guids.append(self.draw_supportfaces())
            self._guids.append(self.draw_supportedges())

        if self.show_contacts:
            self._guids.append(self.draw_contactfaces())
            self._guids.append(self.draw_contactedges())

        return self.guids

    def draw_blockfaces(self):
        positions = []
        colors = []

        for block in self.model.blocks():
            buffer = mesh_to_facesbuffer(block.modelgeometry, Color(0.9, 0.9, 0.9))
            positions += buffer[0]
            colors += buffer[1]

        positions = numpy.array(positions, dtype=numpy.float32)
        colors = numpy.array(colors, dtype=numpy.float32)

        geometry = three.BufferGeometry(
            attributes={
                "position": three.BufferAttribute(positions, normalized=False),
                "color": three.BufferAttribute(colors, normalized=False, itemSize=3),
            }
        )
        material = three.MeshBasicMaterial(
            side="DoubleSide",
            vertexColors="VertexColors",
        )
        return three.Mesh(geometry, material)

    def draw_blockedges(self):
        positions = []
        colors = []

        for block in self.model.blocks():
            buffer = mesh_to_edgesbuffer(block.modelgeometry, Color(0.2, 0.2, 0.2))
            positions += buffer[0]
            colors += buffer[1]

        positions = numpy.array(positions, dtype=numpy.float32)
        colors = numpy.array(colors, dtype=numpy.float32)

        geometry = three.BufferGeometry(
            attributes={
                "position": three.BufferAttribute(positions, normalized=False),
                "color": three.BufferAttribute(colors, normalized=False, itemSize=3),
            }
        )
        material = three.LineBasicMaterial(vertexColors="VertexColors")
        return three.LineSegments(geometry, material)

    def draw_supportfaces(self):
        positions = []
        colors = []

        for block in self.model.supports():
            buffer = mesh_to_facesbuffer(block.modelgeometry, Color.red().lightened(50))
            positions += buffer[0]
            colors += buffer[1]

        positions = numpy.array(positions, dtype=numpy.float32)
        colors = numpy.array(colors, dtype=numpy.float32)

        geometry = three.BufferGeometry(
            attributes={
                "position": three.BufferAttribute(positions, normalized=False),
                "color": three.BufferAttribute(colors, normalized=False, itemSize=3),
            }
        )
        material = three.MeshBasicMaterial(
            side="DoubleSide",
            vertexColors="VertexColors",
        )
        return three.Mesh(geometry, material)

    def draw_supportedges(self):
        positions = []
        colors = []

        for block in self.model.supports():
            buffer = mesh_to_edgesbuffer(block.modelgeometry, Color.red())
            positions += buffer[0]
            colors += buffer[1]

        positions = numpy.array(positions, dtype=numpy.float32)
        colors = numpy.array(colors, dtype=numpy.float32)

        geometry = three.BufferGeometry(
            attributes={
                "position": three.BufferAttribute(positions, normalized=False),
                "color": three.BufferAttribute(colors, normalized=False, itemSize=3),
            }
        )
        material = three.LineBasicMaterial(vertexColors="VertexColors")
        return three.LineSegments(geometry, material)

    def draw_contactfaces(self):
        color = Color.cyan().lightened(75)

        positions = []
        colors = []

        for contact in self.model.contacts():
            buffer = mesh_to_facesbuffer(contact.polygon.to_mesh(), color)
            positions += buffer[0]
            colors += buffer[1]

        positions = numpy.array(positions, dtype=numpy.float32)
        colors = numpy.array(colors, dtype=numpy.float32)

        geometry = three.BufferGeometry(
            attributes={
                "position": three.BufferAttribute(positions, normalized=False),
                "color": three.BufferAttribute(colors, normalized=False, itemSize=3),
            }
        )
        material = three.MeshBasicMaterial(
            side="DoubleSide",
            vertexColors="VertexColors",
        )
        return three.Mesh(geometry, material)

    def draw_contactedges(self):
        color = Color(0.2, 0.2, 0.2)

        positions = []
        colors = []

        for contact in self.model.contacts():
            buffer = mesh_to_edgesbuffer(contact.polygon.to_mesh(), color)
            positions += buffer[0]
            colors += buffer[1]

        positions = numpy.array(positions, dtype=numpy.float32)
        colors = numpy.array(colors, dtype=numpy.float32)

        geometry = three.BufferGeometry(
            attributes={
                "position": three.BufferAttribute(positions, normalized=False),
                "color": three.BufferAttribute(colors, normalized=False, itemSize=3),
            }
        )
        material = three.LineBasicMaterial(vertexColors="VertexColors")
        return three.LineSegments(geometry, material)
