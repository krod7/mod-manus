from pathlib import Path

import pytest

from backend.errors import ValidationAPIError
from backend.services.graph_service import parse_annotated_svg, parse_drawio, parse_json

ROOT = Path(__file__).parent / "fixtures"


def test_imports_all_structured_graph_sources():
    assert len(parse_json((ROOT / "valid_graph.json").read_bytes()).nodes) == 6
    svg = parse_annotated_svg((ROOT / "annotated.svg").read_bytes())
    drawio = parse_drawio((ROOT / "simple.drawio").read_bytes())
    assert svg.nodes[0].type == "start"
    assert {node.type for node in drawio.nodes} == {"start", "end"}


def test_rejects_external_svg_content():
    with pytest.raises(ValidationAPIError):
        parse_annotated_svg(b'<svg><image href="https://example.com/x.png"/></svg>')
