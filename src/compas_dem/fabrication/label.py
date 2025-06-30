from pathlib import Path
from compas.geometry import Polyline, Point
import compas

class Label(object):
    def __init__(self):
        HERE = Path(__file__).parent.parent.parent.parent
        DATA = HERE / "data"
        SESSION = DATA / "text.json"
        self.session = compas.json_load(SESSION)
        self.font_data = self.session.get("bbfont", {}).get("letter", [])
        self.char_map = {}
        for letter in self.font_data:
            if "_code" in letter:
                try:
                    # Store both as integer code and as character if it's a printable ASCII
                    code = int(letter["_code"])
                    self.char_map[code] = letter
                    if 32 <= code <= 126:  # Standard ASCII printable range
                        self.char_map[chr(code)] = letter
                except ValueError:
                    # Handle special cases where _code might be a character
                    self.char_map[letter["_code"]] = letter

    @staticmethod
    def from_string(string, scale=1.0, offset=[0, 0, 0], line_spacing=1.5, letter_spacing=0.0, space_width=0.5):
        """
        Convert a string to a list of polylines based on the font data in the JSON file.
        
        Parameters
        ----------
        string : str
            The string to convert to polylines
        scale : float, optional
            Scale factor for the letters, defaults to 1.0
        offset : list, optional
            Starting position offset [x, y, z], defaults to [0, 0, 0]
        line_spacing : float, optional
            Factor for vertical spacing between lines, defaults to 1.5
        letter_spacing : float, optional
            Additional spacing factor between letters, defaults to 0.0 for zero spacing
        space_width : float, optional
            Width of space character. Defaults to 0.5.
        
        Returns
        -------
        list
            List of compas.geometry.Polyline objects.
        """
        label = Label()
        polylines = []
        current_x = offset[0]
        current_y = offset[1]
        line_height = 1.0

        def get_letter_bounds(letter_data):
            min_x, min_y = float('inf'), float('inf')
            max_x, max_y = float('-inf'), float('-inf')
            
            path_data = letter_data.get("path", [])
            if not isinstance(path_data, list):
                path_data = [path_data]
                
            for path in path_data:
                x = float(path.get("_x", 0))
                y = float(path.get("_y", 0))
                min_x, min_y = min(min_x, x), min(min_y, y)
                max_x, max_y = max(max_x, x), max(max_y, y)
                
                to_points = path.get("to", [])
                if not isinstance(to_points, list):
                    to_points = [to_points]
                    
                for point in to_points:
                    x = float(point.get("_x", 0))
                    y = float(point.get("_y", 0))
                    min_x, min_y = min(min_x, x), min(min_y, y)
                    max_x, max_y = max(max_x, x), max(max_y, y)
            
            return min_x, min_y, max_x, max_y
        
        for char in string:
            if char == '\n':
                current_x = offset[0]
                current_y -= line_height * line_spacing * scale
                continue
            
            if char == ' ':
                current_x += space_width * scale
                continue
            
            letter_data = label.char_map.get(char) or label.char_map.get(ord(char))
            
            if not letter_data:
                current_x += 0.3 * scale
                continue
            
            min_x, min_y, max_x, max_y = get_letter_bounds(letter_data)
            letter_width = max_x - min_x
            letter_height = max_y - min_y
            
            if letter_height > line_height:
                line_height = letter_height
            
            start_pos = float(letter_data.get("_start", 0.0))
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
            
            # Always use actual letter width plus letter_spacing
            # This ensures consistent proportional spacing for all letters
            current_x += letter_width * scale + letter_spacing * scale
        
        return polylines

    def to_polylines(self, text, scale=1.0, offset=[0, 0, 0], line_spacing=1.5, letter_spacing=0.001, space_width=0.5):
        """
        Convenience method that calls the static from_string method.
        
        Parameters
        ----------
        text : str
            The string to convert to polylines
        scale : float, optional
            Scale factor for the letters, defaults to 1.0
        offset : list, optional
            Starting position offset [x, y, z], defaults to [0, 0, 0]
            
        Returns
        -------
        list
            List of polylines representing the letters
        """
        return self.from_string(text, scale, offset, line_spacing, letter_spacing, space_width)
