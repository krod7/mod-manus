from backend.services.graph_service import graph_from_payload
from backend.services.logic_service import interpret_graph
from backend.services.pseudocode_service import generate_pseudocode


def test_pseudocode_has_every_node_trace(valid_graph):
    graph = graph_from_payload(valid_graph)
    generated = generate_pseudocode(graph, interpret_graph(graph))
    assert "WHILE state" in generated.source
    assert set(generated.node_lines) == {node.id for node in graph.nodes}
    assert all(min(lines) >= 1 for lines in generated.node_lines.values())
