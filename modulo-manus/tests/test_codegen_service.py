import subprocess
import tempfile
from pathlib import Path

import pytest

from backend.services.codegen_service import generate_code
from backend.services.graph_service import graph_from_payload
from backend.services.logic_service import interpret_graph


def test_generated_python_and_javascript_are_executable(valid_graph):
    graph = graph_from_payload(valid_graph)
    instructions = interpret_graph(graph)
    python = generate_code(graph, instructions, "python")
    namespace = {}
    exec(python.source, namespace)  # trusted fixture-generated source, never request source
    assert namespace["run"]({"n": 3})["output"] == [3.0]
    javascript = generate_code(graph, instructions, "javascript")
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "flow.js"
        path.write_text(javascript.source + "\nconsole.log(JSON.stringify(run({n: -1})));\n")
        assert '"output":[0]' in subprocess.check_output(["node", str(path)], text=True)


def test_generated_boolean_and_finite_number_inputs_are_checked():
    boolean_graph = graph_from_payload({
        "name": "boolean input",
        "nodes": [
            {"id": "start", "type": "start", "label": "Start"},
            {"id": "input", "type": "input", "label": "READ enabled: boolean"},
            {"id": "output", "type": "output", "label": "PRINT enabled"},
            {"id": "end", "type": "end", "label": "End"},
        ],
        "edges": [
            {"id": "e1", "source": "start", "target": "input", "label": ""},
            {"id": "e2", "source": "input", "target": "output", "label": ""},
            {"id": "e3", "source": "output", "target": "end", "label": ""},
        ],
    })
    boolean_instructions = interpret_graph(boolean_graph)
    python = generate_code(boolean_graph, boolean_instructions, "python")
    namespace = {}
    exec(python.source, namespace)
    assert namespace["run"]({"enabled": True})["output"] == [True]
    with pytest.raises(ValueError, match="Input must be boolean"):
        namespace["run"]({"enabled": "true"})

    javascript = generate_code(boolean_graph, boolean_instructions, "javascript")
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "boolean.js"
        path.write_text(javascript.source + "\nconsole.log(JSON.stringify(run({enabled: true})));\n")
        assert '"output":[true]' in subprocess.check_output(["node", str(path)], text=True)

    number_graph = graph_from_payload({
        "name": "finite number",
        "nodes": [
            {"id": "start", "type": "start", "label": "Start"},
            {"id": "input", "type": "input", "label": "INPUT n"},
            {"id": "output", "type": "output", "label": "OUTPUT n"},
            {"id": "end", "type": "end", "label": "End"},
        ],
        "edges": [
            {"id": "e1", "source": "start", "target": "input", "label": ""},
            {"id": "e2", "source": "input", "target": "output", "label": ""},
            {"id": "e3", "source": "output", "target": "end", "label": ""},
        ],
    })
    number_instructions = interpret_graph(number_graph)
    python = generate_code(number_graph, number_instructions, "python")
    namespace = {}
    exec(python.source, namespace)
    with pytest.raises(ValueError, match="Input must be finite"):
        namespace["run"]({"n": "nan"})

    javascript = generate_code(number_graph, number_instructions, "javascript")
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "finite.js"
        path.write_text(
            javascript.source
            + "\ntry { run({n: Infinity}); } catch (error) { console.log(error.message); }\n"
        )
        assert "Input must be finite" in subprocess.check_output(["node", str(path)], text=True)


def test_generated_javascript_modulo_matches_python_for_negative_operands():
    graph = graph_from_payload({
        "name": "modulo signs",
        "nodes": [
            {"id": "start", "type": "start", "label": "Start"},
            {"id": "positive", "type": "output", "label": "OUTPUT -3 % 2"},
            {"id": "negative", "type": "output", "label": "OUTPUT -3 % -2"},
            {"id": "end", "type": "end", "label": "End"},
        ],
        "edges": [
            {"id": "e1", "source": "start", "target": "positive", "label": ""},
            {"id": "e2", "source": "positive", "target": "negative", "label": ""},
            {"id": "e3", "source": "negative", "target": "end", "label": ""},
        ],
    })
    instructions = interpret_graph(graph)
    python = generate_code(graph, instructions, "python")
    namespace = {}
    exec(python.source, namespace)
    assert namespace["run"]()["output"] == [1, -1]

    javascript = generate_code(graph, instructions, "javascript")
    assert "function _mod" in javascript.source
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "modulo.js"
        path.write_text(javascript.source + "\nconsole.log(JSON.stringify(run()));\n")
        assert '"output":[1,-1]' in subprocess.check_output(["node", str(path)], text=True)

    zero_division = graph_from_payload({
        "name": "division by zero",
        "nodes": [
            {"id": "start", "type": "start", "label": "Start"},
            {"id": "output", "type": "output", "label": "OUTPUT 1 / 0"},
            {"id": "end", "type": "end", "label": "End"},
        ],
        "edges": [
            {"id": "e1", "source": "start", "target": "output", "label": ""},
            {"id": "e2", "source": "output", "target": "end", "label": ""},
        ],
    })
    source = generate_code(zero_division, interpret_graph(zero_division), "javascript").source
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "divide.js"
        path.write_text(source + "\ntry { run(); } catch (error) { console.log(error.message); }\n")
        assert "Division by zero" in subprocess.check_output(["node", str(path)], text=True)
