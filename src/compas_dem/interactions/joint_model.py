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
        return {"name": self.name, "kn": self.kn, "kt": self.kt}

    @classmethod
    def __from_data__(cls, data: dict) -> "JointModel":
        return cls(kn=data["kn"], kt=data["kt"], name=data.get("name"))
