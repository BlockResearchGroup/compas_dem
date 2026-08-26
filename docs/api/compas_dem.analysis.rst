********************************************************************************
compas_dem.analysis
********************************************************************************

.. currentmodule:: compas_dem.analysis

Bindings to the numerical engines that actually solve a
:class:`~compas_dem.problem.Problem`. Each routine takes a configured problem
and a block model, and returns a :class:`~compas_dem.problem.Results`:

- :func:`lmgc90_solve` — dynamic relaxation through the LMGC90 contact
  dynamics library.
- :func:`cra_solve` — coupled rigid-block analysis, suitable for limit-state
  checks.
- :func:`rbe_solve` — rigid-body equilibrium, the lightest-weight option,
  for quick stability assessments.

``prd_solve`` (piecewise rigid displacement) and ``bla_solve`` (block limit
analysis) round out the set, but their backends are not part of the
documentation environment and so are not listed below.

These routines are optional — they are only importable if the corresponding
backend is installed (see ``requirements-analysis.txt``). Rather than calling
them directly, configure a solver on the problem with
:meth:`~compas_dem.problem.Problem.set_solver` and call
:meth:`~compas_dem.problem.Problem.solve`, which dispatches to the right one.


Functions
=========

.. autosummary::
    :toctree: generated/
    :nosignatures:

    lmgc90_solve
    cra_solve
    rbe_solve
