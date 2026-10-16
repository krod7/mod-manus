"""Structured graph import and normalization (JSON, Modulo SVG, uncompressed draw.io)."""
from __future__ import annotations

import html
import json
import re
import xml.etree.ElementTree as ET
from typing import Any

from backend.errors import ValidationAPIError
from backend.models import Edge, Graph, Node

_TYPE_ALIASES = {
    "startend": "start_end", "terminal": "start_end", "io": "input_output",
    "input/output": "input_output", "parallelogram": "input_output",
    "rectangle": "process", "diamond": "decision", "ellipse": "start_end",
}


def _tag(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def _text(value: Any, limit: int | None = None) -> str:
    """Keep strings intact for semantic checks; the request-size limit bounds memory."""
    if not isinstance(value, str):
        return ""
    return value if limit is None else value[:limit]


def _number(value: Any, default: float = 0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def canonical_type(node_type: str, label: str) -> str:
    value = _TYPE_ALIASES.get(node_type.strip().lower(), node_type.strip().lower())
    if value == "start_end":
        lowered = label.strip().lower()
        if lowered in {"start", "begin"}:
            return "start"
        if lowered in {"end", "stop", "finish"}:
            return "end"
    return value


def graph_from_payload(payload: Any) -> Graph:
    """Convert untrusted JSON-shaped graph data to models; semantic validation happens later."""
    if not isinstance(payload, dict):
        raise ValidationAPIError("graph must be an object", ["graph_type"])
    raw_nodes, raw_edges = payload.get("nodes"), payload.get("edges")
    if not isinstance(raw_nodes, list) or not isinstance(raw_edges, list):
        raise ValidationAPIError("graph.nodes and graph.edges must be arrays", ["graph_shape"])
    nodes: list[Node] = []
    for raw in raw_nodes:
        if not isinstance(raw, dict):
            raise ValidationAPIError("Each node must be an object", ["node_shape"])
        label = _text(raw.get("label", ""))
        raw_type = _text(raw.get("type", ""))
        nodes.append(Node(
            id=_text(raw.get("id", "")), type=canonical_type(raw_type, label), label=label,
            x=_number(raw.get("x", 0)), y=_number(raw.get("y", 0)),
            confidence=_number(raw.get("confidence", 1), -1),
            note=_text(raw.get("note")) or None, color=_text(raw.get("color"), 100) or None,
        ))
    edges: list[Edge] = []
    for raw in raw_edges:
        if not isinstance(raw, dict):
            raise ValidationAPIError("Each edge must be an object", ["edge_shape"])
        edges.append(Edge(
            id=_text(raw.get("id", "")), source=_text(raw.get("source", "")),
            target=_text(raw.get("target", "")), label=_text(raw.get("label", "")),
        ))
    return Graph(name=_text(payload.get("name", "Untitled"), 240) or "Untitled", nodes=nodes, edges=edges)


def _secure_xml(data: bytes) -> ET.Element:
    if len(data) > 10 * 1024 * 1024:
        raise ValidationAPIError("XML source exceeds the 10 MiB limit", ["upload_size"])
    text = data.decode("utf-8", "strict")
    lowered = text.lower()
    forbidden = ("<!doctype", "<!entity", "<script", "javascript:", "file:")
    external_href = re.search(r"(?:xlink:)?href\s*=\s*['\"]\s*(?:https?:|//)", lowered)
    external_css_url = re.search(r"url\(\s*(?:https?:|//)", lowered)
    if any(marker in lowered for marker in forbidden) or external_href or external_css_url:
        raise ValidationAPIError("SVG/XML contains unsafe external or executable content", ["unsafe_xml"])
    try:
        return ET.fromstring(text)
    except ET.ParseError as exc:
        raise ValidationAPIError("XML source is malformed", ["xml_parse"]) from exc


def parse_json(data: bytes) -> Graph:
    try:
        payload = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValidationAPIError("JSON source is malformed", ["json_parse"]) from exc
    return graph_from_payload(payload.get("graph", payload) if isinstance(payload, dict) else payload)


def parse_annotated_svg(data: bytes) -> Graph:
    root = _secure_xml(data)
    candidate: str | None = None
    for element in root.iter():
        if element.attrib.get("id") == "modulo-graph":
            candidate = element.text or element.attrib.get("data-graph")
            break
        if "data-modulo-graph" in element.attrib:
            candidate = element.attrib["data-modulo-graph"]
            break
    if not candidate:
        raise ValidationAPIError("SVG must include JSON metadata with id=modulo-graph", ["missing_modulo_graph"])
    try:
        return graph_from_payload(json.loads(html.unescape(candidate)))
    except json.JSONDecodeError as exc:
        raise ValidationAPIError("modulo-graph SVG metadata is not valid JSON", ["svg_metadata"]) from exc


def _plain_value(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html.unescape(value or ""))).strip()


def _drawio_type(style: str, label: str) -> str:
    style = (style or "").lower()
    if "rhombus" in style or "diamond" in style:
        return "decision"
    if "parallelogram" in style:
        return "input_output"
    if "ellipse" in style or "terminator" in style:
        return canonical_type("start_end", label)
    return "process"


def parse_drawio(data: bytes) -> Graph:
    root = _secure_xml(data)
    cells = [element for element in root.iter() if _tag(element) == "mxCell"]
    if not cells:
        raise ValidationAPIError("draw.io XML has no mxCell elements", ["drawio_cells"])
    nodes: list[Node] = []
    edges: list[Edge] = []
    for cell in cells:
        attrs = cell.attrib
        if attrs.get("vertex") == "1":
            geometry = next((child for child in cell if _tag(child) == "mxGeometry"), None)
            geometry_attrs = geometry.attrib if geometry is not None else {}
            nodes.append(Node(
                id=attrs.get("id", ""), type=_drawio_type(attrs.get("style", ""), _plain_value(attrs.get("value", ""))),
                label=_plain_value(attrs.get("value", "")),
                x=_number(geometry_attrs.get("x", 0)),
                y=_number(geometry_attrs.get("y", 0)),
                confidence=1.0,
            ))
        elif attrs.get("edge") == "1":
            edges.append(Edge(attrs.get("id", ""), attrs.get("source", ""), attrs.get("target", ""), _plain_value(attrs.get("value", ""))))
    return Graph("Imported draw.io flowchart", nodes, edges)
