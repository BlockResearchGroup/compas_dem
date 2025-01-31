from typing import Optional

import pythreejs as three
from compas.colors import Color
from compas_notebook.scene import ThreeSceneObject

from compas_dem.models import BlockModel

from .buffers import meshes_to_edgesbuffer
from .buffers import meshes_to_facesbuffer


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

    def draw_blockfaces(self) -> three.Mesh:
        meshes = [block.modelgeometry for block in self.model.blocks()]
        return meshes_to_facesbuffer(meshes, Color(0.9, 0.9, 0.9))

    def draw_blockedges(self) -> three.LineSegments:
        meshes = [block.modelgeometry for block in self.model.blocks()]
        return meshes_to_edgesbuffer(meshes, Color(0.2, 0.2, 0.2))

    def draw_supportfaces(self) -> three.Mesh:
        meshes = [block.modelgeometry for block in self.model.supports()]
        return meshes_to_facesbuffer(meshes, Color.red().lightened(50))

    def draw_supportedges(self) -> three.LineSegments:
        meshes = [block.modelgeometry for block in self.model.supports()]
        return meshes_to_edgesbuffer(meshes, Color(0.2, 0.2, 0.2))

    def draw_contactfaces(self):
        meshes = [contact.polygon.to_mesh() for contact in self.model.contacts()]
        return meshes_to_facesbuffer(meshes, Color.cyan().lightened(75))

    def draw_contactedges(self):
        meshes = [contact.polygon.to_mesh() for contact in self.model.contacts()]
        return meshes_to_edgesbuffer(meshes, Color(0.2, 0.2, 0.2))
