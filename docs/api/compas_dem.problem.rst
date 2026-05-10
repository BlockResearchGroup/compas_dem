********************************************************************************
compas_dem.problem
********************************************************************************

.. currentmodule:: compas_dem.problem

Defines the structural problem to be solved on a
:class:`~compas_dem.models.BlockModel`. A :class:`Problem` ties a block model
to its :class:`BoundaryConditions` — supports, applied loads, prescribed
displacements — and to a :class:`Solver` that captures the configuration of
the underlying numerical engine (LMGC90, CRA, or RBE). Once configured, a
problem is handed to a routine in :mod:`compas_dem.analysis` for execution.


Classes
=======

.. autosummary::
    :toctree: generated/
    :nosignatures:

    Problem
    BoundaryConditions
    Solver
