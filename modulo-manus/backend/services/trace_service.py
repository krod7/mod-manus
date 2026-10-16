"""Bidirectional node/source trace metadata helpers."""
from __future__ import annotations

from backend.models import Graph


def build_trace(graph: Graph, code_lines: dict[str, list[int]], pseudo_lines: dict[str, list[int]]) -> list[dict[str, object]]:
    trace = [
        {"nodeId": node.id, "codeLines": code_lines.get(node.id, []), "pseudoLines": pseudo_lines.get(node.id, [])}
        for node in graph.nodes
    ]
    # A decision's two edges share its conditional region; a sequence edge shares
    # its source state's final transition. Keep edgeId to distinguish selection.
    for edge in graph.edges:
        trace.append({
            "edgeId": edge.id, "nodeId": edge.source,
            "codeLines": code_lines.get(edge.source, []),
            "pseudoLines": pseudo_lines.get(edge.source, []),
        })
    return trace
