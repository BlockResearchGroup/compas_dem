import math
from math import radians

from compas.datastructures import Mesh
from compas.geometry import Rotation
from compas.geometry import add_vectors
from compas.geometry import angle_vectors
from compas.geometry import subtract_vectors
from compas.geometry import transform_points
from compas.geometry import translate_points

from .template import Template

_FACES = [
    [0, 1, 3, 2],
    [0, 4, 5, 1],
    [4, 6, 7, 5],
    [6, 2, 3, 7],
    [1, 5, 7, 3],
    [2, 6, 4, 0],
]


class BarrelVaultStaggeredTemplate(Template):
    """Barrel vault with a configurable staggering pattern and optional end beam rows.

    Parameters
    ----------
    span : float
        Span of the vault.
    length : float
        Length of the vault perpendicular to the span.
    thickness : float
        Thickness of the vault.
    rise : float
        Rise of the vault (from springing to middle axis of vault thickness).
    vou_span : int
        Number of voussoirs in the span (arch) direction.
    vou_length : int
        Number of voussoirs in the length direction.
    stagger : float
        Staggering offset as a fraction of block depth, in range ``[0.0, 1.0)``.
        ``0.0`` produces aligned (no-stagger) joints; ``0.5`` is the classic
        half-block brick pattern; ``0.2`` shifts alternating arch columns by
        20 % of the block depth.
    add_beam_row : bool
        When ``True``, a non-staggered arch ring of the same voussoir depth is
        appended at each longitudinal end of the vault, acting as a closing rib
        or beam.
    zero_is_centerline_or_lowest_point : bool
        When ``False`` (default) the whole assembly is translated so its lowest
        vertex sits at z = 0.  When ``True`` the arch centre-line is kept at
        the nominal coordinates.
    """

    def __init__(
        self,
        span: float = 6.0,
        length: float = 6.0,
        thickness: float = 0.25,
        rise: float = 0.6,
        vou_span: int = 9,
        vou_length: int = 6,
        stagger: float = 0.5,
        add_beam_row: bool = False,
        zero_is_centerline_or_lowest_point: bool = False,
    ):
        super().__init__()
        self.span = span
        self.length = length
        self.thickness = thickness
        self.rise = rise
        self.vou_span = vou_span
        self.vou_length = vou_length
        self.stagger = stagger
        self.add_beam_row = add_beam_row
        self.zero_is_centerline_or_lowest_point = zero_is_centerline_or_lowest_point

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _arch_column_pts(self) -> list[list[list[float]]]:
        """Return the (vou_span+1) cross-section point pairs along the arch."""
        span = self.span
        thickness = self.thickness
        rise = self.rise
        vou_span = self.vou_span
        length = self.length

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
        seed: list[list[float]] = transform_points([a, d], R)

        pts: list[list[list[float]]] = []
        for i in range(vou_span + 1):
            R_i: Rotation = Rotation.from_axis_and_angle([0, 1.0, 0], -angle * i, center)
            pts.append(transform_points(seed, R_i))
        return pts

    @staticmethod
    def _make_block(pts_b: list[list[float]], pts_t: list[list[float]], is_support: bool) -> Mesh:
        mesh: Mesh = Mesh.from_vertices_and_faces(pts_b + pts_t, _FACES)
        mesh.attributes["is_support"] = is_support
        return mesh

    # ------------------------------------------------------------------
    # public
    # ------------------------------------------------------------------

    def blocks(self) -> list[Mesh]:
        """Compute the blocks.

        Returns
        -------
        list[Mesh]
            A list of blocks defined as simple meshes.
        """
        vou_length = self.vou_length
        length = self.length
        s = self.stagger

        depth: float = length / vou_length

        arch_pts = self._arch_column_pts()
        # Each entry in grouped_data is 4 points: two from column l, two from column l+1,
        # all located at y = -length/2 (the seed plane of the vault).
        grouped_data: list[list[list[float]]] = [p[0] + p[1] for p in zip(arch_pts, arch_pts[1:])]

        meshes: list[Mesh] = []

        for l, group in enumerate(grouped_data):  # noqa: E741
            is_support: bool = l == 0 or l == len(grouped_data) - 1
            base: list[list[float]] = group[:4]  # 4 pts at y = -length/2

            if l % 2 == 0:
                # ── Even columns ── no offset; blocks fill the vault cleanly ──────
                for i in range(vou_length):
                    pts_b = translate_points(base, [0, depth * i, 0])
                    pts_t = translate_points(base, [0, depth * (i + 1), 0])
                    meshes.append(self._make_block(pts_b, pts_t, is_support))

            else:
                # ── Odd columns ── offset by s*depth ─────────────────────────────
                offset: float = s * depth

                # Starting fragment [0, offset] — only when s > 0
                if offset > 1e-10:
                    meshes.append(self._make_block(base, translate_points(base, [0, offset, 0]), is_support))

                # Full blocks that fit entirely within [0, length]
                # condition: offset + depth*(i+1) <= length  →  i <= vou_length-1-s
                i_max: int = math.floor(vou_length - 1 - s + 1e-9)
                for i in range(i_max + 1):
                    pts_b = translate_points(base, [0, offset + depth * i, 0])
                    pts_t = translate_points(base, [0, offset + depth * (i + 1), 0])
                    meshes.append(self._make_block(pts_b, pts_t, is_support))

                # Ending fragment [end_start, length] — only when block ends before length/2
                end_start: float = offset + depth * (i_max + 1)
                if end_start < length - 1e-10:
                    pts_b = translate_points(base, [0, end_start, 0])
                    pts_t = translate_points(base, [0, length, 0])
                    meshes.append(self._make_block(pts_b, pts_t, is_support))

        # ── Optional beam rows at the longitudinal ends of the vault ──────────────
        if self.add_beam_row:
            for l, group in enumerate(grouped_data):  # noqa: E741
                is_support: bool = l == 0 or l == len(grouped_data) - 1
                base: list[list[float]] = group[:4]

                # Front beam ring: just before y = -length/2
                pts_b = translate_points(base, [0, -depth, 0])
                meshes.append(self._make_block(pts_b, base, is_support))

                # Back beam ring: just after y = length/2
                pts_b = translate_points(base, [0, length, 0])
                pts_t = translate_points(base, [0, length + depth, 0])
                meshes.append(self._make_block(pts_b, pts_t, is_support))

        # ── Translate so lowest vertex sits at z = 0 (unless suppressed) ─────────
        if not self.zero_is_centerline_or_lowest_point:
            min_z: float = min(min(mesh.vertex_coordinates(v)[2] for v in mesh.vertices()) for mesh in meshes)
            for mesh in meshes:
                mesh.translate([0, 0, -min_z])

        return meshes
