********************************************************************************
compas_dem.problem
********************************************************************************

.. currentmodule:: compas_dem.problem

Defines the structural problem to be solved on a
:class:`~compas_dem.models.BlockModel`. A :class:`Problem` ties a block model
to its boundary conditions — applied loads and prescribed displacements,
grouped into one or more :class:`BoundaryConditionGroup` — and to a
:class:`Solver` that captures the configuration of the underlying numerical
engine (LMGC90, CRA, RBE, PRD or BLA). Supports are not part of the problem:
they live on the model, as ``block.is_support``.

Each ``add_*`` call on a group builds the matching :class:`BoundaryCondition`
subclass, so a group holds objects rather than plain dictionaries. Once
configured, :meth:`Problem.solve` dispatches to the routine in
:mod:`compas_dem.analysis` that matches the chosen solver, and returns a
:class:`Results`.


Classes
=======

.. autosummary::
    :toctree: generated/
    :nosignatures:

    Problem
    BoundaryConditionGroup
    BoundaryCondition
    Load
    PointLoad
    SurfaceLoad
    BodyForce
    Gravity
    Displacement
    Translation
    Rotation
    Results
    Solver
