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

        self.color_edges = Color(0.2, 0.2, 0.2)
        self.color_blocks = Color(0.9, 0.9, 0.9)
        self.color_supports = Color.red().lightened(50)
        self.color_contacts = Color.cyan().lightened(75)

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
            facesbuffer, edgesbuffer = self.draw_blocks()
            if facesbuffer:
                self._guids.append(facesbuffer)
            if edgesbuffer:
                self._guids.append(edgesbuffer)

        if self.show_supports:
            facesbuffer, edgesbuffer = self.draw_supports()
            self._guids.append(facesbuffer)
            self._guids.append(edgesbuffer)

        if self.show_contacts:
            facesbuffer, edgesbuffer = self.draw_contacts()
            self._guids.append(facesbuffer)
            self._guids.append(edgesbuffer)

        return self.guids

    def draw_blocks(self) -> tuple[three.Mesh, three.LineSegments]:
        """Draw the blocks of the model."""
        meshes = [block.modelgeometry for block in self.model.blocks()]

        if self.show_blockfaces:
            facesbuffer = meshes_to_facesbuffer(meshes, self.color_blocks)
        else:
            facesbuffer = None

        edgesbuffer = meshes_to_edgesbuffer(meshes, self.color_edges)

        return facesbuffer, edgesbuffer

    def draw_supports(self) -> tuple[three.Mesh, three.LineSegments]:
        """Draw the supports of the model."""
        meshes = [block.modelgeometry for block in self.model.supports()]

        facesbuffer = meshes_to_facesbuffer(meshes, self.color_supports)
        edgesbuffer = meshes_to_edgesbuffer(meshes, self.color_edges)

        return facesbuffer, edgesbuffer

    def draw_contacts(self) -> tuple[three.Mesh, three.LineSegments]:
        """Draw the contacts between the blocks."""
        meshes = [contact.polygon.to_mesh() for contact in self.model.contacts()]

        facesbuffer = meshes_to_facesbuffer(meshes, self.color_contacts)
        edgesbuffer = meshes_to_edgesbuffer(meshes, self.color_edges)

        return facesbuffer, edgesbuffer

    # =============================================================================
    # Individual components
    # =============================================================================

    def draw_blockfaces(self) -> three.Mesh:
        meshes = [block.modelgeometry for block in self.model.blocks()]
        return meshes_to_facesbuffer(meshes, self.color_blocks)

    def draw_blockedges(self) -> three.LineSegments:
        meshes = [block.modelgeometry for block in self.model.blocks()]
        return meshes_to_edgesbuffer(meshes, self.color_edges)

    def draw_supportfaces(self) -> three.Mesh:
        meshes = [block.modelgeometry for block in self.model.supports()]
        return meshes_to_facesbuffer(meshes, self.color_supports)

    def draw_supportedges(self) -> three.LineSegments:
        meshes = [block.modelgeometry for block in self.model.supports()]
        return meshes_to_edgesbuffer(meshes, self.color_edges)

    def draw_contactfaces(self):
        meshes = [contact.polygon.to_mesh() for contact in self.model.contacts()]
        return meshes_to_facesbuffer(meshes, self.color_contacts)

    def draw_contactedges(self):
        meshes = [contact.polygon.to_mesh() for contact in self.model.contacts()]
        return meshes_to_edgesbuffer(meshes, self.color_edges)
