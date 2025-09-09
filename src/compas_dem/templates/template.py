class Template:
    def __init__(self):
        pass

    def blocks(self):
        raise NotImplementedError

    def interfaces(self):
        raise NotImplementedError
    
    def intrados_and_extrados(self):
        """Return the intrados and extrados surfaces as meshes.
        Returns
        -------
        tuple
            0. Mesh representing the intrados surface.
            1. Mesh representing the extrados surface.
        """
        raise NotImplementedError

    def to_blocks_and_interfaces(self):
        """Convert the geometry to a list of block meshes,
        and a list of block index pairs representing connections or interfaces.

        Returns
        -------
        tuple
            0. List of meshes representing the block geometries.
            1. List of block index pairs representing connections or interfaces.
        """
        raise NotImplementedError
