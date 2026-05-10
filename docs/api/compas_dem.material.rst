********************************************************************************
compas_dem.material
********************************************************************************

.. currentmodule:: compas_dem.material

Material models attached to the blocks of a :class:`~compas_dem.models.BlockModel`. 
The materials carry the constitutive parameters — strength, stiffness, density —
which can be accessed by solvers when computing self-weight, contact forces, 
failure criteria or other computations. :class:`Stone` is the generic masonry 
material; new materials can be added by subclassing the COMPAS ``Material`` interface.


Classes
=======

.. autosummary::
    :toctree: generated/
    :nosignatures:

    Stone
