from typing import Optional

from compas_model.materials import Material
from compas_model.materials.errors import PropertyNotDefined


class GenericMaterial(Material):
    """Base class for DEM materials."""

    predefined_material = {
        "GENERIC": {
            "fc": None,
            "ft": None,
            "Ecm": None,
            "density": 1000,
            "poisson": 0.2,
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
        fc: Optional[float] = None,
        ft: Optional[float] = None,
        Ecm: Optional[float] = None,
        density: float = 1000,
        poisson: float = 0.2,
        name: Optional[str] = None,
    ):
        super().__init__(name=name)
        self.fc = fc
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
    def from_predefined_material(cls, predefined_material: str) -> "GenericMaterial":
        key = predefined_material.upper()
        if key not in cls.predefined_material:
            raise ValueError(f"Predefined material not supported: {key}")
        return cls(**cls.predefined_material[key])
