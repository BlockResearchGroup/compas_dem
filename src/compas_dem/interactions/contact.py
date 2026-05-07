from typing import Annotated
from typing import Optional
from typing import Union

from compas.data import Data
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Point
from compas.geometry import Polygon
from compas.geometry import Transformation
from compas.geometry import Vector
from compas.geometry import centroid_points_weighted
from compas.geometry import dot_vectors
from compas.geometry import transform_points
from compas.itertools import pairwise
from compas_model.interactions import Contact


def outer_product(u, v):
    return [[ui * vi for vi in v] for ui in u]


def scale_matrix(M, scale):
    r = len(M)
    c = len(M[0])
    for i in range(r):
        for j in range(c):
            M[i][j] *= scale
    return M


def sum_matrices(A, B):
    r = len(A)
    c = len(A[0])
    M = [[None for j in range(c)] for i in range(r)]
    for i in range(r):
        for j in range(c):
            M[i][j] = A[i][j] + B[i][j]
    return M


class VertexContact(Data):
    """Class representing a point contact between two elements.

    Parameters
    ----------
    point : :class:`compas.geometry.Point`
        The point defining the contact.
    frame : :class:`compas.geometry.Frame`, optional
        The local coordinate system of the contact.
    name : str, optional
        A human-readable name.

    Warnings
    --------
    The definition of vertex contacts is under active development and may change frequently.

    """

    @property
    def __data__(self) -> dict:
        return {
            "point": self._point,
            "frame": self._frame,
            "name": self.name,
        }

    def __init__(
        self,
        point: Point,
        frame: Frame = None,
        name: Optional[str] = None,
    ):
        super().__init__(name)
        self._point = point
        self._frame = frame

    @property
    def point(self) -> Point:
        return self._point

    @property
    def frame(self) -> Optional[Frame]:
        return self._frame

    @property
    def geometry(self):
        return self.point


