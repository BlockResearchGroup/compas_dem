from typing import Literal
from typing import Optional

from compas_model.materials import Material
from compas_model.materials.errors import PropertyNotDefined

from .generic import GenericMaterial


class Stone(GenericMaterial):
    """Class representing a generic stone material.

    Parameters
    ----------
    fc : float
        Mean compressive strength in [MPa].
    ft : float, optional
        Mean tensile strength in [MPa].
    Ecm : float, optional
        Modulus of elasticity in [GPa].
    density : float, optional
        Density of the material in [kg/m3].
        If not provided, 2400 kg/m3 is used.
    poisson : float, optional
        Poisson's ratio.
        If not provided, `poisson = 0.2` is used.
    name : str, optional
        Name of the material.

    Attributes
    ----------
    fc : float
        Mean compressive strength in [MPa].
    ft : float
        Mean tensile strength in [MPa].
    Ecm : float
        Modulus of elasticity in [MPa].

    """

    predefined_material = {
        "LIMESTONE": {
            "fc": None,
            "ft": None,
            "Ecm": 20000,
            "density": 2200,
            "poisson": 0.2,
        },
        "CONCRETE C20/25": {
            "fc": 20,
            "ft": 2.8,
            "Ecm": 30000,
            "density": 2400,
            "poisson": 0.2,
        },
    }
