from compas.plugins import plugin
from compas.scene import register

from compas_dem.models import BlockModel
from .modelobject import ThreeBlockModelObject


@plugin(category="factories", requires=["pythreejs"])
def register_scene_objects():
    register(BlockModel, ThreeBlockModelObject, context="Notebook")
