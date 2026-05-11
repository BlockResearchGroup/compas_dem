********************************************************************************
compas_dem.models
********************************************************************************

.. currentmodule:: compas_dem.models

The data structure that ties everything together. :class:`BlockModel` is a
specialised COMPAS ``Model`` that holds the blocks, their interactions, and
the bookkeeping that lets ``compas_dem`` compute contacts, query topology,
and feed an assembly to a solver. It is the central object passed around
the rest of the package — built from a :class:`~compas_dem.templates.Template`
or constructed directly from input geometry, then enriched with materials,
contacts, and boundary conditions.


Classes
=======

.. autosummary::
    :toctree: generated/
    :nosignatures:

    BlockModel
