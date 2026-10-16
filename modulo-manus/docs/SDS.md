# Modulo — Software Design Specification

Version 0.1 · 2026-10-16

## Deployment architecture

The frontend is plain HTML/CSS/ES modules. GitHub Pages serves `frontend/` without a build. `app.js` orchestrates state and views; `api.js` abstracts browser compilation and an optional remote Python API. `upload.js` parses supported structured formats locally and sends image/PDF files to the API. `run.py` optionally serves the same frontend and Flask API on one origin for local development.

A Pages deployment and a Python deployment are independent. The API URL is saved locally in the browser. An explicitly configured and healthy endpoint can perform compilation; without one, `engine.js` is the compiler. Raster/PDF recognition always requires API health. No API keys, model accounts, database or Manus-specific service are necessary.

## Frontend responsibilities

`engine.js` owns normalization, a recursive bounded expression parser, structure and definite-assignment checks, code/pseudocode generation, trace indexing, Mermaid parsing and the safe graph interpreter. It never invokes `eval` or `Function` on user expressions.

`flowchart-view.js` renders only reconstructed SVG shapes/text, connection paths and graph IDs. It handles pointer-based node movement, panning, zoom/fit, connection selection, keyboard selection and annotated SVG exports. `code-view.js` renders source/pseudocode lines or trace rows; `highlighter.js` escapes and formats tokens and synchronizes one-based line highlights. `status.js` controls progress, validation summaries and accessible notifications.

`app.js` holds projects, the active graph, original source, generated result, selected element and bounded undo/redo stacks. Logic edits clear generated output. Source previews use text or object URLs; arbitrary SVG is not inserted as executable markup. The browser stores graphs and notes, never original upload bytes. Exported project files contain the graph and schema version.

## Python service bus

The pipeline composes independently testable services:

1. `intake_service.py` checks actual bytes, signature/type, upload size, image dimensions and PDF pages.
2. `vision_service.py` rasterizes a one-page PDF if needed, detects bounded contours, OCRs candidates, classifies basic shapes and tests simple Hough connector/arrow evidence. Uncertain direction is omitted, not guessed.
3. `graph_service.py` converts structured data into typed Graph/Node/Edge models and parses annotated SVG/uncompressed draw.io.
4. `validation_service.py` checks graph structure, paths, terminal/decision cardinality and loop warnings.
5. `logic_service.py` converts supported node labels into typed instructions with a strictly validated AST; it never evaluates that AST on the server.
6. `pseudocode_service.py` produces a readable state-machine specification and per-node line positions.
7. `codegen_service.py` emits Python or JavaScript with a 10,000-step default and runtime input checks.
8. `trace_service.py` joins node and source line maps and records edge/source-region associations.

`config.py` owns limits and explicit CORS origins; `errors.py` defines structured service errors. Recognition returns a graph even when structurally incomplete, so the browser can repair it. Conversion rejects invalid graph/logic instead of returning placeholders.

## Graph schema

```json
{
  "name": "Number checker",
  "nodes": [
    {"id": "start", "type": "start", "label": "Start", "x": 330, "y": 48, "confidence": 1, "note": ""}
  ],
  "edges": [
    {"id": "e1", "source": "start", "target": "read", "label": ""}
  ]
}
```

Node types are `start`, `input`, `process`, `decision`, `output`, `end`. The vision API can temporarily return `input_output` when shape classification is ambiguous; the user must choose input or output in review. Confidence ranges from 0 to 1 and signals review needs, not measured semantic accuracy. `x/y` are diagram layout positions, not preserved bounding boxes. IDs remain stable across generation, editing and export.

## HTTP API

`GET /api/health` returns `{"status":"ok","service":"modulo-api"}`. It verifies process availability, not OCR quality or the presence of every system dependency.

`POST /api/analyze` accepts multipart form data with a single `file`. It returns `{graph,warnings,recognition:{method,needsReview:true}}`. It supports image/PDF recognition and structured JSON/SVG/draw.io intake. Recognition warnings include OCR uncertainty and structural issues. Invalid input returns structured 4xx/422; an unavailable recognition dependency returns 503.

`POST /api/convert` accepts `{graph,language:"python"|"javascript"}` and returns `{graph,language,code,pseudocode,trace,validation}`. Trace entries contain `nodeId`, optional `edgeId`, and one-based `codeLines`/`pseudoLines`. Validation uses arrays of errors/warnings. API messages can be strings; browser validation carries node IDs for navigation. The UI handles both.

`OPTIONS` supports explicit CORS preflight for configured localhost/GitHub Pages origins. `MODULO_ALLOWED_ORIGINS` is a comma-separated origin list, not paths or wildcard patterns. The API does not implement authentication/rate limiting and must be placed behind those controls before public use.

## Control-flow and execution semantics

A state-machine compiler emits one state per node and an outgoing target assignment. Decisions emit conditional target selection; back edges implement loops. End returns output. This representation handles arbitrary binary graph control flow without incorrectly guessing nested source structure.

The browser compiler returns an output list from generated `run`; API-generated source additionally returns final variables and steps. These are documented independent output contracts, not server execution. The UI interpreter always displays outputs and final variables independently. Numeric input is the default. Boolean and string inputs are explicit. String/arithmetic coercion and extreme floating-point values can differ across Python and JavaScript; the supported portable use case is finite numeric arithmetic, same-type string concatenation and straightforward comparisons. Review and test exported code before use in a larger application.

The local interpreter has a step limit and parses expressions into nodes. Downloaded code has the same control-flow bound, but should still be treated as user-reviewed generated source. It is never executed by the API.

## Storage, privacy and failure recovery

Graphs and API origin live in `localStorage`. Saving failures remain visible and require export. Original files and preview object URLs are session-memory only; object URLs are revoked when replaced. JSON export is the durable handoff format; SVG also contains re-importable JSON metadata.

API calls omit cookies, use timeouts and surface non-JSON responses. Structured imports work when the API is offline. Remote image recognition failures do not replace the active graph. Generation failure clears stale output. UI selection is local and never transmits source or input values to a third party.