class EdgeContact(Data):
    """Contact between a vertex and an edge, defined by two points and a frame.

    Parameters
    ----------
    points : list[:class:`compas.geometry.Point`]
        The two contact points.
    frame : :class:`compas.geometry.Frame`
        The contact frame. ``zaxis`` is the contact normal (n);
        ``xaxis`` and ``yaxis`` are the tangential directions (t1, t2).
    forces : list[dict[str, float]], optional
        Force components at each contact point, expressed in the contact frame.
        Each dict uses keys ``"c_np"`` (normal compression), ``"c_nn"`` (normal tension),
        ``"c_u"`` (tangential t1), ``"c_v"`` (tangential t2).

    """

    def __init__(self, points, frame, forces=None, name=None, **kwargs):
        super().__init__(name=name, **kwargs)
        self._points = [Point(*p) for p in points]
        self._frame = frame
        self._forces = forces or []

    @property
    def points(self) -> list[Point]:
        return self._points

    @property
    def frame(self) -> Frame:
        return self._frame

    # ==========================================================================
    # Factory methods
    # ==========================================================================

    @property
    def __data__(self) -> dict:
        return {
            "points": self._points,
            "frame": self._frame,
            "forces": self._forces,
            "name": self.name,
        }

    @classmethod
    def __from_data__(cls, data: dict) -> "EdgeContact":
        return cls(
            points=data["points"],
            frame=data["frame"],
            forces=data.get("forces") or [],
            name=data.get("name"),
        )

    @classmethod
    def from_face_and_transformations(
        cls,
        face,
        transformation_a: Transformation,
        transformation_b: Transformation,
        points: list[Point],
        forces=None,
        **kwargs,
    ) -> "EdgeContact":
        """Construct from a shared mesh face and the two blocks' current transformations.

        Used when the contact was originally face-face (before displacement).
        The face is duplicated and transformed by each block's current transformation;
        the contact frame's ``zaxis`` is the bisector of the two transformed face normals.
        The frame's origin is the midpoint of the two contact points.

        Parameters
        ----------
        face : :class:`compas.datastructures.Mesh`
            The original shared face (single-face mesh) when contact was face-face.
        transformation_a : :class:`compas.geometry.Transformation`
            Current transformation of block A.
        transformation_b : :class:`compas.geometry.Transformation`
            Current transformation of block B.
        points : list[:class:`compas.geometry.Point`]
            The two new contact points (the edge after displacement).
        forces : list[dict[str, float]], optional

        Returns
        -------
        :class:`EdgeContact`

        """
        face_a = face.transformed(transformation_a)
        face_b = face.transformed(transformation_b)

        n_a = Vector(*face_a.face_normal(0))
        n_b = Vector(*face_b.face_normal(0))

        # Originally face-face: the two normals are opposite. Flip n_b so both
        # point the same way, then average to get the bisector.
        if dot_vectors(n_a, n_b) < 0:
            n_b = n_b.scaled(-1)
        zaxis = (n_a + n_b).unitized()

        p0, p1 = points[0], points[1]
        origin = Point(*((Point(*p0) + Point(*p1)) * 0.5))

        # xaxis along the contact edge, projected into the bisector plane.
        edge_dir = Vector(p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2])
        xaxis = edge_dir - zaxis * dot_vectors(edge_dir, zaxis)
        xaxis = xaxis.unitized()
        yaxis = zaxis.cross(xaxis)

        frame = Frame(origin, xaxis, yaxis)
        return cls(points=points, frame=frame, forces=forces, **kwargs)

    # ==========================================================================
    # Forces
    # ==========================================================================

    @property
    def forces(self) -> list[dict[str, float]]:
        return self._forces

    @forces.setter
    def forces(self, forces: list[dict[str, float]]) -> None:
        self._forces = forces

    @property
    def resultantpoint(self) -> Point:
        """Line of action through the contact: per-point normal-force-weighted centroid, falling back to the geometric midpoint when normal forces are absent or net to zero."""
        pts = [list(p) for p in self.points]
        if self._forces:
            fn_vals = [f.get("c_np", 0.0) - f.get("c_nn", 0.0) for f in self._forces]
            if abs(sum(fn_vals)) > 1e-12:
                return Point(*centroid_points_weighted(pts, fn_vals))
        return Point(*centroid_points_weighted(pts, [1] * len(pts)))

    @property
    def resultant(self) -> Optional[Vector]:
        """Resultant force, projected onto global XYZ, as a :class:`compas.geometry.Vector`."""
        if not self._forces:
            return None
        n = self.frame.zaxis
        t1 = self.frame.xaxis
        t2 = self.frame.yaxis
        total = Vector(0, 0, 0)
        for force in self._forces:
            fn = force.get("c_np", 0.0) - force.get("c_nn", 0.0)
            f1 = force.get("c_u", 0.0)
            f2 = force.get("c_v", 0.0)
            total += n * fn + t1 * f1 + t2 * f2
        return total

    @property
    def resultantforce(self) -> Optional[Line]:
        """Line of length ``|resultant|`` centered at the force-weighted contact point, oriented along the resultant force."""
        r = self.resultant
        if r is None or r.length == 0:
            return None
        half = r * 0.5
        center = self.resultantpoint
        return Line(center - half, center + half)

    def resultantline(self, scale: float = 1.0) -> Line:
        """Line ``|resultant|`` centered at the force-weighted contact point, oriented along the resultant force."""
        r = self.resultant
        if r is None or r.length == 0:
            return None
        half = r * 0.5 * scale
        center = self.resultantpoint
        return Line(center - half, center + half)


# =============================================================================


