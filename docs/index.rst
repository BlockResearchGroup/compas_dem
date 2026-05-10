********************************************************************************
compas_dem
********************************************************************************

.. rst-class:: lead

Modeling and assessment of discrete block assemblies

.. .. figure:: /_images/compas_dem.png
     :figclass: figure
     :class: figure-img img-fluid


About
=====

``compas_dem`` is a COMPAS-based toolkit for building, analysing, and
visualising discrete element models of block assemblies. 

It provides:

- A data structure for assembling blocks and computing contacts

- Parametric templates for common typologies like arches, vaults, domes and walls.

- Library of contact laws to describe block interactions

- Tools for setting up problems, running solvers, and inspecting results.

- An extensible framework for defining new block types, contact laws, and solver bindings.


Where to start
==============

- **New here?** Start with :doc:`installation`, then walk through the
  :doc:`tutorial` to build your first block model end-to-end.
- **Looking for a worked example?** The :doc:`examples` cover canonical
  typologies — arches, domes, barrel and cross vaults, walls — with
  ready-to-run scripts.
- **Already building?** Jump to the :doc:`api` for the full reference of
  classes, functions, and solver bindings.


Table of Contents
=================

.. toctree::
   :maxdepth: 3
   :titlesonly:

   Introduction <self>
   installation
   tutorial
   examples
   api
   license


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
