from compas.colors import Color
from compas.geometry import Line
from compas.geometry import Point
from compas.geometry import Cylinder
from compas.scene import Group
from compas_viewer.config import Config
from compas_viewer.config import MenubarConfig
from compas_viewer.scene import ViewerSceneObject
from compas_viewer.viewer import Viewer

from compas_dem.models import BlockModel
from compas_dem.models.surfacemodel import SurfaceModel
from compas_tna.diagrams import FormDiagram

from typing import Optional, Union

import math

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


def show_intrados_extrados():
    from compas_viewer import Viewer

    viewer: DEMViewer = Viewer()  # type: ignore

    viewer.groups["intrados"].show = True
    viewer.groups["extrados"].show = True

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
            {
                "title": "Show Inrados|Extrados",
                "action": show_intrados_extrados,
            },
        ],
    }
)


class DEMViewer(Viewer):
    blockcolor: Color = Color.grey().lightened(85)
    supportcolor: Color = Color.red().lightened(50)
    interfacecolor: Color = Color.cyan().lightened(50)
    graphnodecolor: Color = Color.blue()
    graphedgecolor: Color = Color.blue().lightened(50)
    surfacecolor: Color = Color.grey().lightened(90)

    form_max_thk: float = 0.1  # Maximum pipe radius for the largest detected force
    intrados_color: Color = Color.blue().darkened(30)
    extrados_color: Color = Color.green().darkened(30)
    form_color: Color = Color.red()
    shape_color: Color = Color.grey().lightened(30)
    shape_opacity: float = 0.4
    thrust_opacity: float = 0.9
    crack_opacity: float = 0.9
    crack_size: int = 20  # Size of crack points
    cracks_tol: float = 1e-3  # Tolerance for comparing vertex z to lb/ub values

    def __init__(self, model: Union[BlockModel, SurfaceModel], config=config):
        super().__init__(config=config)
        self.model = model
        self.groups = {}

    def setup(self):
        self.setup_groups()

        # add stuff
        self.add_supports()
        self.add_blocks()
        self.add_contacts()
        self.add_graph()

    def setup2(self):
        """Setup the viewer."""
        self.setup_intrados_extrado_groups()

        # add stuff
        self.add_idos_edos()
        self.add_form()

    # =============================================================================
    # Groups
    # =============================================================================

    def setup_groups(self):
        self.groups["model"] = self.scene.add_group(name="Model")
        self.groups["supports"] = self.scene.add_group(name="Supports", parent=self.groups["model"])
        self.groups["blocks"] = self.scene.add_group(name="Blocks", parent=self.groups["model"])
        self.groups["contacts"] = self.scene.add_group(name="Contacts", parent=self.groups["model"], show=False)
        self.groups["interactions"] = self.scene.add_group(name="Interactions", parent=self.groups["model"], show=False)

    def setup_intrados_extrado_groups(self):
        self.groups["model"] = self.scene.add_group(name="Model")
        self.groups["intrados"] = self.scene.add_group(name="Intrados", parent=self.groups["model"])
        self.groups["extrados"] = self.scene.add_group(name="Extrados", parent=self.groups["model"])

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

    def add_formdiagram(self, maxradius=50, minradius=10):

        if self.formdiagram is None:
            return
        else:
            formdiagram : FormDiagram = self.formdiagram

        formgroup = self.scene.add_group(name="FormDiagram")
        formgroup.add(formdiagram.viewmesh, facecolor=Color.magenta(), name="Diagram")  # type: ignore

        group = self.scene.add_group(name="Supports", parent=formgroup)
        for vertex in formdiagram.vertices_where(is_support=True):
            group.add(formdiagram.vertex_point(vertex), pointsize=10, pointcolor=Color.red())  # type: ignore

        fmax = max(formdiagram.edges_attribute("_f"))  # type: ignore
        pipes = []
        for edge in formdiagram.edges():
            force = formdiagram.edge_attribute(edge, "_f")
            radius = maxradius * force / fmax  # type: ignore
            if radius > minradius:
                cylinder = Cylinder.from_line_and_radius(formdiagram.edge_line(edge), radius)
                pipes.append(cylinder)

        group = self.scene.add_group(name="Pipes", parent=formgroup)
        group.add_from_list(pipes, surfacecolor=Color.blue())  # type: ignore

    def add_form(self):
        """
        Create and add cylindrical pipes for each form-diagram edge into 'Form' group.

        Parameters
        ----------
        max_thick : float, optional
            Maximum pipe radius for the largest detected force.

        """

        if self.model.formdiagram is None:
            return

        grp = self.scene.add_group(name='Form', show=True)

        edges = list(self.model.formdiagram.edges_where({'_is_edge': True}))
        forces = [self.model.formdiagram.edge_attribute(e, 'q') * self.model.formdiagram.edge_length(e) for e in edges] # type: ignore
        f_max = math.sqrt(max(abs(max(forces)), abs(min(forces)))) or 1e-6
        for edge in edges:
            q = self.model.formdiagram.edge_attribute(edge, 'q')
            line = self.model.formdiagram.edge_line(edge)
            length = line.length
            force = math.sqrt(abs(q * length))
            if force < 1e-3:
                continue
            radius = (force / f_max) * self.form_max_thk
            cyl = Cylinder.from_line_and_radius(line, radius)
            grp.add(cyl, 
                    name=f"thrust_{edge}",  # type: ignore
                    color = self.form_color,  # type: ignore 
                    opacity = self.thrust_opacity)  # type: ignore
        self.groups['form'] = grp

    def add_cracks(self):
        """
        Identify vertices where the form touches intrados/extrados and add them to 'Cracks' group.

        Parameters
        ----------
        tol : float, optional
            Tolerance for comparing vertex z to lb/ub values.
        """
        grp = self.scene.add_group(name='Cracks', show=True)

        for key in self.formdiagram.vertices():   # type: ignore
            x, y, z = self.formdiagram.vertex_coordinates(key)  # type: ignore
            lb = self.formdiagram.vertex_attribute(key, 'lb')  # type: ignore
            ub = self.formdiagram.vertex_attribute(key, 'ub')  # type: ignore
            if lb is not None and abs(z - lb) < self.cracks_tol:
                grp.add(Point(x, y, z), 
                        name=f"intrados_crack_{key}",  # type: ignore
                        pointsize=self.crack_size,  # type: ignore
                        pointcolor=self.intrados_color,  # type: ignore
                        opacity=self.crack_opacity)  # type: ignore
            if ub is not None and abs(ub - z) < self.cracks_tol:
                grp.add(Point(x, y, z), 
                        name=f"extrados_crack_{key}",  # type: ignore
                        pointsize=self.crack_size,  # type: ignore
                        pointcolor=self.extrados_color, # type: ignore
                        opacity=self.crack_opacity) # type: ignore
        self.groups['cracks'] = grp

    def add_forcediagram(self, forcediagram):
        self.scene.add(forcediagram, show_faces=False, show_lines=True)

    def add_idos_edos(self):
        parent: Group = self.groups["intrados"]
        parent.add(
            self.model.intrados,
            facecolor=self.surfacecolor,  # type: ignore
            edgecolor=self.surfacecolor.contrast,
            opacity=0.8,  # type: ignore
        )

        parent : Group = self.groups["extrados"]
        parent.add(
            self.model.extrados,
            facecolor=self.surfacecolor,  # type: ignore
            edgecolor=self.surfacecolor.contrast,
            opacity=0.8,  # type: ignore
        )

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
