from math import radians

from compas.datastructures import Mesh
from compas.geometry import Rotation
from compas.geometry import add_vectors
from compas.geometry import angle_vectors
from compas.geometry import subtract_vectors
from compas.geometry import transform_points
from compas.geometry import translate_points

from .template import Template


class BarrelVaultTemplate(Template):
    """Create voussoir geometry for a semi-circular arch with given rise and span.

    Parameters
    ----------
    span : float
        span of the vault
    length : float
        length of the vault perpendicular to the span
    thickness : float
        thickness of the vault
    rise : float
        rise of the vault from 0.0 to middle axis of the vault thickness
    vou_span : int
        number of voussoirs in the span direction
    vou_length : int
        number of voussoirs in the length direction
    zero_is_centerline_or_lowestpoint : bool
        if True, the lowest point of the vault is at the center line of the arch, otherwise the center line of the vault is lowest mesh z-coordinate.

    """

    def __init__(
        self,
        span: float = 6.0,
        length: float = 6.0,
        thickness: float = 0.25,
        rise: float = 0.6,
        vou_span: int = 9,
        vou_length: int = 6,
        zero_is_centerline_or_lowest_point: bool = False,
    ):
        super().__init__()

        self.span = span
        self.length = length
        self.thickness = thickness
        self.rise = rise
        self.vou_span = vou_span
        self.vou_length = vou_length
        self.zero_is_centerline_or_lowest_point = zero_is_centerline_or_lowest_point

    def blocks(self) -> list[Mesh]:
        """Compute the blocks.

        Returns
        -------
        list
            A list of blocks defined as simple meshes.

        """
        span = self.span
        length = self.length
        thickness = self.thickness
        rise = self.rise
        vou_span = self.vou_span
        vou_length = self.vou_length

        radius: float = rise / 2 + span**2 / (8 * rise)
        top: list[float] = [0, 0, rise]
        left: list[float] = [-span / 2, 0, 0]
        center: list[float] = [0.0, 0.0, rise - radius]
        vector: list[float] = subtract_vectors(left, center)
        springing: float = angle_vectors(vector, [-1.0, 0.0, 0.0])
        sector: float = radians(180) - 2 * springing
        angle: float = sector / vou_span

        a: list[float] = [0, -length / 2, rise - (thickness / 2)]
        d: list[float] = add_vectors(top, [0, -length / 2, (thickness / 2)])

        R: Rotation = Rotation.from_axis_and_angle([0, 1.0, 0], 0.5 * sector, center)
        bottom: list[list[float]] = transform_points([a, d], R)
        brick_pts: list[list[list[float]]] = []
        for i in range(vou_span + 1):
            R_angle: Rotation = Rotation.from_axis_and_angle([0, 1.0, 0], -angle * i, center)
            points: list[list[float]] = transform_points(bottom, R_angle)
            brick_pts.append(points)

        depth: float = length / vou_length
        grouped_data: list[list[float]] = [pair[0] + pair[1] for pair in zip(brick_pts, brick_pts[1:])]

        meshes: list[Mesh] = []
        for i in range(vou_length):
            for l, group in enumerate(grouped_data):  # noqa: E741
                is_support: bool = l == 0 or l == (len(grouped_data) - 1)
                if l % 2 == 0:
                    point_l: list[list[float]] = [group[0], group[1], group[2], group[3]]
                    point_list: list[list[float]] = [
                        [group[0][0], group[0][1] + (depth * i), group[0][2]],
                        [group[1][0], group[1][1] + (depth * i), group[1][2]],
                        [group[2][0], group[2][1] + (depth * i), group[2][2]],
                        [group[3][0], group[3][1] + (depth * i), group[3][2]],
                    ]
                    p_t: list[list[float]] = translate_points(point_l, [0, depth * (i + 1), 0])
                    vertices: list[list[float]] = point_list + p_t
                    faces: list[list[int]] = [[0, 1, 3, 2], [0, 4, 5, 1], [4, 6, 7, 5], [6, 2, 3, 7], [1, 5, 7, 3], [2, 6, 4, 0]]
                    mesh: Mesh = Mesh.from_vertices_and_faces(vertices, faces)
                    mesh.attributes["is_support"] = is_support
                    meshes.append(mesh)
                else:
                    point_l: list[list[float]] = [group[0], group[1], group[2], group[3]]
                    points_base: list[list[float]] = translate_points(point_l, [0, depth / 2, 0])
                    points_b_t: list[list[float]] = translate_points(points_base, [0, depth * i, 0])
                    points_t: list[list[float]] = translate_points(points_base, [0, depth * (i + 1), 0])
                    vertices: list[list[float]] = points_b_t + points_t
                    if i != vou_length - 1:
                        faces: list[list[int]] = [[0, 1, 3, 2], [0, 4, 5, 1], [4, 6, 7, 5], [6, 2, 3, 7], [1, 5, 7, 3], [2, 6, 4, 0]]
                        mesh: Mesh = Mesh.from_vertices_and_faces(vertices, faces)
                        mesh.attributes["is_support"] = is_support
                        meshes.append(mesh)

        for l, group in enumerate(grouped_data):  # noqa: E741
            is_support: bool = l == 0 or l == (len(grouped_data) - 1)
            if l % 2 != 0:
                point_l: list[list[float]] = [group[0], group[1], group[2], group[3]]
                p_t: list[list[float]] = translate_points(point_l, [0, depth / 2, 0])
                vertices: list[list[float]] = point_l + p_t
                faces: list[list[int]] = [[0, 1, 3, 2], [0, 4, 5, 1], [4, 6, 7, 5], [6, 2, 3, 7], [1, 5, 7, 3], [2, 6, 4, 0]]
                mesh: Mesh = Mesh.from_vertices_and_faces(vertices, faces)
                mesh.attributes["is_support"] = is_support
                meshes.append(mesh)

                point_f: list[list[float]] = translate_points(point_l, [0, length, 0])
                p_f: list[list[float]] = translate_points(point_f, [0, -depth / 2, 0])
                vertices: list[list[float]] = p_f + point_f
                faces: list[list[int]] = [[0, 1, 3, 2], [0, 4, 5, 1], [4, 6, 7, 5], [6, 2, 3, 7], [1, 5, 7, 3], [2, 6, 4, 0]]
                mesh: Mesh = Mesh.from_vertices_and_faces(vertices, faces)
                mesh.attributes["is_support"] = is_support
                meshes.append(mesh)

        # Find the lowest z-coordinate and move all the block to zero.
        if not self.zero_is_centerline_or_lowest_point:
            min_z: float = min([min(mesh.vertex_coordinates(key)[2] for key in mesh.vertices()) for mesh in meshes])
            for mesh in meshes:
                mesh.translate([0, 0, -min_z])

        return meshes
