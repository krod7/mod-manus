"""Emit executable, bounded state-machine programs from validated graph instructions."""
from __future__ import annotations

import json
from dataclasses import dataclass

from backend.models import Edge, Graph
from backend.services.logic_service import Instruction, javascript_expression, python_expression


@dataclass
class GeneratedCode:
    source: str
    node_lines: dict[str, list[int]]


def _outgoing(graph: Graph) -> dict[str, list[Edge]]:
    result: dict[str, list[Edge]] = {node.id: [] for node in graph.nodes}
    for edge in graph.edges:
        result[edge.source].append(edge)
    return result


def _targets(edges: list[Edge]) -> tuple[str | None, str | None]:
    yes = next((edge.target for edge in edges if edge.label.strip().lower() in {"yes", "true"}), None)
    no = next((edge.target for edge in edges if edge.label.strip().lower() in {"no", "false"}), None)
    return yes, no


def _python(graph: Graph, instructions: dict[str, Instruction]) -> GeneratedCode:
    outgoing = _outgoing(graph)
    start = next(node.id for node in graph.nodes if node.type == "start")
    lines = [
        "import math",
        "def run(inputs=None, max_steps=10000):",
        "    \"\"\"Execute the flowchart with caller-supplied input values.\"\"\"",
        "    env = dict(inputs or {})",
        "    output = []",
        f"    state = {start!r}",
        "    steps = 0",
        "    while state is not None:",
        "        if steps >= max_steps:",
        "            raise RuntimeError('flowchart step limit exceeded')",
        "        steps += 1",
    ]
    node_lines: dict[str, list[int]] = {}
    for index, node in enumerate(graph.nodes):
        instruction = instructions[node.id]
        beginning = len(lines) + 1
        prefix = "if" if index == 0 else "elif"
        lines.append(f"        {prefix} state == {node.id!r}:")
        edges = outgoing[node.id]
        if instruction.kind == "end":
            lines.append("            state = None")
        elif instruction.kind == "decision":
            assert instruction.expression is not None
            yes, no = _targets(edges)
            lines.append(f"            if {python_expression(instruction.expression)}:")
            lines.append(f"                state = {yes!r}")
            lines.append("            else:")
            lines.append(f"                state = {no!r}")
        else:
            if instruction.kind == "input":
                variable = instruction.variable
                assert variable is not None
                lines.append(f"            if {variable!r} not in env:")
                lines.append(f"                raise ValueError('Missing input: {variable}')")
                if instruction.input_type == "number":
                    lines.append(f"            env[{variable!r}] = float(env[{variable!r}])")
                    lines.append(f"            if not math.isfinite(env[{variable!r}]): raise ValueError('Input must be finite')")
                elif instruction.input_type in {"text", "string"}:
                    lines.append(f"            env[{variable!r}] = str(env[{variable!r}])")
                elif instruction.input_type == "boolean":
                    lines.append(f"            if not isinstance(env[{variable!r}], bool): raise ValueError('Input must be boolean')")
            elif instruction.kind == "output":
                assert instruction.expression is not None
                lines.append(f"            output.append({python_expression(instruction.expression)})")
            elif instruction.kind == "assignment":
                assert instruction.variable is not None
                assert instruction.expression is not None
                lines.append(f"            env[{instruction.variable!r}] = {python_expression(instruction.expression)}")
            # start has no operation, but still transitions below.
            lines.append(f"            state = {edges[0].target!r}")
        node_lines[node.id] = list(range(beginning, len(lines) + 1))
    lines.extend([
        "        else:",
        "            raise RuntimeError('unknown flowchart state')",
        "    return {'output': output, 'variables': env, 'steps': steps}",
    ])
    return GeneratedCode("\n".join(lines) + "\n", node_lines)


