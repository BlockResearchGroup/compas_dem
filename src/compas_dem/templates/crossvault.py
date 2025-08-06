from numpy import array
from numpy import concatenate
from numpy import linspace
from numpy import ones
from numpy import zeros

from typing import List

import math

from compas.datastructures import Mesh
from compas_pattern.parametric import create_cross_form
from compas_pattern.parametric import create_fan_form

from .template import Template


def crossvault_ub_lb_update(x, y, thk, min_lb, xy_span=[[0.0, 10.0], [0.0, 10.0]], tol=1e-6):
    """Update upper and lower bounds of an crossvault based in the parameters

    Parameters
    ----------
    x : list
        x-coordinates of the points
    y : list
        y-coordinates of the points
    thk : float
        Thickness of the arch
    min_lb : float
        Parameter for lower bound in nodes in the boundary
    xy_span : [list[float], list[float]], optional
        xy-span of the shape, by default [[0.0, 10.0], [0.0, 10.0]]
    tol : float, optional
        Tolerance, by default 10e-6

    Returns
    -------
    ub : array
        Values of the upper bound in the points
    lb : array
        Values of the lower bound in the points
    """

    y1 = xy_span[1][1]
    y0 = xy_span[1][0]
    x1 = xy_span[0][1]
    x0 = xy_span[0][0]

    y1_ub = y1 + thk / 2
    y0_ub = y0 - thk / 2
    x1_ub = x1 + thk / 2
    x0_ub = x0 - thk / 2

    y1_lb = y1 - thk / 2
    y0_lb = y0 + thk / 2
    x1_lb = x1 - thk / 2
    x0_lb = x0 + thk / 2

    rx_ub = (x1_ub - x0_ub) / 2
    ry_ub = (y1_ub - y0_ub) / 2
    rx_lb = (x1_lb - x0_lb) / 2
    ry_lb = (y1_lb - y0_lb) / 2

    hc_ub = max(rx_ub, ry_ub)
    hc_lb = max(rx_lb, ry_lb)

    ub = ones((len(x), 1))
    lb = ones((len(x), 1)) * - min_lb

    for i in range(len(x)):
        xi, yi = x[i], y[i]
        xd_ub = x0_ub + (x1_ub - x0_ub) / (y1_ub - y0_ub) * (yi - y0_ub)
        yd_ub = y0_ub + (y1_ub - y0_ub) / (x1_ub - x0_ub) * (xi - x0_ub)
        hxd_ub = math.sqrt((rx_ub) ** 2 - ((xd_ub - x0_ub) - rx_ub) ** 2)
        hyd_ub = math.sqrt((ry_ub) ** 2 - ((yd_ub - y0_ub) - ry_ub) ** 2)

        intrados_null = False

        if (yi > y1_lb and (xi > x1_lb or xi < x0_lb)) or (yi < y0_lb and (xi > x1_lb or xi < x0_lb)):
            intrados_null = True
        else:
            yi_intra = yi
            xi_intra = xi
            if yi > y1_lb:
                yi_intra = y1_lb
            if yi < y0_lb:
                yi_intra = y0_lb
            elif xi > x1_lb:
                xi_intra = x1_lb
            elif xi < x0_lb:
                xi_intra = x0_lb

            xd_lb = x0_lb + (x1_lb - x0_lb) / (y1_lb - y0_lb) * (yi_intra - y0_lb)
            yd_lb = y0_lb + (y1_lb - y0_lb) / (x1_lb - x0_lb) * (xi_intra - x0_lb)
            hxd_lb = _sqrt(((rx_lb) ** 2 - ((xd_lb - x0_lb) - rx_lb) ** 2))
            hyd_lb = _sqrt(((ry_lb) ** 2 - ((yd_lb - y0_lb) - ry_lb) ** 2))

        if yi <= y0 + (y1 - y0) / (x1 - x0) * (xi - x0) + tol and yi >= y1 - (y1 - y0) / (x1 - x0) * (xi - x0) - tol:  # Q1
            ub[i] = hc_ub * (hxd_ub + math.sqrt((ry_ub) ** 2 - ((yi - y0_ub) - ry_ub) ** 2)) / (rx_ub + ry_ub)
            if not intrados_null:
                lb[i] = hc_lb * (hxd_lb + math.sqrt((ry_lb) ** 2 - ((yi_intra - y0_lb) - ry_lb) ** 2)) / (rx_lb + ry_lb)
        elif yi >= y0 + (y1 - y0) / (x1 - x0) * (xi - x0) - tol and yi >= y1 - (y1 - y0) / (x1 - x0) * (xi - x0) - tol:  # Q3
            ub[i] = hc_ub * (hyd_ub + math.sqrt((rx_ub) ** 2 - ((xi - x0_ub) - rx_ub) ** 2)) / (rx_ub + ry_ub)
            if not intrados_null:
                lb[i] = hc_lb * (hyd_lb + math.sqrt((rx_lb) ** 2 - ((xi_intra - x0_lb) - rx_lb) ** 2)) / (rx_lb + ry_lb)
        elif yi >= y0 + (y1 - y0) / (x1 - x0) * (xi - x0) - tol and yi <= y1 - (y1 - y0) / (x1 - x0) * (xi - x0) + tol:  # Q2
            ub[i] = hc_ub * (hxd_ub + math.sqrt((ry_ub) ** 2 - ((yi - y0_ub) - ry_ub) ** 2)) / (rx_ub + ry_ub)
            if not intrados_null:
                lb[i] = hc_lb * (hxd_lb + math.sqrt((ry_lb) ** 2 - ((yi_intra - y0_lb) - ry_lb) ** 2)) / (rx_lb + ry_lb)
        elif yi <= y0 + (y1 - y0) / (x1 - x0) * (xi - x0) + tol and yi <= y1 - (y1 - y0) / (x1 - x0) * (xi - x0) + tol:  # Q4
            ub[i] = hc_ub * (hyd_ub + math.sqrt((rx_ub) ** 2 - ((xi - x0_ub) - rx_ub) ** 2)) / (rx_ub + ry_ub)
            if not intrados_null:
                lb[i] = hc_lb * (hyd_lb + math.sqrt((rx_lb) ** 2 - ((xi_intra - x0_lb) - rx_lb) ** 2)) / (rx_lb + ry_lb)
        else:
            print("Error Q. (x,y) = ({0},{1})".format(xi, yi))

    return ub, lb


