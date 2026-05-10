********************************************************************************
Problem Setup
********************************************************************************

.. rst-class:: lead

A :class:`~compas_dem.models.BlockModel` describes the geometry and topology
of an assembly, but says nothing yet about what we want to compute. That is
the job of :class:`~compas_dem.problem.Problem` — it ties a model to its
boundary conditions and contact properties so a solver can take it through.


Load the model
==============

We pick up the JSON dumped on the previous page and reconstruct the model.
COMPAS handles the serialisation transparently — what comes back is the
same :class:`~compas_dem.models.BlockModel` instance with all blocks,
contacts, and material assignments intact.

.. code-block:: python

    import os
    import compas

    HERE = os.path.dirname(__file__)
    model = compas.json_load(os.path.join(HERE, "DEM_model.json"))


Create the problem
==================

A :class:`~compas_dem.problem.Problem` wraps the model and exposes methods
for adding boundary conditions and configuring the contact behaviour.

.. code-block:: python

    from compas_dem.problem import Problem

    problem = Problem(model)


Boundary conditions
===================

In the previous step we marked the base plate as a support. ``Problem``
exposes :meth:`~compas_dem.problem.Problem.add_supports_from_model` to
promote those flags into proper boundary conditions on the problem.

.. code-block:: python

    problem.add_supports_from_model()


Contact properties
==================

Contact behaviour is governed by a :class:`~compas_dem.interactions.ContactModel`.
Here we use a Mohr–Coulomb friction model with a friction coefficient of
``0.5`` — a typical value for limestone-on-limestone interfaces.

.. code-block:: python

    problem.add_contact_model("MohrCoulomb", mu=0.5)


Serialise the problem
=====================

Just like the model on the previous page, the problem is fully
serialisable. The next page loads exactly this file and runs the analysis.

.. code-block:: python

    compas.json_dump(problem, os.path.join(HERE, "DEM_problem.json"))


Inspect the setup
=================

Before solving, it is useful to view the model with supports and load
arrows in place. :class:`~compas_dem.viewer.DEMViewer` renders the
problem interactively.

.. code-block:: python

    from compas_dem.viewer import DEMViewer

    viewer = DEMViewer(problem.model)
    viewer.setup()
    viewer.show()

The complete script is available at
:download:`200_SW_Problem.py <200_SW_Problem.py>`.
