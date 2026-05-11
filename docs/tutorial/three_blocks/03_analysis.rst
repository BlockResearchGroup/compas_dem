********************************************************************************
Analysis and Visualisation
********************************************************************************

.. rst-class:: lead

With a fully configured :class:`~compas_dem.problem.Problem` we can hand it
off to a solver. ``compas_dem`` ships with bindings for three engines:

- **LMGC90** Discrete Element Analysis
- **CRA** - Coubpled-Rigid Body Analysis
- **RBE** - Rigid-Body Equilibrium

All reachable through the same :class:`~compas_dem.problem.Solver` API.


Load the problem
================

We start by deserialising the problem from the previous page.

.. code-block:: python

    import os
    import compas

    HERE = os.path.dirname(__file__)
    problem = compas.json_load(os.path.join(HERE, "DEM_problem.json"))


Solve with LMGC90
=================

LMGC90 runs a discrete element simulation through ``n_steps`` time
increments of size ``dt``. Calling :meth:`~compas_dem.problem.Problem.solve`
with the configured solver writes the results back onto ``problem.model``
in place — block transformations on the graph nodes, contact forces on the
graph edges.

.. code-block:: python

    from compas_dem.problem import Solver

    lmgc90 = Solver.LMGC90(n_steps=100, dt=0.001)
    problem.solve(lmgc90)

    compas.json_dump(problem, os.path.join(HERE, "DEM_results.json"))


Solve with CRA
==============

For a static limit-state check, the CRA solver is a better fit. It uses a
penalty formulation to compute admissible contact forces under self-weight
and applied loads. The interface is identical, only the solver
configuration was swapped.

.. code-block:: python

    cra = Solver.CRA(verbose=True)
    problem.solve(cra)

    compas.json_dump(problem, os.path.join(HERE, "DEM_results.json"))

.. note::

   Both solvers serialise their results to the same JSON file. Run the
   solver of interest, then move on to the visualisation step below.


Inspect the results
===================

The solver writes per-block transformations on the model graph's nodes and
per-contact forces on its edges. We can iterate through them directly.

.. code-block:: python

    problem = compas.json_load(os.path.join(HERE, "DEM_results.json"))

    graph = problem.model.graph

    for node in graph.nodes():
        block_transformation = graph.node_attribute(node, "transformation")

    for edge in graph.edges():
        gap = graph.edge_attribute(edge, "gap")
        magnitude = graph.edge_attribute(edge, "force_magnitude")
        print(f"Edge {edge} gap: {gap}, force magnitude: {magnitude}")


Visualise the results
=====================

:class:`~compas_dem.viewer.DEMViewer` renders the deformed model, the
contact polygons, and the resultant force vectors. The ``scale`` argument
amplifies the displacements so they are visible in static configurations.

.. code-block:: python

    from compas_dem.viewer import DEMViewer

    viewer = DEMViewer(problem.model)
    viewer.add_solution(scale=0.5)
    viewer.show()


.. figure:: /_images/three_blocks_results_0.png
   :align: center
   :width: 80%

.. note::
    Inside the viewer panel, you can access each force line's vector (in global coordinate system) and magnitude.



The complete scripts are available at
:download:`300_SW_Analysis.py <300_SW_Analysis.py>` (LMGC90),
:download:`300_SW_Analysis_CRA.py <300_SW_Analysis_CRA.py>` (CRA), and
:download:`301_SW_Viz.py <301_SW_Viz.py>` (visualisation).
