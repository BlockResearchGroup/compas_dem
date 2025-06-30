from tracemalloc import Frame
from compas_dem.fabrication.label import Label
from compas.geometry import Point, Polyline, Translation, Frame
from compas_viewer.viewer import Viewer

# Create a Label instance
label = Label()

# Example text to show thin letters and various spacing
text = "Will the thin letters now have better spacing?"
scale = 1.0  # Scale factor for better visibility
offset = [0, 0, 0]  # Starting position

frame = Frame.worldYZ()
polylines3 = Label.from_string(text, frame)

viewer = Viewer()
for polyline in polylines3:
    viewer.scene.add(polyline)
viewer.show()
