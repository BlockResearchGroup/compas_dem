from tracemalloc import Frame
from compas_dem.fabrication.label import Label
from compas.geometry import Frame
from compas_viewer.viewer import Viewer

# Example text to show thin letters and various spacing
text = "Will the thin letters now have a better spacing?"
frame = Frame.worldYZ()
label = Label.from_string(text, frame, 1)

viewer = Viewer()
for polyline in label.polylines:
    viewer.scene.add(polyline)
viewer.show()
