********************************************************************************
compas_dem.interactions
********************************************************************************

.. currentmodule:: compas_dem.interactions

Contact and joint descriptions that express how blocks meet each other. A
contact captures the geometry of the interface between two blocks —
:class:`FrictionContact` for surface-to-surface, :class:`EdgeContact` for
edge-to-edge, :class:`VertexContact` for point contact — while a contact
model such as :class:`MohrCoulomb` parametrises the constitutive law that
governs the forces transmitted across that interface. :class:`JointModel`
and :class:`ContactProperties` group these into reusable configurations
that can be assigned to whole groups of contacts at once.


Contact Classes
===============

.. autosummary::
    :toctree: generated/
    :nosignatures:

    FrictionContact
    EdgeContact
    VertexContact


Contact Models
==============

.. autosummary::
    :toctree: generated/
    :nosignatures:

    ContactModel
    MohrCoulomb


Properties and Joints
=====================

.. autosummary::
    :toctree: generated/
    :nosignatures:

    ContactProperties
    JointModel
