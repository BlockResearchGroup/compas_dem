from typing import Optional

from compas.data import Data


class JointModel(Data):
    """Contact properties for the Mohr-Coulomb contact law.

    Parameters
    ----------
    name : str, optional
        The name of the contact law.
    kn : float, optional
        Normal stiffness.
    kt : float, optional
        Tangential stiffness.
    """

    def __init__(
        self,
        kn: Optional[float] = None,
        kt: Optional[float] = None,
        name: Optional[str] = None,
    ):
        super().__init__(name=name)

        self.kn = kn
        self.kt = kt

    @property
    def __data__(self) -> dict:
        data = super().__data__
        data.update(
            {
                "kn": self.kn,
                "kt": self.kt,
            }
        )
        return data
