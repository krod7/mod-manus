"""API-level pipeline composition; individual stages remain independently testable."""
from __future__ import annotations

from backend.errors import APIError, ValidationAPIError
from backend.services.codegen_service import generate_code
from backend.services.graph_service import graph_from_payload, parse_annotated_svg, parse_drawio, parse_json
from backend.services.intake_service import Intake, read_upload
from backend.services.logic_service import LogicError, interpret_graph
from backend.services.pseudocode_service import generate_pseudocode
from backend.services.trace_service import build_trace
from backend.services.validation_service import validate_graph
from backend.services.vision_service import recognize


def analyze_upload(file_storage) -> dict:
    intake: Intake = read_upload(file_storage)
    if intake.kind == "json":
        graph = parse_json(intake.data)
        warnings = ["Imported structured JSON; verify semantics before conversion."]
        recognition = {"method": "structured-json import", "needsReview": True}
    elif intake.kind == "svg":
        graph = parse_annotated_svg(intake.data)
        warnings = ["Imported trusted Modulo SVG metadata; verify semantics before conversion."]
        recognition = {"method": "annotated-svg metadata import", "needsReview": True}
    elif intake.kind == "drawio":
        graph = parse_drawio(intake.data)
        warnings = ["Imported uncompressed draw.io XML; inspect inferred shape types and edge labels."]
        recognition = {"method": "drawio-xml import", "needsReview": True}
    else:
        graph, warnings, recognition = recognize(intake)
    structural = validate_graph(graph)
    # Structural failures are feedback for the editable recognition view, not a failed upload.
    warnings.extend(structural.warnings)
    warnings.extend(f"Graph review: {item}" for item in structural.errors)
    return {"graph": graph.to_dict(), "warnings": list(dict.fromkeys(warnings)), "recognition": recognition}


def convert(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValidationAPIError("Request body must be a JSON object", ["request_shape"])
    language = payload.get("language")
    if language not in {"python", "javascript"}:
        raise ValidationAPIError("language must be 'python' or 'javascript'", ["language"])
    graph = graph_from_payload(payload.get("graph"))
    validation = validate_graph(graph)
    if validation.errors:
        raise ValidationAPIError("Graph validation failed", validation.as_dict())
    try:
        instructions = interpret_graph(graph)
    except LogicError as exc:
        raise ValidationAPIError("Flowchart operation validation failed", [str(exc)]) from exc
    pseudo = generate_pseudocode(graph, instructions)
    code = generate_code(graph, instructions, language)
    return {
        "graph": graph.to_dict(), "code": code.source, "pseudocode": pseudo.source,
        "trace": build_trace(graph, code.node_lines, pseudo.node_lines),
        "validation": validation.as_dict(), "language": language,
    }
