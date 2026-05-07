import numpy as np
from compas_viewer.config import Config
from compas_viewer.scene import ViewerSceneObject
from compas_viewer.viewer import Viewer

import compas.geometry as cg
from compas.colors import Color
from compas.scene import Group
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

    def add_solution(self, scale=1.0):
        """
        Adds the solution to the viewer.

        Parameters
        ----------
        - scale : float
            A scaling factor for the resultant force lines, to make them visible in the viewer. Adjust as needed based on the magnitude of forces in the model.

        """

        moved_blocks = []

        solution_group = self.scene.add_group(name="Solution")
        updated_blocks = self.scene.add_group(name="Updated_Blocks", parent=solution_group)
        resultant_forces = self.scene.add_group(name="Forces", parent=solution_group)
        face_contacts = self.scene.add_group(name="Contact_Polygons", parent=solution_group)
        edge_contacts = self.scene.add_group(name="Contact_Edges", parent=solution_group)
        supports = self.scene.add_group(name="Supports", parent=solution_group)
        reactions = self.scene.add_group(name="Reactions", parent=supports)
        support_contacts = self.scene.add_group(name="Support_Contacts", parent=supports)
        point_results = self.scene.add_group(name="Point Results : [Fn, Ft1, Ft2]", parent=solution_group)
        degenerate_contacts = self.scene.add_group(name="Degenerate_Contacts", parent=solution_group)

        block_ln = []
        for block in self.model.elements():
            T = self.model.graph.node_attribute(block.graphnode, "transformation") or cg.Transformation()
            new_block = block.modelgeometry.transformed(T)
            moved_blocks.append(new_block)
            updated_blocks.add(
                new_block,
                name=f"block_{block.graphnode}",
                opacity=0.25,
            )
            try:
                block_ln.append(block.modelgeometry.edge_length([0, 1]))
            except Exception:
                pass

        forces = [np.array((self.model.graph.edge_attribute(edge, "force") or [0, 0, 0])) for edge in self.model.graph.edges()]
        max_force = max(np.linalg.norm(force) for force in forces)
        block_scale = scale * max(block_ln) / max_force if max_force > 0 else 1.0

        face_contact_edges = list(self.model.graph.edges_where(face_contact=True))
        edge_contact_edges = list(self.model.graph.edges_where(edge_contact=True))

        # =============================================================================
        # Supports and reactions
        # =============================================================================
        supports = list(support.graphnode for support in self.model.supports())
        support_edges = {s: [] for s in supports}
        for edge in self.model.graph.edges():
            u, v = edge
            if u in supports:
                support_edges[u].append(edge)
            if v in supports:
                support_edges[v].append(edge)

        for support_node, edges in support_edges.items():
            point_forces: list[tuple[cg.Point, cg.Vector]] = []
            support_block = self.model.graph.node_element(support_node)
            support_point = support_block.point

            for edge in edges:
                if edge in face_contact_edges:
                    fc = self.model.graph.edge_attribute(edge, "contact_data")

                    if fc is None:
                        continue

                    resultant = fc.resultantline()
                    if resultant is None:
                        continue

                    from_support = cg.Vector.from_start_end(support_point, resultant.midpoint)
                    if resultant.vector.dot(from_support) < 0:
                        resultant.vector.flip()

                    point_forces.append((fc.resultantpoint, resultant.vector))

                    # Viz the contact polygon

                    contact_polygon = self.model.graph.edge_attribute(edge, "contact_polygon")

                    if contact_polygon.area < 1e-6:
                        print(f"WARNING:\nContact polygon for support edge {edge} has very small area ({contact_polygon.area:.2e}), skipping visualization. \n")
                        continue

                    polyg = contact_polygon.to_brep()
                    support_contacts.add(
                        polyg,
                        name=f"contact_polygon_{edge}",
                        color=Color.brown(),
                        opacity=0.5,
                    )

                elif edge in edge_contact_edges:
                    ec = self.model.graph.edge_attribute(edge, "contact_data")
                    support_contacts.add(
                        cg.Line(ec.points[0], ec.points[1]),
                        name=f"contact_line_{edge}",
                        linewidth=2,
                        linecolor=Color.brown(),
                    )

                    if ec.resultantline() is None:
                        continue

                    from_support = cg.Vector.from_start_end(support_point, resultant.midpoint)

                    if resultant.vector.dot(from_support) < 0:
                        resultant.vector.flip()
                    point_forces.append((ec.resultantpoint, ec.resultantline().vector))

            if point_forces:
                weights = [f.length for _, f in point_forces]

                total_weight = sum(weights)

                if total_weight > 0:
                    position = cg.Point(
                        sum(p.x * w for (p, _), w in zip(point_forces, weights)) / total_weight,
                        sum(p.y * w for (p, _), w in zip(point_forces, weights)) / total_weight,
                        sum(p.z * w for (p, _), w in zip(point_forces, weights)) / total_weight,
                    )
                    resultant = cg.Vector(0, 0, 0)

                    for _, f in point_forces:
                        if f:
                            resultant += f

                    # if resultant.dot(cg.Vector(0, 0, 1)) < 0:
                    #     resultant.flip()
                    forcevector = resultant * 0.5

                    p1 = position + forcevector * block_scale
                    p2 = position - forcevector * block_scale
                    reactions.add(
                        cg.Line(p1, p2),
                        name=f"F=({resultant.x:.1f}, {resultant.y:.1f}, {resultant.z:.1f}) \n|F|={resultant.length:.1f}",
                        linewidth=2.5,
                        color=Color.red(),
                    )

        # =============================================================================
        # Visualize forces at contacts
        # =============================================================================

        # Face contacts
        # --------------
        for edge in face_contact_edges:
            fc = self.model.graph.edge_attribute(edge, "contact_data")
            contact_polygon = self.model.graph.edge_attribute(edge, "contact_polygon")
            resultant = fc.resultantforce[0].vector

            if fc is None:
                continue
            resultant_line = fc.resultantline(scale=block_scale)
            if resultant_line is not None:
                resultant_forces.add(
                    resultant_line,
                    name=f"F=({resultant.x:.1f}, {resultant.y:.1f}, {resultant.z:.1f}) \n|F|={resultant.length:.1f}",
                    linewidth=2.5,
                    linecolor=Color.blue(),
                )

            if contact_polygon.area < 1e-6:
                if len(contact_polygon.points) < 3:
                    print(f"WARNING:\nContact polygon for edge {edge} has less than 3 points, skipping visualization. \n")
                    continue
                # Collapse it to a line if it's very small, to avoid visualization issues
                lines_polyg = []
                for line in contact_polygon.lines:
                    lines_polyg.append(line.length)
                line_min = min(lines_polyg)
                line_max = max(lines_polyg)

                # collapse face contact to a line
                if line_max > 0.001 and line_max / line_min > 10:
                    longest_line = contact_polygon.lines[np.argmax(lines_polyg)]
                    degenerate_contacts.add(
                        longest_line,
                        name=f"contact_line_{edge}",
                        linewidth=2,
                        linecolor=Color.red(),
                    )
                elif line_max / line_min <= 10:
                    print(f"Contact_polygon {contact_polygon}")
                    point = contact_polygon.centroid
                    degenerate_contacts.add(
                        point,
                        name=f"contact_point_{edge}",
                        pointsize=5,
                        pointcolor=Color.red(),
                    )

                continue

            polyg = contact_polygon.to_brep()
            face_contacts.add(
                polyg,
                name=f"contact_polygon_{edge}",
                color=Color.green(),
                opacity=0.5,
            )

            # Viz the point forces

            for i, (point, force) in enumerate(zip(fc.points, fc.forces)):
                c_np, c_u, c_v = force["c_np"], force["c_u"], force["c_v"]
                t1, t2, n = fc.frame.xaxis, fc.frame.yaxis, fc.frame.zaxis
                forcevector_unsc = n * c_np + t1 * c_u + t2 * c_v

                # point = fc.points[i]

                if forcevector_unsc and point is not None:
                    forcevector = forcevector_unsc * block_scale
                    p1 = point.translated(forcevector)
                    p2 = point.translated(-forcevector)
                    point_results.add(
                        cg.Line(p1, p2),
                        name=f"[{c_np:.1f}, {c_u:.1f}, {c_v:.1f}] \n|F|={forcevector_unsc.length:.1f}",
                        linewidth=2.5,
                        linecolor=Color.magenta(),
                    )

        # Edge contacts
        # --------------
        for edge in edge_contact_edges:
            ec = self.model.graph.edge_attribute(edge, "contact_data")

            if ec.resultantforce is None:
                continue
            resultant = ec.resultantforce.vector
            line = ec.resultantline(scale=block_scale) if ec else None

            if line is None:
                continue
            resultant_forces.add(
                line,
                name=f"F=({resultant.x:.1f}, {resultant.y:.1f}, {resultant.z:.1f}) \n|F|={resultant.length:.1f}",
                linewidth=2.5,
                linecolor=Color.blue(),
            )

            edge_contacts.add(
                cg.Line(ec.points[0], ec.points[1]),
                name=f"contact_line_{edge}",
                linewidth=2,
                linecolor=Color.red(),
            )
