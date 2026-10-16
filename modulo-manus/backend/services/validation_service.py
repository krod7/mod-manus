"""Graph-only validation.  This service never evaluates user labels as code."""
from __future__ import annotations

import math
import re
from collections import defaultdict, deque
from dataclasses import dataclass, field

from backend.config import MAX_EDGES, MAX_ID_LENGTH, MAX_LABEL_LENGTH, MAX_NODES
from backend.models import Graph

ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
ALLOWED_TYPES = {"start", "end", "process", "decision", "input_output", "input", "output"}


@dataclass
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict[str, list[str]]:
        return {"errors": self.errors, "warnings": self.warnings}


def _cycle_nodes(graph: Graph, outgoing: dict[str, list[str]]) -> set[str]:
    visiting: set[str] = set()
    visited: set[str] = set()
    cycle: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            cycle.update(visiting)
            return
        if node in visited:
            return
        visiting.add(node)
        for target in outgoing[node]:
            visit(target)
        visiting.remove(node)
        visited.add(node)

    for item in (node.id for node in graph.nodes):
        visit(item)
    return cycle


def validate_graph(graph: Graph) -> ValidationResult:
    result = ValidationResult()
    if len(graph.nodes) > MAX_NODES:
        result.errors.append(f"Graph has more than {MAX_NODES} nodes")
    if len(graph.edges) > MAX_EDGES:
        result.errors.append(f"Graph has more than {MAX_EDGES} edges")
    if not graph.nodes:
        result.errors.append("Graph must contain nodes")
        return result

    ids = [node.id for node in graph.nodes]
    seen: set[str] = set()
    for node in graph.nodes:
        if not ID_RE.fullmatch(node.id or "") or len(node.id) > MAX_ID_LENGTH:
            result.errors.append(f"Invalid node id: {node.id!r}")
        elif node.id in seen:
            result.errors.append(f"Duplicate node id: {node.id}")
        seen.add(node.id)
        if node.type not in ALLOWED_TYPES:
            result.errors.append(f"Node {node.id} has unsupported type {node.type!r}")
        if len(node.label) > MAX_LABEL_LENGTH:
            result.errors.append(f"Node {node.id} label exceeds {MAX_LABEL_LENGTH} characters")
        if not (0 <= node.confidence <= 1) or not math.isfinite(node.confidence):
            result.errors.append(f"Node {node.id} has invalid confidence")
        elif node.confidence < 0.8:
            result.warnings.append(f"Node {node.id} has low recognition confidence ({node.confidence:.2f})")

    edge_ids: set[str] = set()
    outgoing: dict[str, list[str]] = defaultdict(list)
    incoming: dict[str, list[str]] = defaultdict(list)
    edge_labels: dict[str, list[str]] = defaultdict(list)
    for edge in graph.edges:
        if not ID_RE.fullmatch(edge.id or ""):
            result.errors.append(f"Invalid edge id: {edge.id!r}")
        elif edge.id in edge_ids:
            result.errors.append(f"Duplicate edge id: {edge.id}")
        edge_ids.add(edge.id)
        if edge.source not in seen or edge.target not in seen:
            result.errors.append(f"Edge {edge.id} has a dangling endpoint")
            continue
        if len(edge.label) > 80:
            result.errors.append(f"Edge {edge.id} label exceeds 80 characters")
        outgoing[edge.source].append(edge.target)
        incoming[edge.target].append(edge.source)
        edge_labels[edge.source].append(edge.label.strip().lower())

    starts = [node for node in graph.nodes if node.type == "start"]
    ends = [node for node in graph.nodes if node.type == "end"]
    if len(starts) != 1:
        result.errors.append("Graph must have exactly one start node")
    if not ends:
        result.errors.append("Graph must have at least one end node")

    for node in graph.nodes:
        degree = len(outgoing[node.id])
        if node.type == "end" and degree:
            result.errors.append(f"End node {node.id} must not have outgoing edges")
        elif node.type == "decision":
            labels = edge_labels[node.id]
            valid = set(labels) == {"yes", "no"} or set(labels) == {"true", "false"}
            if degree != 2 or not valid:
                result.errors.append(f"Decision node {node.id} must have exactly two yes/no or true/false edges")
        elif node.type != "end" and degree != 1:
            result.errors.append(f"Node {node.id} must have exactly one outgoing edge")

    if len(starts) == 1 and starts[0].id in seen:
        start = starts[0].id
        reachable: set[str] = {start}
        queue = deque([start])
        while queue:
            source = queue.popleft()
            for target in outgoing[source]:
                if target not in reachable:
                    reachable.add(target)
                    queue.append(target)
        for node in graph.nodes:
            if node.id not in reachable:
                result.errors.append(f"Node {node.id} is unreachable from start")
        # A reverse walk establishes which nodes can terminate; loop-only states are errors.
        terminating: set[str] = {node.id for node in ends}
        queue = deque(terminating)
        while queue:
            target = queue.popleft()
            for source in incoming[target]:
                if source not in terminating:
                    terminating.add(source)
                    queue.append(source)
        for node_id in reachable - terminating:
            result.errors.append(f"Node {node_id} cannot reach an end node (non-terminating cycle)")

    cycles = _cycle_nodes(graph, outgoing)
    if cycles:
        result.warnings.append("Graph contains loop(s): " + ", ".join(sorted(cycles)))
    return result
