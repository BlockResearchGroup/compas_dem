from compas.colors import Color
from compas.geometry import Line
from compas.scene import Group
from compas_viewer.config import Config
from compas_viewer.config import MenubarConfig
from compas_viewer.scene import ViewerSceneObject
from compas_viewer.viewer import Viewer

from compas_dem.models import BlockModel

config = Config()


def show_blocks():
    from compas_viewer import Viewer

    viewer: DEMViewer = Viewer()  # type: ignore

    viewer.groups["supports"].show = True
    viewer.groups["blocks"].show = True
    viewer.groups["contacts"].show = False
    viewer.groups["interactions"].show = False

    obj: ViewerSceneObject

    for obj in viewer.groups["supports"].children:
        obj.show_faces = True
        obj.update()

    for obj in viewer.groups["blocks"].children:
        obj.show_faces = True
        obj.update()

    viewer.ui.sidebar.update()
    viewer.renderer.update()


def show_contacts():
    from compas_viewer import Viewer

    viewer: DEMViewer = Viewer()  # type: ignore

    viewer.groups["supports"].show = True
    viewer.groups["blocks"].show = True
    viewer.groups["contacts"].show = True
    viewer.groups["interactions"].show = False

    obj: ViewerSceneObject

    for obj in viewer.groups["supports"].children:
        obj.show_faces = False
        obj.update()

    for obj in viewer.groups["blocks"].children:
        obj.show_faces = False
        obj.update()

    viewer.ui.sidebar.update()
    viewer.renderer.update()


def show_interactions():
    from compas_viewer import Viewer

    viewer: DEMViewer = Viewer()  # type: ignore

    viewer.groups["supports"].show = True
    viewer.groups["blocks"].show = True
    viewer.groups["contacts"].show = False
    viewer.groups["interactions"].show = True

    obj: ViewerSceneObject

    for obj in viewer.groups["supports"].children:
        obj.show_faces = False
        obj.update()

    for obj in viewer.groups["blocks"].children:
        obj.show_faces = False
        obj.update()

    viewer.ui.sidebar.update()
    viewer.renderer.update()


MenubarConfig._items.append(
    {
        "title": "COMPAS DEM",
        "items": [
            {
                "title": "Show Blocks",
                "action": show_blocks,
            },
            {
                "title": "Show Contacts",
                "action": show_contacts,
            },
            {
                "title": "Show Interactions",
                "action": show_interactions,
            },
        ],
    }
)


class DEMViewer(Viewer):
    blockcolor: Color = Color.grey().lightened(85)
    supportcolor: Color = Color.red().lightened(50)
    interfacecolor: Color = Color.cyan().lightened(50)
    graphnodecolor: Color = Color.blue()
    graphedgecolor: Color = Color.cyan().lightened(50)

    def __init__(self, model: BlockModel, config=config):
        super().__init__(config=config)
        self.model = model
        self.groups = {}

    # def add_formdiagram(self, formdiagram: FormDiagram, maxradius=50, minradius=10):
    #     formgroup = self.scene.add_group(name="FormDiagram")
    #     formgroup.add(formdiagram.viewmesh, facecolor=Color.magenta(), name="Diagram")  # type: ignore

    #     group = self.scene.add_group(name="Supports", parent=formgroup)
    #     for vertex in formdiagram.vertices_where(is_support=True):
    #         group.add(formdiagram.vertex_point(vertex), pointsize=10, pointcolor=Color.red())  # type: ignore

    #     fmax = max(formdiagram.edges_attribute("_f"))  # type: ignore
    #     pipes = []
    #     for edge in formdiagram.edges():
    #         force = formdiagram.edge_attribute(edge, "_f")
    #         radius = maxradius * force / fmax  # type: ignore
    #         if radius > minradius:
    #             cylinder = Cylinder.from_line_and_radius(formdiagram.edge_line(edge), radius)
    #             pipes.append(cylinder)

    #     group = self.scene.add_group(name="Pipes", parent=formgroup)
    #     group.add_from_list(pipes, surfacecolor=Color.blue())  # type: ignore

    # def add_forcediagram(self, forcediagram):
    #     self.scene.add(forcediagram, show_faces=False, show_lines=True)

    def setup(self):
        self.setup_groups()

        # add stuff
        self.add_supports()
        self.add_blocks()
        self.add_contacts()
        self.add_graph()

    # =============================================================================
    # Groups
    # =============================================================================

    def setup_groups(self):
        self.groups["model"] = self.scene.add_group(name="Model")
        self.groups["supports"] = self.scene.add_group(name="Supports", parent=self.groups["model"])
        self.groups["blocks"] = self.scene.add_group(name="Blocks", parent=self.groups["model"])
        self.groups["contacts"] = self.scene.add_group(name="Contacts", parent=self.groups["model"], show=False)
        self.groups["interactions"] = self.scene.add_group(name="Interactions", parent=self.groups["model"], show=False)

    # =============================================================================
    # Blocks and Contacts
    # =============================================================================

    def add_supports(self):
        parent: Group = self.groups["supports"]

        for block in self.model.supports():
            parent.add(
                block.modelgeometry,
                facecolor=self.supportcolor,  # type: ignore
                edgecolor=self.supportcolor.contrast,
                linewidth=0.5,  # type: ignore
                name=block.name,  # type: ignore
            )

    def add_blocks(self):
        parent: Group = self.groups["blocks"]

        for block in self.model.blocks():
            parent.add(
                block.modelgeometry,
                facecolor=self.blockcolor,  # type: ignore
                edgecolor=self.blockcolor.contrast,
                linewidth=0.5,  # type: ignore
                name=block.name,  # type: ignore
            )

    def add_contacts(self):
        parent: Group = self.groups["contacts"]

        for contact in self.model.contacts():
            geometry = contact.polygon
            color = self.interfacecolor
            parent.add(geometry, linewidth=1, surfacecolor=color, linecolor=color.contrast)  # type: ignore

    # =============================================================================
    # Graph
    # =============================================================================

    def add_graph(self):
        parent: Group = self.groups["interactions"]

        node_point = {node: self.model.graph.node_element(node).point for node in self.model.graph.nodes()}  # type: ignore
        points = list(node_point.values())
        lines = [Line(node_point[u], node_point[v]) for u, v in self.model.graph.edges()]

        nodegroup = self.scene.add_group(name="Nodes", parent=parent)  # type: ignore
        edgegroup = self.scene.add_group(name="Edges", parent=parent)  # type: ignore

        nodegroup.add_from_list(points, pointsize=10, pointcolor=self.graphnodecolor)  # type: ignore
        edgegroup.add_from_list(lines, linewidth=1, linecolor=self.graphedgecolor)  # type: ignore
