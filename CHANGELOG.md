# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
