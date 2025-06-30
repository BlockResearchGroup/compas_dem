from compas_dem.fabrication.label import Label
from compas.geometry import Point, Polyline, Translation
from compas_viewer.viewer import Viewer
import sys

# Debug version of from_string that prints letter width info
def debug_from_string(label, string, scale=1.0, offset=[0, 0, 0], line_spacing=1.5, letter_spacing=0.0, space_width=0.5):
    polylines = []
    current_x = offset[0]
    current_y = offset[1]
    line_height = 0.7  # Default height for a line
    
    def get_letter_bounds(letter_data):
        min_x = float('inf')
        min_y = float('inf')
        max_x = float('-inf')
        max_y = float('-inf')
        
        path_data = letter_data.get("path", [])
        if not isinstance(path_data, list):
            path_data = [path_data]
            
        for path in path_data:
            # Check start point
            x = float(path.get("_x", 0))
            y = float(path.get("_y", 0))
            min_x = min(min_x, x)
            min_y = min(min_y, y)
            max_x = max(max_x, x)
            max_y = max(max_y, y)
            
            # Check all points in the 'to' array
            to_points = path.get("to", [])
            if not isinstance(to_points, list):
                to_points = [to_points]
                
            for to_point in to_points:
                x = float(to_point.get("_x", 0))
                y = float(to_point.get("_y", 0))
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)
                
        return min_x, min_y, max_x, max_y
    
    print("\nDEBUG: Letter width and spacing information:")
    print("Char | Width | _start | _end | Bounding Box | Mode | Position Update")
    print("-" * 80)
    
    for char in string:
        if char == '\n':
            print(f"\n    | ------ | ------ | ----- | ------------- | newline | x reset, y -= {line_height * line_spacing * scale:.3f}")
            current_x = offset[0]
            current_y -= line_height * line_spacing * scale
            continue
        
        if char == ' ':
            space_advance = space_width * scale
            print(f"' '  | ------ | ------ | ----- | ------------- | space | x += {space_advance:.3f}")
            current_x += space_advance
            continue
        
        letter_data = label.char_map.get(char) or label.char_map.get(ord(char))
        
        if not letter_data:
            fallback_advance = 0.3 * scale
            print(f"{char}   | ------ | ------ | ----- | ------------- | unknown | x += {fallback_advance:.3f}")
            current_x += fallback_advance
            continue
        
        min_x, min_y, max_x, max_y = get_letter_bounds(letter_data)
        letter_width = max_x - min_x
        letter_height = max_y - min_y
        
        start_pos = float(letter_data.get("_start", 0.0))
        end_pos = float(letter_data.get("_end", 0.7))
        
        if line_height < letter_height:
            line_height = letter_height
        
        letter_x = current_x - start_pos * scale
        
        path_data = letter_data.get("path", [])
        if not isinstance(path_data, list):
            path_data = [path_data]
                
        for path in path_data:
            points = []
            
            start_x = float(path.get("_x", 0)) * scale + letter_x
            start_y = float(path.get("_y", 0)) * scale + current_y
            points.append(Point(start_x, start_y, offset[2]))
            
            to_points = path.get("to", [])
            if not isinstance(to_points, list):
                to_points = [to_points]
                
            for to_point in to_points:
                x = float(to_point.get("_x", 0)) * scale + letter_x
                y = float(to_point.get("_y", 0)) * scale + current_y
                points.append(Point(x, y, offset[2]))
            
            if len(points) > 1:
                polylines.append(Polyline(points))
        
        if letter_spacing == 0:
            position_update = letter_width * scale
            mode = "bbox"
            current_x += position_update
        else:
            position_update = end_pos * scale + letter_spacing * scale
            mode = "end+"
            current_x += position_update
        
        print(f"{char}   | {letter_width:.3f} | {start_pos:.3f} | {end_pos:.3f} | [{min_x:.2f},{max_x:.2f}] | {mode} | x += {position_update:.3f}")
    
    return polylines

# Create a Label instance
label = Label()

# Example text to show thin letters and various spacing
text = "Will ijlI thin letters now have better spacing?"
scale = 1.0  # Scale factor for better visibility
offset = [0, 0, 0]  # Starting position

# Test with different letter_spacing values
print("=== TEST WITH LETTER_SPACING = 0 ===")
polylines1 = debug_from_string(label, text, scale, offset, letter_spacing=0.0)

print("\n=== TEST WITH LETTER_SPACING = 0.05 ===")
polylines2 = debug_from_string(label, text, scale, offset, letter_spacing=0.0001)

print("\n=== TEST WITH LETTER_SPACING = 0.1 ===")
polylines3 = debug_from_string(label, text, scale, [0, -4, 0], letter_spacing=0.1)

# Visualize the results
viewer = Viewer()

# Add polylines from the first test (red - 0 spacing)
for polyline in polylines1:
    viewer.scene.add(polyline, color=(1, 0, 0))

# Add polylines from the second test (green - 0.05 spacing) - offset vertically 
polylines2_offset = []
for polyline in polylines2:
    new_points = [Point(p.x, p.y - 2, p.z) for p in polyline.points]
    polylines2_offset.append(Polyline(new_points))
    viewer.scene.add(polylines2_offset[-1])

# Add polylines from the third test (blue - 0.1 spacing) - already has offset in original data
for polyline in polylines3:
    viewer.scene.add(polyline)

print("\nRed: letter_spacing=0.0 (zero spacing)")
print("Green: letter_spacing=0.05 (small spacing) - middle line")
print("Blue: letter_spacing=0.1 (larger spacing) - bottom line")

# Show the viewer
viewer.show()