class FrictionContact(Contact):
    """Class representing an interaction between two elements through surface-to-surface contact.

    Parameters
    ----------
    forces : list[dict[Literal["c_np", "c_nn", "c_u", "c_v"], float]], optional
        The forces at the corners of the contact.

    Attributes
    ----------
    forces : list[dict[Literal["c_np", "c_nn", "c_u", "c_v"], float]]
        A dictionary of force components per interface point.
        Each dictionary contains the following items: ``{"c_np": ..., "c_nn": ...,  "c_u": ..., "c_v": ...}``.
    points2
    polygon2
    M0
    M1
    M2
    kern
    stressdistribution
    normalforces : list[:class:`compas.geometry.Line`]
        A list of lines representing the normal components of the contact forces at the corners of the interface.
        The length of each line is proportional to the magnitude of the corresponding force.
    compressionforces : list[:class:`compas.geometry.Line`]
        A list of lines representing the compression components of the normal contact forces
        at the corners of the interface.
        The length of each line is proportional to the magnitude of the corresponding force.
    compressiondata
    tensionforces : list[:class:`compas.geometry.Line`]
        A list of lines representing the tension components of the normal contact forces
        at the corners of the interface.
        The length of each line is proportional to the magnitude of the corresponding force.
    tensiondata
    frictionforces : list[:class:`compas.geometry.Line`]
        A list of lines representing the friction or tangential components of the contact forces
        at the corners of the interface.
        The length of each line is proportional to the magnitude of the corresponding force.
    frictiondata
    resultantforce : list[:class:`compas.geometry.Line`]
        A list with a single line representing the resultant of all the contact forces at the corners of the interface.
        The length of the line is proportional to the magnitude of the resultant force.
    resultantdata
    resultantpoint : :class:`compas.geometry.Point`
        The point of application of the resultant force on the interface.

    """

    @property
    def __data__(self) -> dict:
        data = super().__data__
        data["forces"] = self.forces
        return data

    @classmethod
    def __from_data__(cls, data: dict) -> "FrictionContact":
        if not data.get("points"):
            from compas.data import Data

            obj = object.__new__(cls)
            Data.__init__(obj, data.get("name"))
            obj._frame = data.get("frame")
            obj._size = data.get("size")
            obj._mesh = data.get("mesh")
            poly = Polygon.__new__(Polygon)
            poly._points = []
            poly._lines = []
            poly._vertices = []
            poly._faces = []
            obj._polygon = poly
            obj._points2 = None
            obj._polygon2 = None
            obj._forces = data.get("forces") or []
            obj._compressiondata = None
            obj._tensiondata = None
            obj._frictiondata = None
            obj._resultantdata = None
            return obj
        return super().__from_data__(data)

    def __init__(self, forces=None, **kwargs):
        super().__init__(**kwargs)

        self._points2 = None
        self._polygon2 = None
        self._forces = forces or []

        self._compressiondata = None
        self._tensiondata = None
        self._frictiondata = None
        self._resultantdata = None

    # =============================================================================
    # Structural
    # =============================================================================

    @property
    def forces(self) -> list[dict[str, float]]:
        return self._forces

    @forces.setter
    def forces(self, forces: list[dict[str, float]]) -> None:
        self._forces = forces

    @property
    def points2(self) -> list[Point]:
        if not self._points2:
            X = Transformation.from_frame_to_frame(self.frame, Frame.worldXY())
            self._points2 = [Point(*point) for point in transform_points(self.points, X)]
        return self._points2

    @property
    def polygon2(self) -> Polygon:
        if not self._polygon2:
            X = Transformation.from_frame_to_frame(self.frame, Frame.worldXY())
            self._polygon2 = self.polygon.transformed(X)
        return self._polygon2

    @property
    def M0(self) -> float:
        m0 = 0
        for a, b in pairwise(self.points2 + self.points2[:1]):
            d = b - a
            n = [d[1], -d[0], 0]  # type: ignore
            m0 += dot_vectors(a, n)
        return 0.5 * m0

    @property
    def M1(self) -> Point:
        m1 = Point(0, 0, 0)
        for a, b in pairwise(self.points2 + self.points2[:1]):
            d = b - a
            n = [d[1], -d[0], 0]  # type: ignore
            m0 = dot_vectors(a, n)
            m1 += (a + b) * m0
        return m1 / 6

    @property
    def M2(self) -> Annotated[list[Annotated[list[float], 3]], 3]:
        m2 = outer_product([0, 0, 0], [0, 0, 0])
        for a, b in pairwise(self.points2 + self.points2[:1]):
            d = b - a
            n = [d[1], -d[0], 0]  # type: ignore
            m0 = dot_vectors(a, n)
            aa = outer_product(a, a)
            ab = outer_product(a, b)
            ba = outer_product(b, a)
            bb = outer_product(b, b)
            m2 = sum_matrices(
                m2,
                scale_matrix(
                    sum_matrices(sum_matrices(aa, bb), scale_matrix(sum_matrices(ab, ba), 0.5)),
                    m0,
                ),
            )
        return scale_matrix(m2, 1 / 12.0)  # type: ignore

    @property
    def kern(self):
        raise NotImplementedError

    @property
    def stressdistribution(self):
        raise NotImplementedError

    @property
    def normalforces(self) -> list[Line]:
        lines = []
        if not self.forces:
            return lines
        frame = self.frame
        w = frame.zaxis
        for point, force in zip(self.points, self.forces):
            force = force["c_np"] - force["c_nn"]
            p1 = point + w * force * 0.5
            p2 = point - w * force * 0.5
            lines.append(Line(p1, p2))
        return lines

    @property
    def compressionforces(self) -> list[Line]:
        lines = []
        if not self.forces:
            return lines
        frame = self.frame
        w = frame.zaxis
        for point, force in zip(self.points, self.forces):
            force = force["c_np"] - force["c_nn"]
            if force > 0:
                p1 = point + w * force * 0.5
                p2 = point - w * force * 0.5
                lines.append(Line(p1, p2))
        return lines

    @property
    def compressiondata(self) -> list[list[float]]:
        if not self._compressiondata:
            self._compressiondata = []
            if self.forces:
                vector = list(self.frame.zaxis)
                for point, force in zip(self.points, self.forces):
                    force = force["c_np"] - force["c_nn"]
                    if force > 0:
                        self._compressiondata.append(list(point) + vector + [0.5 * force])
        return self._compressiondata

    @property
    def tensionforces(self) -> list[Line]:
        lines = []
        if not self.forces:
            return lines
        frame = self.frame
        w = frame.zaxis
        for point, force in zip(self.points, self.forces):
            force = force["c_np"] - force["c_nn"]
            if force < 0:
                p1 = point + w * force * 0.5
                p2 = point - w * force * 0.5
                lines.append(Line(p1, p2))
        return lines

    @property
    def tensiondata(self) -> list[list[float]]:
        if not self._tensiondata:
            self._tensiondata = []
            if self.forces:
                vector = list(self.frame.zaxis)
                for point, force in zip(self.points, self.forces):
                    force = force["c_np"] - force["c_nn"]
                    if force < 0:
                        self._tensiondata.append(list(point) + vector + [0.5 * force])
        return self._tensiondata

    @property
    def frictionforces(self) -> list[Line]:
        lines = []
        if not self.forces:
            return lines
        frame = self.frame
        u, v = frame.xaxis, frame.yaxis
        for point, force in zip(self.points, self.forces):
            ft_uv = (u * force["c_u"] + v * force["c_v"]) * 0.5
            p1 = point + ft_uv
            p2 = point - ft_uv
            lines.append(Line(p1, p2))
        return lines

    @property
    def frictiondata(self) -> list[list[float]]:
        if not self._frictiondata:
            self._frictiondata = []
            if self.forces:
                u, v = list(self.frame.xaxis), list(self.frame.yaxis)
                for point, force in zip(self.points, self.forces):
                    xyz = list(point)
                    self._frictiondata.append(xyz + u + v + [force["c_u"], force["c_v"]])
        return self._frictiondata

    @property
    def resultantpoint(self) -> Optional[Union[Point, list[float]]]:
        if not self.forces:
            return []
        normalcomponents = [f["c_np"] - f["c_nn"] for f in self.forces]
        if sum(normalcomponents):
            return Point(*centroid_points_weighted(self.points, normalcomponents))

    @property
    def resultantforce(self) -> list[Line]:
        if not self.forces:
            return []
        normalcomponents = [f["c_np"] - f["c_nn"] for f in self.forces]
        sum_n = sum(normalcomponents)
        sum_u = sum(f["c_u"] for f in self.forces)
        sum_v = sum(f["c_v"] for f in self.forces)
        if abs(sum_n) > 1e-12:
            position = Point(*centroid_points_weighted(self.points, normalcomponents))
        else:
            position = Point(*centroid_points_weighted(self.points, [1] * len(self.points)))
        frame = self.frame
        w, u, v = frame.zaxis, frame.xaxis, frame.yaxis
        forcevector = (w * sum_n + u * sum_u + v * sum_v) * 0.5
        p1 = position + forcevector
        p2 = position - forcevector
        return [Line(p1, p2)]

    @property
    def resultantdata(self) -> Optional[list[float]]:
        if not self._resultantdata:
            if self.forces:
                normalcomponents = [f["c_np"] - f["c_nn"] for f in self.forces]
                sum_n = sum(normalcomponents)
                sum_u = sum(f["c_u"] for f in self.forces)
                sum_v = sum(f["c_v"] for f in self.forces)
                position = centroid_points_weighted(self.points, normalcomponents)
                u, v, w = self.frame.xaxis, self.frame.yaxis, self.frame.zaxis
                forcevector = u * sum_u + v * sum_v + w * sum_n
                direction = list(forcevector.unitized())
                self._resultantdata = position + direction + [0.5 * forcevector.length]
        return self._resultantdata

    def resultantline(self, scale: float = 1.0) -> Line:
        if not self.forces:
            return None
        normalcomponents = [f["c_np"] - f["c_nn"] for f in self.forces]
        sum_n = sum(normalcomponents)
        sum_u = sum(f["c_u"] for f in self.forces)
        sum_v = sum(f["c_v"] for f in self.forces)
        frame = self.frame
        w, u, v = frame.zaxis, frame.xaxis, frame.yaxis
        forcevector = (w * sum_n + u * sum_u + v * sum_v) * 0.5
        if forcevector.length == 0:
            return None
        if sum_n:
            position = Point(*centroid_points_weighted(self.points, normalcomponents))
        else:
            position = Point(*centroid_points_weighted(self.points, [1] * len(self.points)))
        p1 = position + forcevector * scale
        p2 = position - forcevector * scale
        return Line(p1, p2)
