from typing import Annotated

from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Point
from compas.geometry import Polygon
from compas.geometry import Transformation
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

    def __init__(self, forces=None, **kwargs):
        super().__init__(**kwargs)

        self._points2 = None
        self._polygon2 = None
        self._forces = forces

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
            n = [d[1], -d[0], 0]
            m0 += dot_vectors(a, n)
        return 0.5 * m0

    @property
    def M1(self) -> Point:
        m1 = Point(0, 0, 0)
        for a, b in pairwise(self.points2 + self.points2[:1]):
            d = b - a
            n = [d[1], -d[0], 0]
            m0 = dot_vectors(a, n)
            m1 += (a + b) * m0
        return m1 / 6

    @property
    def M2(self) -> Annotated[list[Annotated[list[float], 3]], 3]:
        m2 = outer_product([0, 0, 0], [0, 0, 0])
        for a, b in pairwise(self.points2 + self.points2[:1]):
            d = b - a
            n = [d[1], -d[0], 0]
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
        return scale_matrix(m2, 1 / 12.0)

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
    def resultantpoint(self) -> list[float]:
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
        position = Point(*centroid_points_weighted(self.points, normalcomponents))
        frame = self.frame
        w, u, v = frame.zaxis, frame.xaxis, frame.yaxis
        forcevector = (w * sum_n + u * sum_u + v * sum_v) * 0.5
        p1 = position + forcevector
        p2 = position - forcevector
        return [Line(p1, p2)]

    @property
    def resultantdata(self) -> list[float]:
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
