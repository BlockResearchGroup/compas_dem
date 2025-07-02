from pathlib import Path

import compas
from compas.data import Data
from compas.geometry import Frame
from compas.geometry import Point
from compas.geometry import Polyline
from compas.geometry import Transformation


class Label(Data):
    @property
    def __data__(self) -> dict:
        return {
            "name": self.name,
            "frame": self.frame,
            "polylines": self.polylines,
        }

    def __init__(self, name: str = "", frame: Frame = Frame.worldXY(), polylines=None):
        super().__init__(name=name)

        self.frame = frame
        self.polylines: list[Polyline] = polylines or []

        # Path to font data file
        HERE = Path(__file__).parent.parent.parent.parent
        DATA = HERE / "data"
        SESSION = DATA / "text.json"
        
        # Store the file path for later lazy loading
        self._session_path = SESSION
        self._session = None
        self._font_data = None
        self._char_map = {}
        
    def _load_session(self):
        """Lazy load the session data when needed."""
        if self._session is None:
            self._session = compas.json_load(self._session_path)
            
    def _load_font_data(self):
        """Lazy load the font data when needed."""
        if self._font_data is None:
            self._load_session()
            self._font_data = self._session.get("bbfont", {}).get("letter", [])
            
    def _get_letter(self, char):
        """Get a letter from the font data, loading it if necessary."""
        # Try to get from cache first
        if char in self._char_map:
            return self._char_map[char]
            
        # If not in cache, try to load it
        self._load_font_data()
        
        # Check if it's a code point or character
        code = None
        if isinstance(char, int):
            code = char
        elif isinstance(char, str) and len(char) == 1:
            code = ord(char)
            
        # Find and cache the letter
        for letter in self._font_data:
            if "_code" in letter:
                try:
                    letter_code = int(letter["_code"])
                    if letter_code == code:
                        self._char_map[char] = letter
                        if 32 <= letter_code <= 126:  # Standard ASCII printable range
                            self._char_map[chr(letter_code)] = letter
                        return letter
                except ValueError:
                    # Handle special cases where _code might be a character
                    if letter["_code"] == char:
                        self._char_map[char] = letter
                        return letter
                        
        # Letter not found
        return None

    @classmethod
    def from_string(cls, string, frame, scale=1.0, line_spacing=1.5, letter_spacing=0.0, space_width=0.5):
        """
        Convert a string to a list of polylines based on the font data in the JSON file.

        Parameters
        ----------
        string : str
            The string to convert to polylines
        frame : Frame
            The frame to place the text in
        scale : float, optional
            Scale factor for the letters, defaults to 1.0
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
        label = Label(name=string, frame=frame)
        polylines = []
        current_x = 0
        current_y = 0
        line_height = 1.0

        def get_letter_bounds(letter_data):
            min_x, min_y = float("inf"), float("inf")
            max_x, max_y = float("-inf"), float("-inf")

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
            if char == "\n":
                current_x = 0
                current_y -= line_height * line_spacing * scale
                continue

            if char == " ":
                current_x += space_width * scale
                continue

            letter_data = label._get_letter(char) or label._get_letter(ord(char))

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
                points.append(Point(start_x, start_y, 0))

                to_points = path.get("to", [])
                if not isinstance(to_points, list):
                    to_points = [to_points]

                for to_point in to_points:
                    x = float(to_point.get("_x", 0)) * scale + letter_x
                    y = float(to_point.get("_y", 0)) * scale + current_y
                    points.append(Point(x, y, 0))

                if len(points) > 1:
                    polylines.append(Polyline(points))

            # Use the _end parameter to determine letter spacing
            # This ensures consistent spacing regardless of the letter's actual width
            end_pos = float(letter_data.get("_end", letter_width))
            current_x += end_pos * scale + letter_spacing * scale

        xform = Transformation.from_frame_to_frame(Frame.worldXY(), label.frame)
        for polyline in polylines:
            polyline.transform(xform)

        label.polylines = polylines

        return label

    def transform(self, xform):
        for polyline in self.polylines:
            polyline.transform(xform)

    def transformed(self, xform):
        new = self.copy()
        new.transform(xform)
        return new
