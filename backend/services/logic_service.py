"""Safe interpretation of the small Modulo flowchart label language.

No generated expression is evaluated on the server.  Parsing produces a Python AST only after a
strict token grammar and AST whitelist; generators consume that trusted AST representation.
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from typing import Any

from backend.models import Graph

IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
FORBIDDEN_NAMES = {
    "__proto__", "prototype", "constructor", "eval", "exec", "globals", "locals", "open",
    "import", "require", "process", "window", "global", "this", "function", "class", "lambda",
    "new", "delete", "getattr", "setattr", "compile", "input", "builtins",
}
_INPUT = re.compile(r"^(?:INPUT|READ)\s+([A-Za-z_][A-Za-z0-9_]{0,63})(?:\s*:\s*(number|text|string|boolean))?\s*$", re.I)
_OUTPUT = re.compile(r"^(?:OUTPUT|PRINT|DISPLAY)\s+(.+?)\s*$", re.I | re.S)
_ASSIGNMENT = re.compile(r"^([A-Za-z_][A-Za-z0-9_]{0,63})\s*=\s*(?![=])(.+?)\s*$", re.S)


class LogicError(ValueError):
    pass


@dataclass
class Instruction:
    kind: str
    expression: ast.Expression | None = None
    variable: str | None = None
    input_type: str | None = None


def _assert_name(name: str) -> None:
    if not IDENTIFIER.fullmatch(name) or name in FORBIDDEN_NAMES or "__" in name:
        raise LogicError(f"Unsafe identifier {name!r}")


def _read_string(source: str, index: int) -> tuple[str, int]:
    quote = source[index]
    cursor = index + 1
    escaped = False
    while cursor < len(source):
        char = source[cursor]
        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == quote:
            literal = source[index:cursor + 1]
            try:
                parsed = ast.literal_eval(literal)
            except (ValueError, SyntaxError) as exc:
                raise LogicError("Invalid quoted string literal") from exc
            if not isinstance(parsed, str):
                raise LogicError("Only string literals are allowed")
            return repr(parsed), cursor + 1
        cursor += 1
    raise LogicError("Unterminated string literal")


def _tokens(source: str) -> list[tuple[str, str]]:
    """Tokenize only the intentionally small expression grammar."""
    result: list[tuple[str, str]] = []
    i = 0
    while i < len(source):
        char = source[i]
        if char.isspace():
            i += 1
            continue
        if char in "'\"":
            literal, i = _read_string(source, i)
            result.append(("string", literal))
            continue
        match = re.match(r"(?:\d+\.\d*|\.\d+|\d+)(?:[eE][+-]?\d+)?", source[i:])
        if match:
            value = match.group(0)
            result.append(("number", value))
            i += len(value)
            continue
        match = re.match(r"[A-Za-z_][A-Za-z0-9_]*", source[i:])
        if match:
            value = match.group(0)
            result.append(("identifier", value))
            i += len(value)
            continue
        operation = next((op for op in ("==", "!=", ">=", "<=", "&&", "||", "+", "-", "*", "/", "%", ">", "<", "!", "(", ")") if source.startswith(op, i)), None)
        if operation is None:
            raise LogicError(f"Unsupported character in expression: {char!r}")
        result.append(("operator", operation))
        i += len(operation)
    if not result:
        raise LogicError("Expression cannot be empty")
    return result


def _python_source(tokens: list[tuple[str, str]]) -> str:
    translated: list[str] = []
    for kind, value in tokens:
        if kind == "identifier":
            lowered = value.lower()
            if lowered == "true":
                translated.append("True")
            elif lowered == "false":
                translated.append("False")
            elif lowered in {"null", "none"}:
                translated.append("None")
            elif lowered in {"and", "or", "not"}:
                translated.append(lowered)
            else:
                _assert_name(value)
                translated.append(value)
        elif value == "&&":
            translated.append("and")
        elif value == "||":
            translated.append("or")
        elif value == "!":
            translated.append("not")
        else:
            translated.append(value)
    return " ".join(translated)


class _ExpressionValidator(ast.NodeVisitor):
    def visit_Expression(self, node: ast.Expression) -> Any:
        self.visit(node.body)

    def visit_Name(self, node: ast.Name) -> Any:
        _assert_name(node.id)

    def visit_Constant(self, node: ast.Constant) -> Any:
        if not isinstance(node.value, (str, int, float, bool, type(None))):
            raise LogicError("Unsupported literal")

    def visit_BinOp(self, node: ast.BinOp) -> Any:
        if not isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod)):
            raise LogicError("Unsupported arithmetic operator")
        self.visit(node.left)
        self.visit(node.right)

    def visit_UnaryOp(self, node: ast.UnaryOp) -> Any:
        if not isinstance(node.op, (ast.UAdd, ast.USub, ast.Not)):
            raise LogicError("Unsupported unary operator")
        self.visit(node.operand)

    def visit_BoolOp(self, node: ast.BoolOp) -> Any:
        if not isinstance(node.op, (ast.And, ast.Or)):
            raise LogicError("Unsupported boolean operator")
        for value in node.values:
            self.visit(value)

    def visit_Compare(self, node: ast.Compare) -> Any:
        if not all(isinstance(op, (ast.Eq, ast.NotEq, ast.Gt, ast.GtE, ast.Lt, ast.LtE)) for op in node.ops):
            raise LogicError("Unsupported comparison operator")
        self.visit(node.left)
        for comparator in node.comparators:
            self.visit(comparator)

    def generic_visit(self, node: ast.AST) -> Any:
        raise LogicError(f"Unsupported expression construct: {type(node).__name__}")


def parse_expression(source: str) -> ast.Expression:
    try:
        parsed = ast.parse(_python_source(_tokens(source)), mode="eval")
    except SyntaxError as exc:
        raise LogicError("Expression syntax is invalid") from exc
    _ExpressionValidator().visit(parsed)
    return parsed


def clean_condition(label: str) -> str:
    return re.sub(r"^(?:IF|WHILE|DECISION)\s+", "", label.strip(), flags=re.I).rstrip("?").strip()


def _expression_names(instruction: Instruction) -> set[str]:
    if instruction.expression is None:
        return set()
    return {node.id for node in ast.walk(instruction.expression) if isinstance(node, ast.Name)}


def _definite_assignment_errors(graph: Graph, instructions: dict[str, Instruction]) -> list[str]:
    """Return must-assignment errors using a greatest fixed point over reachable nodes.

    ``before[node]`` is the set of variables available on *every* path into that
    node.  Starting non-start states at the complete name universe is important:
    it allows a back edge to contribute only variables that are guaranteed on the
    first visit as well as later loop iterations.
    """
    starts = [node.id for node in graph.nodes if node.type == "start"]
    if len(starts) != 1:
        # Structural validation normally rejects this before interpretation.
        return []
    start = starts[0]
    node_ids = {node.id for node in graph.nodes}
    outgoing: dict[str, list[str]] = {node_id: [] for node_id in node_ids}
    incoming: dict[str, list[str]] = {node_id: [] for node_id in node_ids}
    for edge in graph.edges:
        if edge.source in node_ids and edge.target in node_ids:
            outgoing[edge.source].append(edge.target)
            incoming[edge.target].append(edge.source)

    reachable = {start}
    pending = [start]
    while pending:
        source = pending.pop()
        for target in outgoing[source]:
            if target not in reachable:
                reachable.add(target)
                pending.append(target)

    universe = set().union(*(_expression_names(item) for item in instructions.values()))
    universe.update(item.variable for item in instructions.values() if item.variable is not None)
    before = {
        node_id: (set() if node_id == start else set(universe))
        for node_id in reachable
    }
    after = {
        node_id: before[node_id] | ({instructions[node_id].variable} if instructions[node_id].kind in {"input", "assignment"} else set())
        for node_id in reachable
    }

    # Each transfer function only removes names from a finite set, so this
    # work-list-style iteration terminates even for graphs with back edges.
    changed = True
    while changed:
        changed = False
        for node in graph.nodes:
            node_id = node.id
            if node_id not in reachable:
                continue
            parents = [parent for parent in incoming[node_id] if parent in reachable]
            current_before = set() if node_id == start or not parents else set.intersection(*(after[parent] for parent in parents))
            instruction = instructions[node_id]
            current_after = current_before | ({instruction.variable} if instruction.kind in {"input", "assignment"} else set())
            if current_before != before[node_id] or current_after != after[node_id]:
                before[node_id] = current_before
                after[node_id] = current_after
                changed = True

    errors: list[str] = []
    for node in graph.nodes:
        if node.id not in reachable:
            continue
        missing = sorted(_expression_names(instructions[node.id]) - before[node.id])
        for name in missing:
            errors.append(
                f"Node {node.id}: Variable {name!r} is not assigned on every incoming path; "
                "add an INPUT or assignment before this expression"
            )
    return errors


def interpret_graph(graph: Graph) -> dict[str, Instruction]:
    """Turn labels into typed instructions or raise all known conversion-blocking errors."""
    instructions: dict[str, Instruction] = {}
    errors: list[str] = []
    for node in graph.nodes:
        try:
            label = node.label.strip()
            if node.type in {"start", "end"}:
                instructions[node.id] = Instruction(node.type)
            elif node.type == "decision":
                instructions[node.id] = Instruction("decision", expression=parse_expression(clean_condition(label)))
            elif node.type in {"input", "input_output"} and _INPUT.fullmatch(label):
                match = _INPUT.fullmatch(label)
                assert match is not None
                _assert_name(match.group(1))
                instructions[node.id] = Instruction("input", variable=match.group(1), input_type=(match.group(2) or "number").lower())
            elif node.type in {"output", "input_output"} and _OUTPUT.fullmatch(label):
                match = _OUTPUT.fullmatch(label)
                assert match is not None
                instructions[node.id] = Instruction("output", expression=parse_expression(match.group(1)))
            elif node.type == "process" and _ASSIGNMENT.fullmatch(label):
                match = _ASSIGNMENT.fullmatch(label)
                assert match is not None
                _assert_name(match.group(1))
                instructions[node.id] = Instruction("assignment", expression=parse_expression(match.group(2)), variable=match.group(1))
            else:
                raise LogicError("Unknown named operation; use INPUT, OUTPUT, assignment, or a decision expression")
        except LogicError as exc:
            errors.append(f"Node {node.id}: {exc}")
    if errors:
        raise LogicError("; ".join(errors))
    errors = _definite_assignment_errors(graph, instructions)
    if errors:
        raise LogicError("; ".join(errors))
    return instructions


class _EnvSubstitution(ast.NodeTransformer):
    def visit_Name(self, node: ast.Name) -> ast.AST:
        return ast.copy_location(
            ast.Subscript(value=ast.Name(id="env", ctx=ast.Load()), slice=ast.Constant(node.id), ctx=ast.Load()),
            node,
        )


def python_expression(expression: ast.Expression) -> str:
    """Render from the validated AST, substituting every user variable with env[name]."""
    transformed = _EnvSubstitution().visit(ast.fix_missing_locations(ast.parse(ast.unparse(expression.body), mode="eval")))
    return ast.unparse(ast.fix_missing_locations(transformed.body))


class _JavaScriptExpression(ast.NodeVisitor):
    def render(self, expression: ast.Expression) -> str:
        return self.visit(expression.body)

    def visit_Name(self, node: ast.Name) -> str:
        return f'_get(env, {node.id!r})'

    def visit_Constant(self, node: ast.Constant) -> str:
        if node.value is None:
            return "null"
        if node.value is True:
            return "true"
        if node.value is False:
            return "false"
        return repr(node.value) if isinstance(node.value, str) else str(node.value)

    def visit_BinOp(self, node: ast.BinOp) -> str:
        if isinstance(node.op, ast.Mod):
            return f"_mod({self.visit(node.left)}, {self.visit(node.right)})"
        if isinstance(node.op, ast.Div):
            return f"_divide({self.visit(node.left)}, {self.visit(node.right)})"
        symbols = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*"}
        return f"({self.visit(node.left)} {symbols[type(node.op)]} {self.visit(node.right)})"

    def visit_UnaryOp(self, node: ast.UnaryOp) -> str:
        symbol = "!" if isinstance(node.op, ast.Not) else ("+" if isinstance(node.op, ast.UAdd) else "-")
        return f"({symbol}{self.visit(node.operand)})"

    def visit_BoolOp(self, node: ast.BoolOp) -> str:
        symbol = " && " if isinstance(node.op, ast.And) else " || "
        return "(" + symbol.join(self.visit(value) for value in node.values) + ")"

    def visit_Compare(self, node: ast.Compare) -> str:
        symbols = {ast.Eq: "===", ast.NotEq: "!==", ast.Gt: ">", ast.GtE: ">=", ast.Lt: "<", ast.LtE: "<="}
        left = self.visit(node.left)
        pieces: list[str] = []
        for op, comparator in zip(node.ops, node.comparators):
            right = self.visit(comparator)
            pieces.append(f"({left} {symbols[type(op)]} {right})")
            left = right
        return " && ".join(pieces)


def javascript_expression(expression: ast.Expression) -> str:
    return _JavaScriptExpression().render(expression)
