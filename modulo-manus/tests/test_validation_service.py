from backend.services.graph_service import graph_from_payload
from backend.services.validation_service import validate_graph


def test_valid_graph_and_decision_error(valid_graph):
    assert validate_graph(graph_from_payload(valid_graph)).ok
    valid_graph["edges"][2]["label"] = "maybe"
    result = validate_graph(graph_from_payload(valid_graph))
    assert any("Decision node decision" in item for item in result.errors)


def test_warns_about_loop_that_has_an_exit(valid_graph):
    valid_graph["edges"][4]["target"] = "decision"  # positive loops; decision's no branch still exits
    result = validate_graph(graph_from_payload(valid_graph))
    assert result.ok
    assert any("loop" in warning.lower() for warning in result.warnings)
