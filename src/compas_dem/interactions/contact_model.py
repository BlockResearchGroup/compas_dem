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


class MohrCoulomb(ContactModel):
    """Contact properties for the Mohr-Coulomb contact law.

    Parameters
    ----------
    name : str, optional
        The name of the contact law.
    """

    def __init__(
        self,
        phi: Optional[float] = None,
        mu: Optional[float] = None,
        c: Optional[float] = None,
        t_c: Optional[float] = None,
        k_n: Optional[float] = None,
        k_t: Optional[float] = None,
        name: Optional[str] = None,
    ):
        super().__init__(name=name)

        if phi is not None and mu is not None:
            raise ValueError("Provide only one of `phi` (deg) or `mu`.")
        if (phi is None) == (mu is None):
            raise ValueError("Provide only one of `phi` (deg) or `mu`.")

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
        self.k_n = k_n
        self.k_t = k_t

    @property
    def __data__(self) -> dict:
        data = super().__data__
        data.update(
            {
                "phi": self._phi,
                "c": self.c,
                "t_c": self.t_c,
                "k_n": self.k_n,
                "k_t": self.k_t,
                "mu": self._mu,
            }
        )
        return data

    @property
    def phi(self) -> float:
        return self._phi

    @property
    def mu(self) -> float:
        return self._mu
