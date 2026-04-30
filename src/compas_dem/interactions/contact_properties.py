from typing import Optional

from compas.data import Data

from compas_dem.interactions.contact_model import ContactModel
from compas_dem.interactions.joint_model import JointModel


class ContactProperties(Data):
    """Base class for all types of contacts.

    Parameters
    ----------
    name : str, optional
        The name of the contact law.

    """

    def __init__(
        self,
        contact_model: Optional[ContactModel] = None,
        joint_model: Optional[JointModel] = None,
        name: Optional[str] = None,
    ) -> None:
        self.contact_model = contact_model
        self.joint_model = joint_model
        super().__init__(name=name)

    @property
    def __data__(self) -> dict:
        return {"name": self.name, "contact_model": self.contact_model, "joint_model": self.joint_model}

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(name="{self.name}", contact_model="{self.contact_model}", joint_model={self.joint_model})'

    @classmethod
    def __from_data__(cls, data: dict) -> "ContactProperties":
        contactproperties = cls(
            contact_model=data["contact_model"],
            joint_model=data["joint_model"],
            name=data.get("name"),
        )
        return contactproperties