def crossvault_dub_dlb(x, y, thk, min_lb, xy_span=[[0.0, 10.0], [0.0, 10.0]], tol=1e-6):
    """Computes the sensitivities of upper and lower bounds in the x, y coordinates and thickness specified.

    Parameters
    ----------
    x : list
        x-coordinates of the points
    y : list
        y-coordinates of the points
    thk : float
        Thickness of the arch
    min_lb : float
        Parameter for lower bound in nodes in the boundary
    xy_span : [list[float], list[float]], optional
        xy-span of the shape, by default [[0.0, 10.0], [0.0, 10.0]]
    tol : float, optional
        Tolerance, by default 10e-6

    Returns
    -------
    dub : array
        Values of the sensitivities for the upper bound in the points
    dlb : array
        Values of the sensitivities for the lower bound in the points
    """

    y1 = xy_span[1][1]
    y0 = xy_span[1][0]
    x1 = xy_span[0][1]
    x0 = xy_span[0][0]

    y1_ub = y1 + thk / 2
    y0_ub = y0 - thk / 2
    x1_ub = x1 + thk / 2
    x0_ub = x0 - thk / 2

    y1_lb = y1 - thk / 2
    y0_lb = y0 + thk / 2
    x1_lb = x1 - thk / 2
    x0_lb = x0 + thk / 2

    rx_ub = (x1_ub - x0_ub) / 2
    ry_ub = (y1_ub - y0_ub) / 2
    rx_lb = (x1_lb - x0_lb) / 2
    ry_lb = (y1_lb - y0_lb) / 2

    hc_ub = max(rx_ub, ry_ub)
    hc_lb = max(rx_lb, ry_lb)

    ub = ones((len(x), 1))
    lb = ones((len(x), 1)) * - min_lb
    dub = zeros((len(x), 1))  # dzub / dt
    dlb = zeros((len(x), 1))  # dzlb / dt

    dubdx = zeros((len(x), len(x)))
    dubdy = zeros((len(x), len(x)))
    dlbdx = zeros((len(x), len(x)))
    dlbdy = zeros((len(x), len(x)))

    yc = ry_ub + y0_ub  # Only works for square
    xc = rx_ub + x0_ub

    for i in range(len(x)):
        xi, yi = x[i], y[i]
        xd_ub = x0_ub + (x1_ub - x0_ub) / (y1_ub - y0_ub) * (yi - y0_ub)
        yd_ub = y0_ub + (y1_ub - y0_ub) / (x1_ub - x0_ub) * (xi - x0_ub)
        hxd_ub = math.sqrt((rx_ub) ** 2 - ((xd_ub - x0_ub) - rx_ub) ** 2)
        hyd_ub = math.sqrt((ry_ub) ** 2 - ((yd_ub - y0_ub) - ry_ub) ** 2)

        intrados_null = False

        if (yi > y1_lb and (xi > x1_lb or xi < x0_lb)) or (yi < y0_lb and (xi > x1_lb or xi < x0_lb)):
            intrados_null = True
        else:
            yi_intra = yi
            xi_intra = xi
            if yi > y1_lb:
                yi_intra = y1_lb
            elif yi < y0_lb:
                yi_intra = y0_lb
            if xi > x1_lb:
                xi_intra = x1_lb
            elif xi < x0_lb:
                xi_intra = x0_lb

            xd_lb = x0_lb + (x1_lb - x0_lb) / (y1_lb - y0_lb) * (yi_intra - y0_lb)
            yd_lb = y0_lb + (y1_lb - y0_lb) / (x1_lb - x0_lb) * (xi_intra - x0_lb)
            hxd_lb = _sqrt(((rx_lb) ** 2 - ((xd_lb - x0_lb) - rx_lb) ** 2))
            hyd_lb = _sqrt(((ry_lb) ** 2 - ((yd_lb - y0_lb) - ry_lb) ** 2))

        if yi <= y0 + (y1 - y0) / (x1 - x0) * (xi - x0) + tol and yi >= y1 - (y1 - y0) / (x1 - x0) * (xi - x0) - tol:  # Q1
            ub[i] = hc_ub * (hxd_ub + math.sqrt((ry_ub) ** 2 - ((yi - y0_ub) - ry_ub) ** 2)) / (rx_ub + ry_ub)
            dub[i] = 1 / 2 * ry_ub / ub[i] * hc_ub / ((rx_ub + ry_ub) / 2)
            # dubdx[i, i] += 0.0
            dubdy[i, i] += -(yi - yc) / ub[i]
            if not intrados_null:
                lb[i] = hc_lb * (hxd_lb + math.sqrt((ry_lb) ** 2 - ((yi_intra - y0_lb) - ry_lb) ** 2)) / (rx_lb + ry_lb)
                dlb[i] = -1 / 2 * ry_lb / lb[i] * hc_lb / ((rx_lb + ry_lb) / 2)
                # dlbdx[i, i] += 0.0
                dlbdy[i, i] += -(yi - yc) / lb[i]
        if yi >= y0 + (y1 - y0) / (x1 - x0) * (xi - x0) - tol and yi >= y1 - (y1 - y0) / (x1 - x0) * (xi - x0) - tol:  # Q3
            ub[i] = hc_ub * (hyd_ub + math.sqrt((rx_ub) ** 2 - ((xi - x0_ub) - rx_ub) ** 2)) / (rx_ub + ry_ub)
            dub[i] = 1 / 2 * rx_ub / ub[i] * hc_ub / ((rx_ub + ry_ub) / 2)
            # dubdy[i, i] += 0.0
            dubdx[i, i] += -(xi - xc) / ub[i]
            if not intrados_null:
                lb[i] = hc_lb * (hyd_lb + math.sqrt((rx_lb) ** 2 - ((xi_intra - x0_lb) - rx_lb) ** 2)) / (rx_lb + ry_lb)
                dlb[i] = -1 / 2 * rx_lb / lb[i] * hc_lb / ((rx_lb + ry_lb) / 2)
                # dlbdy[i, i] += 0.0
                dlbdx[i, i] += -(xi - xc) / lb[i]
        if yi >= y0 + (y1 - y0) / (x1 - x0) * (xi - x0) - tol and yi <= y1 - (y1 - y0) / (x1 - x0) * (xi - x0) + tol:  # Q2
            ub[i] = hc_ub * (hxd_ub + math.sqrt((ry_ub) ** 2 - ((yi - y0_ub) - ry_ub) ** 2)) / (rx_ub + ry_ub)
            dub[i] = 1 / 2 * ry_ub / ub[i] * hc_ub / ((rx_ub + ry_ub) / 2)
            # dubdx[i, i] += 0.0
            dubdy[i, i] += -(yi - yc) / ub[i]
            if not intrados_null:
                lb[i] = hc_lb * (hxd_lb + math.sqrt((ry_lb) ** 2 - ((yi_intra - y0_lb) - ry_lb) ** 2)) / (rx_lb + ry_lb)
                dlb[i] = -1 / 2 * ry_lb / lb[i] * hc_lb / ((rx_lb + ry_lb) / 2)
                # dlbdx[i, i] += 0.0
                dlbdy[i, i] += -(yi - yc) / lb[i]
        if yi <= y0 + (y1 - y0) / (x1 - x0) * (xi - x0) + tol and yi <= y1 - (y1 - y0) / (x1 - x0) * (xi - x0) + tol:  # Q4
            ub[i] = hc_ub * (hyd_ub + math.sqrt((rx_ub) ** 2 - ((xi - x0_ub) - rx_ub) ** 2)) / (rx_ub + ry_ub)
            dub[i] = 1 / 2 * rx_ub / ub[i] * hc_ub / ((rx_ub + ry_ub) / 2)
            # dubdy[i, i] += 0.0
            dubdx[i, i] += -(xi - xc) / ub[i]
            if not intrados_null:
                lb[i] = hc_lb * (hyd_lb + math.sqrt((rx_lb) ** 2 - ((xi_intra - x0_lb) - rx_lb) ** 2)) / (rx_lb + ry_lb)
                dlb[i] = -1 / 2 * rx_lb / lb[i] * hc_lb / ((rx_lb + ry_lb) / 2)
                # dlbdy[i, i] += 0.0
                dlbdx[i, i] += -(xi - xc) / lb[i]
        # else:
        #     print('Error Q. (x,y) = ({0},{1})'.format(xi, yi))

    return dub, dlb, dubdx, dubdy, dlbdx, dlbdy


