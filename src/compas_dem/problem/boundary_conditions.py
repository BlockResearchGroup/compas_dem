"""Backwards-compatibility shim.

``BoundaryConditions`` was renamed to :class:`~compas_dem.problem.loadcase.LoadCase`.
This module re-exports the class under both names so that existing imports
(``from compas_dem.problem.boundary_conditions import BoundaryConditions``) keep
working. New code should import :class:`LoadCase` from ``compas_dem.problem``.
"""

from compas_dem.problem.loadcase import LoadCase

BoundaryConditions = LoadCase

__all__ = ["BoundaryConditions", "LoadCase"]
