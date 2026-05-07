from typing import Literal
from typing import Optional

from compas_model.materials import Material
from compas_model.materials.errors import PropertyNotDefined


class Stone(Material):
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
            "poisson": 0.2,
        },
        "GENERIC": {
            "fc": None,
            "ft": None,
            "Ecm": None,
            "poisson": None,
        },
    }

    @property
    def __data__(self) -> dict:
        data = super().__data__
        data.update(
            {
                "fc": self.fc,
                "ft": self.ft,
                "Ecm": self.Ecm,
                "density": self.density,
                "poisson": self.poisson,
            }
        )
        return data

    def __init__(
        self,
        fc: float,
        ft: Optional[float] = None,
        Ecm: Optional[float] = None,
        density: float = 2400,
        poisson: float = 0.2,
        name: Optional[str] = None,
    ):
        super().__init__(name=name)

        self.fc = fc if fc else None
        self.ft = ft if ft else (0.1 * fc) if fc else None
        self.Ecm = Ecm
        self.density = density
        self.poisson = poisson

    @property
    def rho(self) -> float:
        return self.density

    @property
    def nu(self) -> float:
        return self.poisson

    @property
    def G(self) -> float:
        if self.Ecm:
            return self.Ecm / (2 * (1 + self.nu))
        raise PropertyNotDefined

    @classmethod
    def from_predefined_material(cls, predefined_material: Literal["LimeStone", "Generic"]) -> "Stone":
        """Construct a stone material from a predefined material.

        Parameters
        ----------
        predefined_material : {'LimeStone', 'Generic'}
            The predefined material of the stone.

        Returns
        -------
        :class:`Stone`

        """
        strength_class_upper = predefined_material.upper()
        if strength_class_upper not in cls.predefined_material:
            raise ValueError("Predefined material not supported: {}".format(strength_class_upper))
        params = cls.predefined_material[strength_class_upper]
        return cls(**params)
