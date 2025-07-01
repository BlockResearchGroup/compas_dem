from typing import Union

from compas.datastructures import Mesh
from compas.geometry import Brep
from compas_cgal.booleans import boolean_union_mesh_mesh
from compas_model.modifiers import Modifier


class BooleanUnionModifier(Modifier):
    """Boolean union modifier.

    Parameters
    ----------
    name : str, optional
        The name of the interaction.

    """

    def apply(
        self,
        source,
        targetgeometry: Union[Brep, Mesh],
    ) -> Union[Brep, Mesh]:
        """Boolean difference the source geometry with the shape and boolean union the target geometry with the shape.

        Parameters
        ----------
        source : :class:`compas.geometry.Brep` | :class:`compas.datastructures.Mesh`
            The source of the modification.
        targetgeometry : :class:`compas.geometry.Brep` | :class:`compas.datastructures.Mesh`
            The target of the modification.

        Returns
        -------
        Brep | Mesh
            The modified source geometry.

        """
        if isinstance(source.elementgeometry, Mesh) and isinstance(targetgeometry, Mesh):
            VS, FS = source.elementgeometry.to_vertices_and_faces(True)
            VT, FT = targetgeometry.to_vertices_and_faces(True)
            V, F = boolean_union_mesh_mesh((VT, FT), (VS, FS))
            mesh = Mesh.from_vertices_and_faces(V, F)
            mesh.attributes = targetgeometry.attributes
            return mesh
        elif isinstance(source.elementgeometry, Brep) and isinstance(targetgeometry, Brep):
            result = targetgeometry + source.elementgeometry
            return result
        else:
            raise ValueError(f"Source and target geometry must be of the same type. Source: {type(source.elementgeometry)}, Target: {type(targetgeometry)}")
