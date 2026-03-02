from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import List
from typing import Optional
from typing import Tuple

import numpy as np
import numpy.typing as npt
from compas.data import Data

from ..models.blockmodel import BlockModel


class Problem(Data):
    """
    The `Problem` class represents a discrete element method (DEM) problem, which consists of a block model and the associated contacts and interactions between the blocks.
    It serves as a container for all the necessary information to define and solve a DEM simulation:
    Geometry, Boundary Conditions, material properties, and contact properties.

    Parameters
    ----------
    model : BlockModel
        The block model representing the geometry of the problem.

    Attributes
    ----------
    model : BlockModel
        The block model representing the geometry of the problem.
    """

    q: Optional[npt.NDArray] = None  # BC Force vector
    u: Optional[npt.NDArray] = None  # BC Displacement vector
    supports: Optional[List[bool]] = None  # Support conditions

    model: BlockModel

    def __init__(self, model: BlockModel):
        self.model = model
        self.blocks = list(model.blocks())
        self.q = np.zeros([len(self.blocks), 6])
        self.u = np.zeros([len(self.blocks), 6])

    def __data__(self) -> dict:
        data = super().__data__
        data.update(
            {
                "model": self.model,
                "q": self.q,
                "u": self.u,
                "supports": self.supports,
            }
        )
        return data

    def apply_load(self, load_vector: Optional[List[Tuple[str, int, float]]]):
        """Apply loads to one block in the problem."""
        for load in load_vector:
            type, block, magnitude = load
            block = self.blocks[block]
            if block is not None:
                if type == "qx":
                    self.q[block.index, 0] = magnitude
                elif type == "qy":
                    self.q[block.index, 1] = magnitude
                elif type == "qz":
                    self.q[block.index, 2] = magnitude
                elif type == "rx":
                    self.q[block.index, 3] = magnitude
                elif type == "ry":
                    self.q[block.index, 4] = magnitude
                elif type == "rz":
                    self.q[block.index, 5] = magnitude
            else:
                raise ValueError(f"Block with index {block} does not exist in the model.")

        load_vector = None
        return self.q

    def apply_displacement(self, displacement_vector: Optional[List[Tuple[str, int, float]]]):
        """Apply displacements to one block in the problem."""
        for displacement in displacement_vector:
            type, block, magnitude = displacement
            block = self.blocks[block]
            if block is not None:
                if type == "ux":
                    self.u[block.index, 0] = magnitude
                elif type == "uy":
                    self.u[block.index, 1] = magnitude
                elif type == "uz":
                    self.u[block.index, 2] = magnitude
                elif type == "rx":
                    self.u[block.index, 3] = magnitude
                elif type == "ry":
                    self.u[block.index, 4] = magnitude
                elif type == "rz":
                    self.u[block.index, 5] = magnitude
            else:
                raise ValueError(f"Block with index {block} does not exist in the model.")


# Assign contact model for the problem as a whole or just for specific contacts.
# Incase of assigning contact properties for specific contacts, the contact properties can be accessed via the graph edge attributes of the model. For example:
# for contact in model.graph.edges():
#     model.graph.edge_attribute(contact, "contact_properties", contact_type_1)
