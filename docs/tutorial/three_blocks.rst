********************************************************************************
Three Blocks
********************************************************************************

A minimal, end-to-end ``compas_dem`` workflow built around the smallest
non-trivial DEM problem: two base blocks side by side, with a third block
resting on top spanning the gap between them. The whole assembly sits on a
fixed base plate.

The tutorial is split into three pages, each focussing on a single stage
and serialising its result to JSON so the next page can pick it up:

1. :doc:`three_blocks/01_model` — assemble the geometry, build a
   :class:`~compas_dem.models.BlockModel`, compute contacts, and assign
   material.
2. :doc:`three_blocks/02_problem` — wrap the model in a
   :class:`~compas_dem.problem.Problem`, declare boundary conditions, and
   pick a contact model.
3. :doc:`three_blocks/03_analysis` — run the analysis with LMGC90 and CRA,
   inspect the contact forces, and visualise the deformed model.

.. toctree::
    :maxdepth: 1
    :caption: Contents

    three_blocks/01_model
    three_blocks/02_problem
    three_blocks/03_analysis
