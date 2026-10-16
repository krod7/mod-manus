"""Small domain models used by the Modulo graph pipeline."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class Node:
    id: str
    type: str
    label: str
    x: float = 0
    y: float = 0
    confidence: float = 1.0
    note: str | None = None
    color: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {key: value for key, value in asdict(self).items() if value is not None}


@dataclass
class Edge:
    id: str
    source: str
    target: str
    label: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Graph:
    name: str
    nodes: list[Node]
    edges: list[Edge]

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "nodes": [node.to_dict() for node in self.nodes], "edges": [edge.to_dict() for edge in self.edges]}
