********************************************************************************
Geometry and Block Model
********************************************************************************

.. rst-class:: lead

The first step of every ``compas_dem`` workflow is to build a
:class:`~compas_dem.models.BlockModel`. This page walks through the one of
the simplest possible models. Three rectangular blocks resting on a base plate.
Data is serialised to JSON so it can be picked up by the next stage of
the tutorial.


Define the geometry
===================

The geometry of every block is just a :class:`compas.geometry.Box`. We make
two base blocks separated by a small gap, a single top block centred on the
gap, and a thin base plate underneath.

.. code-block:: python

    import compas.geometry as cg

    block_w = 1.0
    block_h = 1.0
    gap = 0.1
    total_w = 2 * block_w + gap

    Pl = cg.Box.from_corner_corner_height([0, 0, -0.1], [total_w, block_w, -0.1], 0.1)
    base_left = cg.Box.from_corner_corner_height([0, 0, 0], [block_w, block_w, 0], block_h)
    base_right = cg.Box.from_corner_corner_height([block_w + gap, 0, 0], [total_w, block_w, 0], block_h)
    top_x = (total_w - block_w) / 2
    top = cg.Box.from_corner_corner_height([top_x, 0, block_h], [top_x + block_w, block_w, block_h], block_h)

    blocks = [Pl, base_left, base_right, top]

.. figure:: /_images/three_blocks_geometry_0.png
   :align: center
   :width: 50%

Build the block model
=====================

:class:`~compas_dem.models.BlockModel` provides the ``from_boxes`` constructor
which wraps each box in a :class:`~compas_dem.elements.Block` and registers
them with the model.

.. code-block:: python

    from compas_dem.models import BlockModel

    model = BlockModel.from_boxes(blocks)


Compute contacts
==================================

``compute_contacts`` analyses the model's geometry and creates a
:class:`~compas_dem.interactions.FrictionContact` for every pair of blocks
that share an interface.

.. code-block:: python

    model.compute_contacts()

.. figure:: /_images/three_blocks_geometry_1.png
    :align: center
    :width: 50%
.. figure:: /_images/three_blocks_geometry_3.png
    :align: center
    :width: 50%

Add supports
============
``is_support`` is a boolean attribute of :class:`~compas_dem.elements.Block` that marks it as a support. 
Here we mark anything below the ground level as a support.

.. code-block:: python

    for block in model.elements():
        if block.point.z < 0.1:
            block.is_support = True

.. figure:: /_images/three_blocks_geometry_2.png
   :align: center
   :width: 50%
   
Assign material
===============

Materials carry the constitutive parameters consumed by the solvers. Here
we use the predefined limestone profile from :mod:`compas_dem.material` and
assign it to every element.

.. code-block:: python

    from compas_dem.material import Stone

    limestone = Stone.from_predefined_material("LimeStone")
    limestone.density = 2000

    model.add_material(limestone)
    model.assign_material(limestone, elements=list(model.elements()))


Serialise the model
===================

The block model is COMPAS-serialisable, so we can dump it to JSON. The next
page picks up exactly this file as the starting point for problem setup.

.. code-block:: python

    import os
    import compas

    HERE = os.path.dirname(__file__)
    compas.json_dump(model, os.path.join(HERE, "DEM_model.json"))

The complete script is available at
:download:`100_init.py <100_init.py>`.