def crossvault_middle_update(x, y, min_lb, xy_span=[[0.0, 10.0], [0.0, 10.0]], tol=1e-6):
    """Update middle of a crossvault based in the parameters

    Parameters
    ----------
    x : list
        x-coordinates of the points
    y : list
        y-coordinates of the points
    thk : float
        Thickness of the arch
    min_lb : float
        Parameter for lower bound in nodes in the boundary
    xy_span : [list[float], list[float]], optional
        xy-span of the shape, by default [[0.0, 10.0], [0.0, 10.0]]
    tol : float, optional
        Tolerance, by default 10e-6

    Returns
    -------
    z : array
        Values of the middle surface in the points
    """

    y1 = xy_span[1][1]
    y0 = xy_span[1][0]
    x1 = xy_span[0][1]
    x0 = xy_span[0][0]

    rx = (x1 - x0) / 2
    ry = (y1 - y0) / 2
    hc = max(rx, ry)

    z = zeros((len(x), 1))

    for i in range(len(x)):
        xi, yi = x[i], y[i]
        if yi > y1:
            yi = y1
        if yi < y0:
            yi = y0
        if xi > x1:
            xi = x1
        if xi < x0:
            xi = x0
        xd = x0 + (x1 - x0) / (y1 - y0) * (yi - y0)
        yd = y0 + (y1 - y0) / (x1 - x0) * (xi - x0)
        hxd = math.sqrt(abs((rx) ** 2 - ((xd - x0) - rx) ** 2))
        hyd = math.sqrt(abs((ry) ** 2 - ((yd - y0) - ry) ** 2))
        if yi <= y0 + (y1 - y0) / (x1 - x0) * (xi - x0) + tol and yi >= y1 - (y1 - y0) / (x1 - x0) * (xi - x0) - tol:  # Q1
            z[i] = hc * (hxd + math.sqrt((ry) ** 2 - ((yi - y0) - ry) ** 2)) / (rx + ry)
        elif yi >= y0 + (y1 - y0) / (x1 - x0) * (xi - x0) - tol and yi >= y1 - (y1 - y0) / (x1 - x0) * (xi - x0) - tol:  # Q3
            z[i] = hc * (hyd + math.sqrt((rx) ** 2 - ((xi - x0) - rx) ** 2)) / (rx + ry)
        elif yi >= y0 + (y1 - y0) / (x1 - x0) * (xi - x0) - tol and yi <= y1 - (y1 - y0) / (x1 - x0) * (xi - x0) + tol:  # Q2
            z[i] = hc * (hxd + math.sqrt((ry) ** 2 - ((yi - y0) - ry) ** 2)) / (rx + ry)
        elif yi <= y0 + (y1 - y0) / (x1 - x0) * (xi - x0) + tol and yi <= y1 - (y1 - y0) / (x1 - x0) * (xi - x0) + tol:  # Q4
            z[i] = hc * (hyd + math.sqrt((rx) ** 2 - ((xi - x0) - rx) ** 2)) / (rx + ry)
        else:
            print("Vertex did not belong to any Q. (x,y) = ({0},{1})".format(xi, yi))
            z[i] = - min_lb

    return z

