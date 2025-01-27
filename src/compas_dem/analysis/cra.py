from compas_assembly.datastructures import Assembly
from compas_assembly.datastructures import Block
from compas_cra.equilibrium import cra_penalty_solve as _cra_penalty_solve
from compas_cra.equilibrium import rbe_solve as _rbe_solve

from compas_dem.elements import BlockElement
from compas_dem.interactions import FrictionContact
from compas_dem.models import BlockModel


def _blockmodel_to_assembly(model: BlockModel) -> Assembly:
    element: BlockElement
    element_block: dict[int, int] = {}

    assembly = Assembly()

    for element in model.elements():
        block: Block = element.modelgeometry.copy(cls=Block)
        x, y, z = block.centroid()
        node = assembly.add_block(block, x=x, y=y, z=z, is_support=element.is_support)
        element_block[element.graphnode] = node

    for edge in model.graph.edges():
        u = element_block[edge[0]]
        v = element_block[edge[1]]

        contacts: list[FrictionContact] = model.graph.edge_attribute(edge, name="contacts")
        assembly.graph.add_edge(u, v, interfaces=contacts)

    return assembly


def rbe_solve(
    model: BlockModel,
    mu: float = 0.84,
    density: float = 1.0,
    verbose: bool = False,
    timer: bool = False,
):
    assembly = _blockmodel_to_assembly(model)
    _rbe_solve(assembly, mu=mu, density=density, verbose=verbose, timer=timer)


def cra_penalty_solve(
    model: BlockModel,
    mu: float = 0.84,
    density: float = 1.0,
    d_bnd: float = 0.001,
    eps: float = 0.0001,
    verbose: bool = False,
    timer: bool = False,
):
    assembly = _blockmodel_to_assembly(model)
    _cra_penalty_solve(
        assembly,
        mu=mu,
        density=density,
        d_bnd=d_bnd,
        eps=eps,
        verbose=verbose,
        timer=timer,
    )
