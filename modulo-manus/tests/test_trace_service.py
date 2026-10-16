from backend.services.codegen_service import generate_code
from backend.services.graph_service import graph_from_payload
from backend.services.logic_service import interpret_graph
from backend.services.pseudocode_service import generate_pseudocode
from backend.services.trace_service import build_trace


def test_trace_has_one_based_lines_for_every_node(valid_graph):
    graph = graph_from_payload(valid_graph)
    instructions = interpret_graph(graph)
    code = generate_code(graph, instructions, "python")
    pseudo = generate_pseudocode(graph, instructions)
    trace = build_trace(graph, code.node_lines, pseudo.node_lines)
    assert [item["nodeId"] for item in trace if "edgeId" not in item] == [node.id for node in graph.nodes]
    assert {item["edgeId"] for item in trace if "edgeId" in item} == {edge.id for edge in graph.edges}
    assert all(item["codeLines"] and item["pseudoLines"] for item in trace)
