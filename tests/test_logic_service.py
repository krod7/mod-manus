import pytest

from backend.services.graph_service import graph_from_payload
from backend.services.logic_service import LogicError, interpret_graph, parse_expression


def test_interprets_known_grammar(valid_graph):
    instructions = interpret_graph(graph_from_payload(valid_graph))
    assert instructions["input"].kind == "input"
    assert instructions["decision"].kind == "decision"


@pytest.mark.parametrize("expression", ["__import__('os').system('id')", "x.__class__", "eval('2')", "a[0]"])
def test_rejects_injection_syntax(expression):
    with pytest.raises(LogicError):
        parse_expression(expression)


@pytest.mark.parametrize(
    ("input_label", "output_label", "input_type"),
    [
        ("READ _value", "PRINT _value", "number"),
        ("INPUT _value: text", "DISPLAY _value", "text"),
        ("READ _value: string", "OUTPUT _value", "string"),
    ],
)
def test_interprets_canonical_input_output_aliases(input_label, output_label, input_type):
    graph = graph_from_payload({
        "name": "aliases",
        "nodes": [
            {"id": "start", "type": "start", "label": "Start"},
            {"id": "read", "type": "input", "label": input_label},
            {"id": "print", "type": "output", "label": output_label},
            {"id": "end", "type": "end", "label": "End"},
        ],
        "edges": [
            {"id": "e1", "source": "start", "target": "read", "label": ""},
            {"id": "e2", "source": "read", "target": "print", "label": ""},
            {"id": "e3", "source": "print", "target": "end", "label": ""},
        ],
    })

    instructions = interpret_graph(graph)

    assert instructions["read"].input_type == input_type
    assert instructions["read"].variable == "_value"
    assert instructions["print"].kind == "output"


def test_rejects_variable_not_assigned_on_every_branch_path():
    graph = graph_from_payload({
        "name": "partial assignment",
        "nodes": [
            {"id": "start", "type": "start", "label": "Start"},
            {"id": "decision", "type": "decision", "label": "true"},
            {"id": "assign", "type": "process", "label": "value = 1"},
            {"id": "output", "type": "output", "label": "OUTPUT value"},
            {"id": "end", "type": "end", "label": "End"},
        ],
        "edges": [
            {"id": "e1", "source": "start", "target": "decision", "label": ""},
            {"id": "e2", "source": "decision", "target": "assign", "label": "yes"},
            {"id": "e3", "source": "decision", "target": "output", "label": "no"},
            {"id": "e4", "source": "assign", "target": "output", "label": ""},
            {"id": "e5", "source": "output", "target": "end", "label": ""},
        ],
    })

    with pytest.raises(LogicError, match=r"Node output: Variable 'value'.*every incoming path"):
        interpret_graph(graph)
