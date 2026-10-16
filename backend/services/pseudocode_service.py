"""Generate readable state-machine pseudocode from validated instructions."""
from __future__ import annotations

from dataclasses import dataclass

from backend.models import Edge, Graph
from backend.services.logic_service import Instruction


@dataclass
class GeneratedPseudocode:
    source: str
    node_lines: dict[str, list[int]]


def _outgoing(graph: Graph) -> dict[str, list[Edge]]:
    table = {node.id: [] for node in graph.nodes}
    for edge in graph.edges:
        table[edge.source].append(edge)
    return table


def _next(edges: list[Edge], labels: set[str] | None = None) -> str:
    edge = next((item for item in edges if labels is None or item.label.strip().lower() in labels), None)
    return edge.target if edge else "<invalid>"


def generate_pseudocode(graph: Graph, instructions: dict[str, Instruction]) -> GeneratedPseudocode:
    start = next(node.id for node in graph.nodes if node.type == "start")
    outgoing = _outgoing(graph)
    lines = [f"SET state ← '{start}'", "SET steps ← 0", "WHILE state IS NOT null AND steps < maxSteps", "  SET steps ← steps + 1"]
    node_lines: dict[str, list[int]] = {}
    for node in graph.nodes:
        instruction = instructions[node.id]
        begin = len(lines) + 1
        lines.append(f"  STATE '{node.id}':")
        edges = outgoing[node.id]
        if instruction.kind == "start":
            lines.append(f"    SET state ← '{_next(edges)}'")
        elif instruction.kind == "end":
            lines.append("    SET state ← null")
        elif instruction.kind == "input":
            suffix = f" AS {instruction.input_type.upper()}" if instruction.input_type else ""
            lines.append(f"    READ {instruction.variable}{suffix} INTO {instruction.variable}")
            lines.append(f"    SET state ← '{_next(edges)}'")
        elif instruction.kind == "output":
            lines.append(f"    WRITE {node.label[7:].strip()}")
            lines.append(f"    SET state ← '{_next(edges)}'")
        elif instruction.kind == "assignment":
            lines.append(f"    {node.label.strip()}")
            lines.append(f"    SET state ← '{_next(edges)}'")
        elif instruction.kind == "decision":
            lines.append(f"    IF {node.label.strip()} THEN SET state ← '{_next(edges, {'yes', 'true'})}'")
            lines.append(f"    ELSE SET state ← '{_next(edges, {'no', 'false'})}'")
        node_lines[node.id] = list(range(begin, len(lines) + 1))
    lines.extend(["END WHILE", "IF steps ≥ maxSteps THEN RAISE step-limit error"])
    return GeneratedPseudocode("\n".join(lines) + "\n", node_lines)
