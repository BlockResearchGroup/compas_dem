import os

import compas
from compas_dem.viewer import DEMViewer

# =============================================================================
# Load Problem
# =============================================================================

HERE = os.path.dirname(__file__)
problem = compas.json_load(
    os.path.join(HERE, "DEM_results.json"),
)

# =============================================================================
# Visualize block results
# =============================================================================

# graph = problem.model.graph
# for node in graph.nodes():
#     block_transformation = graph.node_attribute(node, "transformation")
#     # print(f"Block {node} transformation:\n{block_transformation}\n")

# for edge in graph.edges():
#     gap = graph.edge_attribute(edge, "gap")
#     magnitude = graph.edge_attribute(edge, "force_magnitude")
#     print(f"Edge {edge} gap: {gap}, force magnitude: {magnitude}")


# # =============================================================================
# # Visualize problem
# # =============================================================================

viewer = DEMViewer(problem.model)
viewer.add_solution(scale=0.5)
viewer.show()
