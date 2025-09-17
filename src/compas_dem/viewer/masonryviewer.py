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
from compas_dem.models import SurfaceModel
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


class MasonryViewer(Viewer):
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
    surface_linewidth: float = 0.1

    def __init__(self, model=None, config=config):
        super().__init__(config=config)
        self.blockmodel = None
        self.surfacemodel = None
        self.groups = {}
        
        # Auto-detect model type and assign to appropriate attribute
        if model is not None:
            if isinstance(model, BlockModel):
                self.blockmodel = model
            elif isinstance(model, SurfaceModel):
                self.surfacemodel = model
            else:
                raise TypeError(f"Model must be either BlockModel or SurfaceModel, got {type(model).__name__}")

    def add_model(self, model):
        """Add an additional model to the viewer.
        
        Parameters
        ----------
        model : BlockModel or SurfaceModel
            The model to add to the viewer.
        """
        if isinstance(model, BlockModel):
            if self.blockmodel is not None:
                print("Warning: BlockModel already exists, replacing it.")
            self.blockmodel = model
        elif isinstance(model, SurfaceModel):
            if self.surfacemodel is not None:
                print("Warning: SurfaceModel already exists, replacing it.")
            self.surfacemodel = model
        else:
            raise TypeError(f"Model must be either BlockModel or SurfaceModel, got {type(model).__name__}")

    def setup(self):
        self.setup_groups()

        # add blockmodel stuff
        self.add_supports()
        self.add_blocks()
        self.add_contacts()
        self.add_graph()

        # add surfacemodel stuff
        self.add_idos_edos()
        self.add_form()
        self.add_cracks()
        # self.add_bounds()

    # =============================================================================
    # Groups
    # =============================================================================

    def setup_groups(self):
        self.groups["blockmodel"] = self.scene.add_group(name="BlockModel")
        self.groups["supports"] = self.scene.add_group(name="Supports", parent=self.groups["blockmodel"])
        self.groups["blocks"] = self.scene.add_group(name="Blocks", parent=self.groups["blockmodel"])
        self.groups["contacts"] = self.scene.add_group(name="Contacts", parent=self.groups["blockmodel"], show=False)
        self.groups["interactions"] = self.scene.add_group(name="Interactions", parent=self.groups["blockmodel"], show=False)

        self.groups["surfacemodel"] = self.scene.add_group(name="SurfaceModel")
        self.groups["intrados"] = self.scene.add_group(name="Intrados", parent=self.groups["surfacemodel"])
        self.groups["extrados"] = self.scene.add_group(name="Extrados", parent=self.groups["surfacemodel"])
        self.groups["form"] = self.scene.add_group(name="Form", parent=self.groups["surfacemodel"])
        self.groups["cracks"] = self.scene.add_group(name="Cracks", parent=self.groups["surfacemodel"])

    # =============================================================================
    # Blocks and Contacts
    # =============================================================================

    def add_supports(self):
        if self.blockmodel is None:
            return

        parent: Group = self.groups["supports"]

        for block in self.blockmodel.supports():
            parent.add(
                block.modelgeometry,
                facecolor=self.supportcolor,  # type: ignore
                edgecolor=self.supportcolor.contrast,
                linewidth=0.5,  # type: ignore
                name=block.name,  # type: ignore
            )

    def add_blocks(self):
        if self.blockmodel is None:
            return
        
        parent: Group = self.groups["blocks"]

        for block in self.blockmodel.blocks():
            parent.add(
                block.modelgeometry,
                facecolor=self.blockcolor,  # type: ignore
                edgecolor=self.blockcolor.contrast,
                linewidth=0.5,  # type: ignore
                name=block.name,  # type: ignore
            )

    def add_contacts(self):
        if self.blockmodel is None:
            return
        
        parent: Group = self.groups["contacts"]

        for contact in self.blockmodel.contacts():
            geometry = contact.polygon
            color = self.interfacecolor
            parent.add(geometry, linewidth=1, surfacecolor=color, linecolor=color.contrast)  # type: ignore

    def add_form(self):
        """
        Create and add cylindrical pipes for each form-diagram edge into 'Form' group.

        Parameters
        ----------
        max_thick : float, optional
            Maximum pipe radius for the largest detected force.

        """

        if self.surfacemodel is None:
            return
        
        if self.surfacemodel.formdiagram is None:
            return
        else:
            formdiagram : FormDiagram = self.surfacemodel.formdiagram  # type: ignore

        grp: Group = self.groups["form"]

        edges = list(formdiagram.edges_where({'_is_edge': True}))
        forces = [formdiagram.edge_attribute(e, 'q') * formdiagram.edge_length(e) for e in edges] # type: ignore
        f_max = math.sqrt(max(abs(max(forces)), abs(min(forces)))) or 1e-6
        for edge in edges:
            q = formdiagram.edge_attribute(edge, 'q')
            line = formdiagram.edge_line(edge)
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

        if self.surfacemodel is None:
            return
        
        if self.surfacemodel.formdiagram is None:
            return
        else:
            formdiagram : FormDiagram = self.surfacemodel.formdiagram  # type: ignore

        grp: Group = self.groups["cracks"]

        for key in formdiagram.vertices():   # type: ignore
            x, y, z = formdiagram.vertex_coordinates(key)  # type: ignore
            lb = formdiagram.vertex_attribute(key, 'lb')  # type: ignore
            ub = formdiagram.vertex_attribute(key, 'ub')  # type: ignore
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

    def add_bounds(self):
        """
        Identify vertices where the form touches intrados/extrados and add them to 'Cracks' group.

        Parameters
        ----------
        tol : float, optional
            Tolerance for comparing vertex z to lb/ub values.
        """

        if self.surfacemodel is None:
            return
        
        if self.surfacemodel.formdiagram is None:
            return
        else:
            formdiagram : FormDiagram = self.surfacemodel.formdiagram  # type: ignore

        grp: Group = self.groups["cracks"]

        for key in formdiagram.vertices():   # type: ignore
            x, y, z = formdiagram.vertex_coordinates(key)  # type: ignore
            lb = formdiagram.vertex_attribute(key, 'lb')  # type: ignore
            ub = formdiagram.vertex_attribute(key, 'ub')  # type: ignore
            if lb is not None:
                grp.add(Point(x, y, lb), 
                        name=f"intrados_limit_{key}",  # type: ignore
                        pointsize=self.crack_size,  # type: ignore
                        pointcolor=self.intrados_color,  # type: ignore
                        opacity=0.95)  # type: ignore
            if ub is not None:
                grp.add(Point(x, y, ub), 
                        name=f"extrados_limit_{key}",  # type: ignore
                        pointsize=self.crack_size,  # type: ignore
                        pointcolor=self.extrados_color, # type: ignore
                        opacity=0.95) # type: ignore
        self.groups['cracks'] = grp

    def add_forcediagram(self, forcediagram):
        if self.surfacemodel is None:
            return
        self.scene.add(forcediagram, show_faces=False, show_lines=True)

    def add_idos_edos(self):
        if self.surfacemodel is None:
            return
        parent: Group = self.groups["intrados"]
        parent.add(
            self.surfacemodel.intrados, # type: ignore
            facecolor=self.surfacecolor,  # type: ignore
            edgecolor=self.surfacecolor,
            linewidth=self.surface_linewidth,
            opacity=0.8,  # type: ignore
        )

        parent : Group = self.groups["extrados"]
        parent.add(
            self.surfacemodel.extrados, # type: ignore
            facecolor=self.surfacecolor,  # type: ignore
            edgecolor=self.surfacecolor,
            linewidth=self.surface_linewidth,
            opacity=0.8,  # type: ignore
        )

    # =============================================================================
    # Graph
    # =============================================================================

    def add_graph(self):
        if self.blockmodel is None:
            return
        parent: Group = self.groups["interactions"]

        node_point = {node: self.blockmodel.graph.node_element(node).point for node in self.blockmodel.graph.nodes()}  # type: ignore
        points = list(node_point.values())
        lines = [Line(node_point[u], node_point[v]) for u, v in self.blockmodel.graph.edges()]

        nodegroup = self.scene.add_group(name="Nodes", parent=parent)  # type: ignore
        edgegroup = self.scene.add_group(name="Edges", parent=parent)  # type: ignore

        nodegroup.add_from_list(points, pointsize=10, pointcolor=self.graphnodecolor)  # type: ignore
        edgegroup.add_from_list(lines, linewidth=1, linecolor=self.graphedgecolor)  # type: ignore
