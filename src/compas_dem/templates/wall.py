from .template import Template


class WallTemplate(Template):
    """Create voussoirs for a typical brick wall."""

    def __init__(self):
        super().__init__()

    def blocks(self):
        """Compute the blocks.

        Returns
        -------
        list
            A list of blocks defined as simple meshes.

        Notes
        -----
        This method is used by the ``from_geometry`` constructor of the assembly data structure
        to create an assembly "from geometry".

        """
        pass
