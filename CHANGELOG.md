# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Added


### Changed

* Fixed tangential force direction in post-processing for vizualization.
* Reorganized the `scripts/` examples folder for clarity.
* Adapted the examples to the new API.


### Removed


## [0.5.0] 2026-05-07

### Added

* Added `Problem` class and `BoundaryConditions` (gravity, body forces, point/surface loads, prescribed displacements/rotations, supports).
* Added `Solver` abstraction in `compas_dem.problem.solvers` so additional backends can be plugged in alongside CRA, LMGC90, and RBE.
* Added LMGC90 solver support (`compas_dem.analysis.lmgc90`).
* Added CRA penalty and RBE solver support (`compas_dem.analysis.cra`), with results written back to the `BlockModel` graph in the same schema as LMGC90.
* Added `compas_dem.interactions.ContactProperties` and `JointModel` / `MohrCoulomb` for configuring contact behaviour.
* Added force visualization in `compas_dem.viewer.DEMViewer.add_solution`: per-edge contact resultants, per-support reaction resultants, contact polygons, and reaction labels showing force components and magnitude.

### Changed

* Fixed Compas_CGAL >= 0.9.1 import error.

### Removed


## [0.4.2] 2025-09-10

### Added

* Added `compas_viewer` and `compas_notebook` to `requirements-viz.txt`.
* Added optional "viz" dependencies to `pyproject.toml`.

### Changed

* Fixed bug in serialisation mechanism of block elements due to unhandled `material` parameter.

### Removed

* Removed `compas_viewer` and `compas_notebook` from dev requirements.


## [0.4.1] 2025-09-09

### Added

### Changed

### Removed


## [0.4.0] 2025-09-06

### Added

* Added tutorials.
* Added examples.
* Added documentation.
* Added `is_support` assignment to `compas_dem.BlockModel.from_barrelvault`.

### Changed

### Removed


## [0.3.3] 2025-07-04

### Added

* Added `compas_viewer` to dev requirements.

### Changed

### Removed

* Removed `compas_viewer` from main requirements.


## [0.3.2] 2025-06-26

### Added

### Changed

* Changed `BlockModel.from_triangulation_dual` to use `compas_cgal.meshing.trimesh_dual`.
* Changed `BlockModel.from_meshpattern` to use `compas_cgal.meshing.trimesh_remesh`, `compas_cgal.meshing.project_mesh_on_mesh`, `compas_libigl.mapping.map_pattern_to_mesh`.

### Removed


## [0.3.1] 2025-06-24

### Added

### Changed

* Fixed bug in pattern mapping in `BlockModel.from_meshpattern` related to inconsistent cycles.

### Removed


## [0.3.0] 2025-06-24

### Added

* Added `BlockModel.from_triangulation_dual`.
* Added `BlockModel.from_meshpattern`.
* Added `compas_dem.viewer.Viewer`.

### Changed

### Removed


## [0.2.0] 2025-06-04

### Added

### Changed

* Changed `compas_dem.elements.BlockElement` to `compas_dem.elements.Block`.

### Removed

* Removed `compas_dem.notebook.ThreeBlockModelObject` temporarily.
* Removed `compas_dem.notebook.buffers.meshes_to_edgesbuffer` temporarily.
* Removed `compas_dem.notebook.buffers.meshes_to_facesbuffer` temporarily.
* Removed `compas_dem.viewers.BlockModelViewer` temporarily.
* Removed CRA from default requirements.


## [0.1.1] 2025-01-31

### Added

* Added `compas_dem.analysis.cra_penalty_solve`.
* Added `compas_dem.analysis.rbe_solve`.
* Added `compas_dem.elements.BlockElement`.
* Added `compas_dem.interactions.FrictionContact`.
* Added `compas_dem.models.BlockModel`.
* Added `compas_dem.notebook.ThreeBlockModelObject`.
* Added `compas_dem.notebook.buffers.meshes_to_edgesbuffer`.
* Added `compas_dem.notebook.buffers.meshes_to_facesbuffer`.
* Added `compas_dem.templates.ArchTemplate`.
* Added `compas_dem.templates.BarrelVaultTemplate`.
* Added `compas_dem.templates.DomeTemplate`.
* Added `compas_dem.viewers.BlockModelViewer`.

### Changed

### Removed