def _javascript(graph: Graph, instructions: dict[str, Instruction]) -> GeneratedCode:
    outgoing = _outgoing(graph)
    start = next(node.id for node in graph.nodes if node.type == "start")
    q = json.dumps
    lines = [
        "'use strict';",
        "function _get(env, key) {",
        "  if (!Object.prototype.hasOwnProperty.call(env, key)) throw new Error('Variable ' + key + ' is not defined; add an INPUT or assignment before use');",
        "  return env[key];",
        "}",
        "function _number(value, operator) {",
        "  if (typeof value !== 'number' || !Number.isFinite(value)) throw new Error(operator + ' requires finite numbers');",
        "  return value;",
        "}",
        "function _mod(left, right) {",
        "  const a = _number(left, 'Modulo');",
        "  const b = _number(right, 'Modulo');",
        "  if (b === 0) throw new Error('Modulo by zero');",
        "  return ((a % b) + b) % b;",
        "}",
        "function _divide(left, right) {",
        "  const a = _number(left, 'Division');",
        "  const b = _number(right, 'Division');",
        "  if (b === 0) throw new Error('Division by zero');",
        "  return a / b;",
        "}",
        "function run(inputs = {}, maxSteps = 10000) {",
        "  const env = Object.assign(Object.create(null), inputs || {});",
        "  const output = [];",
        f"  let state = {q(start)};",
        "  let steps = 0;",
        "  while (state !== null) {",
        "    if (steps >= maxSteps) throw new Error('flowchart step limit exceeded');",
        "    steps += 1;",
    ]
    node_lines: dict[str, list[int]] = {}
    for index, node in enumerate(graph.nodes):
        instruction = instructions[node.id]
        beginning = len(lines) + 1
        prefix = "if" if index == 0 else "else if"
        lines.append(f"    {prefix} (state === {q(node.id)}) {{")
        edges = outgoing[node.id]
        if instruction.kind == "end":
            lines.append("      state = null;")
        elif instruction.kind == "decision":
            assert instruction.expression is not None
            yes, no = _targets(edges)
            lines.append(f"      if ({javascript_expression(instruction.expression)}) {{")
            lines.append(f"        state = {q(yes)};")
            lines.append("      } else {")
            lines.append(f"        state = {q(no)};")
            lines.append("      }")
        else:
            if instruction.kind == "input":
                variable = instruction.variable
                assert variable is not None
                lines.append(f"      if (!Object.prototype.hasOwnProperty.call(env, {q(variable)})) throw new Error('Missing input: {variable}');")
                if instruction.input_type == "number":
                    lines.append(f"      if (String(env[{q(variable)}]).trim() === '' || env[{q(variable)}] === null) throw new Error('Input must be a number');")
                    lines.append(f"      env[{q(variable)}] = Number(env[{q(variable)}]);")
                    lines.append(f"      if (!Number.isFinite(env[{q(variable)}])) throw new Error('Input must be finite');")
                elif instruction.input_type in {"text", "string"}:
                    lines.append(f"      env[{q(variable)}] = String(env[{q(variable)}]);")
                elif instruction.input_type == "boolean":
                    lines.append(f"      if (typeof env[{q(variable)}] !== 'boolean') throw new Error('Input must be boolean');")
            elif instruction.kind == "output":
                assert instruction.expression is not None
                lines.append(f"      output.push({javascript_expression(instruction.expression)});")
            elif instruction.kind == "assignment":
                assert instruction.variable is not None
                assert instruction.expression is not None
                lines.append(f"      env[{q(instruction.variable)}] = {javascript_expression(instruction.expression)};")
            lines.append(f"      state = {q(edges[0].target)};")
        lines.append("    }")
        node_lines[node.id] = list(range(beginning, len(lines) + 1))
    lines.extend([
        "    else { throw new Error('unknown flowchart state'); }",
        "  }",
        "  return { output, variables: env, steps };",
        "}",
        "if (typeof module !== 'undefined') module.exports = { run };",
    ])
    return GeneratedCode("\n".join(lines) + "\n", node_lines)


def generate_code(graph: Graph, instructions: dict[str, Instruction], language: str) -> GeneratedCode:
    if language == "python":
        return _python(graph, instructions)
    if language == "javascript":
        return _javascript(graph, instructions)
    raise ValueError("language must be 'python' or 'javascript'")
