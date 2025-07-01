#! python3
# venv: brg-csd
# r: compas_model, Tessagon, compas_cgal==0.9.1, compas_libigl==0.7.4

import pathlib
import compas
from compas.geometry import Polyline
from compas.scene import Scene

# =============================================================================
# User Defined Pattern
# =============================================================================

session = compas.json_load(pathlib.Path(__file__).parent.parent / "data" / "2d_pattern.json")

# =============================================================================
# Vizualize
# =============================================================================

scene = Scene()
pattern = 3
for polygon in session:
    polyline = Polyline(polygon)
    polyline.append(polyline[0])
    scene.add(polyline)
scene.draw()