********************************************************************************
compas_dem.analysis
********************************************************************************

.. currentmodule:: compas_dem.analysis

Bindings to the numerical engines that actually solve a
:class:`~compas_dem.problem.Problem`. Each routine takes a configured problem
and writes the results back onto its block model:

- :func:`lmgc90_solve` — dynamic relaxation through the LMGC90 contact
  dynamics library.
- :func:`cra_penalty_solve` — coupled rigid-block analysis with a penalty
  formulation, suitable for limit-state checks.
- :func:`rbe_solve` — rigid-body equilibrium, the lightest-weight option,
  for quick stability assessments.

These routines are optional — they are only importable if the corresponding
backend is installed (see ``requirements-analysis.txt``).


Functions
=========

.. autosummary::
    :toctree: generated/
    :nosignatures:

    lmgc90_solve
    cra_penalty_solve
    rbe_solve
