import compas.geometry as cg
from compas.colors import Color
from compas.scene import Group
from compas_viewer.config import Config
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


config.ui.menubar.items.append(
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
                name=f"Block {block.graphnode}",  # type: ignore
            )

    def add_blocks(self):
        parent: Group = self.groups["blocks"]

        for block in self.model.blocks():
            parent.add(
                block.modelgeometry,
                facecolor=self.blockcolor,  # type: ignore
                edgecolor=self.blockcolor.contrast,
                linewidth=0.5,  # type: ignore
                name=f"Block {block.graphnode}",  # type: ignore
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
        lines = [cg.Line(node_point[u], node_point[v]) for u, v in self.model.graph.edges()]

        nodegroup = self.scene.add_group(name="Nodes", parent=parent)  # type: ignore
        edgegroup = self.scene.add_group(name="Edges", parent=parent)  # type: ignore

        nodegroup.add_from_list(points, pointsize=10, pointcolor=self.graphnodecolor)  # type: ignore
        edgegroup.add_from_list(lines, linewidth=1, linecolor=self.graphedgecolor)  # type: ignore

    def add_solution(self, scale=1e-7):
        """
        Adds the solution to the viewer.

        Parameters
        ----------
        solver_name : str
            The name of the solver used to generate the solution. This is used to determine how to interpret the solution data and update the viewer accordingly.
            Currently supported solvers:
            - "LMGC90"
            - "CRA" - pending
            - "PRD" - pending
            - "3DEC" - pending

        solution : object
            The solution object returned by the solver. This is expected to contain the updated block geometries and contact information after the simulation run.

        For LMGC90, the following KWARGS are expected:
        - scale_normal: float
            Scaling factor for visualizing contact normals.
        - scale_force: float
            Scaling factor for visualizing contact forces.

        """
        # solver_name = solver_name.lower()  # Ensure solver name is case-insensitive

        # if solver_name == "lmgc90":
        #     scale_normal = kwargs.get("scale_normal", 0.00001)
        #     scale_force = kwargs.get("scale_force", 0.00001)
        #     contacts = solution.get_contacts(scale_normal=scale_normal, scale_force=scale_force)

        #     solution_group = self.scene.add_group(name="Solution")
        #     updated_blocks = self.scene.add_group(name="Updated_Blocks", parent=solution_group)
        #     resultant_forces = self.scene.add_group(name="Forces", parent=solution_group)
        #     contact_polygons = self.scene.add_group(name="Contact_Polygons", parent=solution_group)

        #     supports = solution.supports if solution.supports else []
        #     for i, mesh in enumerate(solution.trimeshes):
        #         is_support = supports[i] if i < len(supports) else False
        #         color = (255, 0, 0) if is_support else (200, 200, 200)
        #         updated_blocks.add(
        #             mesh,
        #             name=f"block_{i}",
        #             facecolor=color,
        #             show_edges=True,
        #             opacity=0.25,
        #         )
        #     for i, line in enumerate(contacts["force_resultants"]):
        #         resultant_forces.add(
        #             line,
        #             name=f"force_resultant_{i}",
        #             linewidth=2.5,
        #             color=(0, 0, 255),
        #         )

        #     for i, polygon in enumerate(contacts["contact_polygons"]):
        #         contact_polygons.add(polygon, name=f"polygon_{i}", color=(0, 100, 0))
        #     # solution.finalize()  # Ensure proper cleanup of LMGC90 resourcesif solver_name == "LMGC90":

        # else:
        #     raise NotImplementedError(f"Viewer update not implemented for solver: {solver_name}")

        scale_force = scale
        moved_blocks = []

        solution_group = self.scene.add_group(name="Solution")
        updated_blocks = self.scene.add_group(name="Updated_Blocks", parent=solution_group)
        resultant_forces = self.scene.add_group(name="Forces", parent=solution_group)
        for block in self.model.elements():
            T = self.model.graph.node_attribute(block.graphnode, "transformation") or cg.Transformation()
            new_block = block.modelgeometry.transformed(T)
            moved_blocks.append(new_block)
            updated_blocks.add(
                new_block,
                name=f"block_{block.graphnode}",
                opacity=0.25,
            )
        for u, v in self.model.graph.edges():
            edge = (min(u, v), max(u, v))
            force = self.model.graph.edge_attribute(edge, "force")
            contact_pts = self.model.graph.edge_attribute(edge, "contact_point")
            fc = self.model.graph.edge_attribute(edge, "friction_contact")
            if not force or not contact_pts:
                continue

            fn_vals = [f["c_np"] - f["c_nn"] for f in fc.forces] if fc else None
            fn_sum = sum(fn_vals) if fn_vals else 0.0

            if fn_vals and abs(fn_sum) > 1e-12:
                pos = cg.Point(*cg.centroid_points_weighted([list(p) for p in fc.points], fn_vals))

                half = [force[j] * fn_sum * scale_force * 0.5 for j in range(3)]
            else:
                n = len(contact_pts)
                pos = cg.Point(*[sum(p[j] for p in contact_pts) / n for j in range(3)])
                half = [force[j] * scale_force * 0.5 for j in range(3)]

            resultant_line = cg.Line([pos[j] + half[j] for j in range(3)], [pos[j] - half[j] for j in range(3)])

            resultant_forces.add(
                resultant_line,
                name=f"force_resultant_{edge}",
                linewidth=2.5,
                linecolor=Color.blue(),
            )
