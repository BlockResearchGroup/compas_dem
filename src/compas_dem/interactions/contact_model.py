import math
from typing import Optional

from compas.data import Data


class ContactModel(Data):
    """Base class for all types of contact models.

    Parameters
    ----------
    name : str, optional
        The name of the contact law.

    """

    def __init__(self, name: Optional[str] = None) -> None:
        super().__init__(name=name)

    @property
    def __data__(self) -> dict:
        return {"name": self.name}

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(name="{self.name}")'

    @classmethod
    def __from_data__(cls, data: dict) -> "ContactModel":
        return cls(name=data.get("name"))


class MohrCoulomb(ContactModel):
    """Contact properties for the Mohr-Coulomb contact law.

    Parameters
    ----------
    name : str, optional
        The name of the contact law.
    phi : float, optional
        Friction angle in degrees. Provide either `phi` or `mu`, not both.
    mu : float, optional
        Friction coefficient (tan(phi)). Provide either `phi` or `mu`, not both.
    c : float, optional
        Cohesion.
    t_c : float, optional
        Tensile cutoff capacity
    """

    def __init__(
        self,
        phi: Optional[float] = None,
        mu: Optional[float] = None,
        c: Optional[float] = None,
        t_c: Optional[float] = None,
        name: Optional[str] = None,
    ):
        super().__init__(name=name)

        if phi is not None:
            self._phi = float(phi)
            self._mu = math.tan(math.radians(self._phi))
        else:
            self._mu = float(mu)
            if self._mu < 0:
                raise ValueError("`mu` must be non-negative.")
            self._phi = math.degrees(math.atan(self._mu))

        self.c = c
        self.t_c = t_c

    @property
    def __data__(self) -> dict:
        data = super().__data__
        data.update(
            {
                "phi": self._phi,
                "c": self.c,
                "t_c": self.t_c,
                "mu": self._mu,
            }
        )
        return data

    @classmethod
    def __from_data__(cls, data: dict) -> "MohrCoulomb":
        return cls(
            phi=data["phi"],
            c=data["c"],
            t_c=data["t_c"],
            name=data.get("name"),
        )

    @property
    def phi(self) -> float:
        return self._phi

    @property
    def mu(self) -> float:
        return self._mu
