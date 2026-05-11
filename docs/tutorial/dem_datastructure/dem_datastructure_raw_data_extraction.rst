********************************************************************************
DEM Data Structure: Raw Data Extraction
********************************************************************************

.. rst-class:: lead

A practical guide to extracting raw numerical data from DEM models for external processing,
analysis, or visualization. Learn how to convert geometry, centroids, contacts, and connectivity 
information into NumPy arrays for computational workflows.


Contents
--------

1. `Model Setup`_: create a :class:`compas_dem.models.BlockModel` from :class:`compas_dem.templates.ArchTemplate` and compute contacts.
2. `Mesh Data`_: extract vertices and faces as NumPy arrays from element geometries.
3. `Centroids`_: convert element centroids to a structured NumPy array.
4. `Contact Polygons`_: extract contact geometry as a list of NumPy arrays.
5. `Contact Indices`_: get connectivity information as element index pairs.


Imports
^^^^^^^

.. literalinclude:: dem_datastructure_raw_data_extraction.py
    :language: python
    :end-before: # Model


Model Setup
^^^^^^^^^^^

We start by creating a model from an :class:`compas_dem.templates.ArchTemplate` and computing contacts using :meth:`compas_dem.models.BlockModel.compute_contacts`. This provides the foundation data structure for raw data extraction.

.. literalinclude:: dem_datastructure_raw_data_extraction.py
    :language: python
    :start-after: # Model
    :end-before: # Meshes to Numpy Arrays


Mesh Data
^^^^^^^^^

Extract vertices and faces from each element's geometry and convert them to NumPy arrays. Vertices are stored as float64 arrays containing 3D coordinates, while faces are stored as int32 arrays containing vertex indices.

.. literalinclude:: dem_datastructure_raw_data_extraction.py
    :language: python
    :start-after: # Meshes to Numpy Arrays
    :end-before: # Centroids

.. note::
   The resulting ``numpy_vertices`` and ``numpy_faces`` are lists of variable-sized arrays, as each element can have a different number of vertices and faces.

Centroids
^^^^^^^^^

Element centroids are extracted and converted to a single NumPy array for efficient processing. Each row represents the 3D centroid coordinates (3 floats per row) of one element.

.. literalinclude:: dem_datastructure_raw_data_extraction.py
    :language: python
    :start-after: # Centroids
    :end-before: # Contact Polygons


Contact Polygons
^^^^^^^^^^^^^^^^

Contact polygons represent the geometric interfaces between elements. Each contact is converted to a NumPy array containing the polygon vertices.

.. literalinclude:: dem_datastructure_raw_data_extraction.py
    :language: python
    :start-after: # Contact Polygons
    :end-before: # Contact Indices

.. note::
   The ``numpy_contact_polygons`` list contains variable-sized arrays, as contact polygons can have different numbers of vertices.


Contact Indices
^^^^^^^^^^^^^^^

Extract connectivity information (2 integers per row) as pairs of element indices that are in contact. This provides the graph structure of the assembly.

.. literalinclude:: dem_datastructure_raw_data_extraction.py
    :language: python
    :start-after: # Contact Indices