import os

import compas
from compas_dem.viewer import DEMViewer

HERE = os.path.dirname(__file__)

model = compas.json_load(os.path.join(HERE, "DEM_model.json"))
results = compas.json_load(os.path.join(HERE, "DEM_results.json"))

# graph = model.graph
# for node in graph.nodes():
#     block_transformation = graph.node_attribute(node, "transformation")
#     # print(f"Block {node} transformation:\n{block_transformation}\n")

# for edge in graph.edges():
#     gap = graph.edge_attribute(edge, "gap")
#     magnitude = graph.edge_attribute(edge, "force_magnitude")
#     print(f"Edge {edge} gap: {gap}, force magnitude: {magnitude}")

viewer = DEMViewer(model)
viewer.add_solution(results, scale=0.5)
viewer.show()