def _sqrt(x):
    try:
        sqrt_x = math.sqrt(x)
    except BaseException:
        if x > -10e4:
            sqrt_x = math.sqrt(abs(x))
        else:
            sqrt_x = 0.0
            print("Problems to sqrt: ", x)
    return sqrt_x


class CrossVaultTemplate(Template):
    """Create voussoirs for a spherical dome geometry with given rise and span."""

    def __init__(
        self,
        xy_span : List[List[float]] = [[0.0, 10.0], [0.0, 10.0]],
        thk : float = 0.50,
        min_lb : float = 0.0,
        n : int = 100
    ):
        super().__init__()
        self.xy_span = xy_span
        self.thk = thk
        self.min_lb = min_lb
        self.n = n

    def blocks(self):
        """Compute the blocks.

        Returns
        -------
        list
            A list of blocks defined as simple meshes.

        Notes
        -----
        This method is used by the ``from_geometry`` constructor of the assembly data structure
        to create an assembly "from geometry".

        """

        return NotImplementedError

    def intrados_and_extrados(self):
        """Helper to create meshes to define upper and lower bounds of 2D arch .

        Returns
        -------
        intrados : :class:`~compas.datastructures.Mesh`
            A Mesh for the intrados of the pattern
        extrados : :class:`~compas.datastructures.Mesh`
            A Mesh for the extrados of the pattern
        middle : :class:`~compas.datastructures.Mesh`
            A Mesh for the middle of the pattern

        """

        if isinstance(self.n, int):
            discretisation = [self.n, self.n]

        [x0, x1], [y0, y1] = self.xy_span

        density_x = discretisation[0]  # type: ignore
        density_y = discretisation[1]  # type: ignore
        x = linspace(x0, x1, num=density_x + 1, endpoint=True)  # arange(x0, x1 + dx/density_x, dx/density_x)
        y = linspace(y0, y1, num=density_y + 1, endpoint=True)  # arange(y0, y1 + dy/density_y, dy/density_y)

        base_topology : Mesh = create_cross_form(self.xy_span, self.n)
        xyz0, faces_i = base_topology.to_vertices_and_faces()
        xi, yi, _ = array(xyz0).transpose()

        zt = crossvault_middle_update(xi, yi, self.min_lb, xy_span=self.xy_span, tol=1e-6)
        xyzt = array([xi, yi, zt.flatten()]).transpose()
        middle = Mesh.from_vertices_and_faces(xyzt, faces_i)

        zub, zlb = crossvault_ub_lb_update(xi, yi, self.thk, self.min_lb, xy_span=self.xy_span, tol=1e-6)
        xyzub = array([xi, yi, zub.flatten()]).transpose()
        xyzlb = array([xi, yi, zlb.flatten()]).transpose()

        extrados = Mesh.from_vertices_and_faces(xyzub, faces_i)
        intrados = Mesh.from_vertices_and_faces(xyzlb, faces_i)

        return intrados, extrados, middle
