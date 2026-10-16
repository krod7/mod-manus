# Modulo — Software Requirements Specification

Version 0.1 · 2026-10-16

## Purpose and operating modes

Modulo converts an existing, single-page flowchart into a reviewable graph, validated logic, pseudocode and executable Python/JavaScript. Its primary actor is a person who owns or is authorized to process the uploaded flowchart. The browser interface requires no account. GitHub Pages hosts the static frontend; a separately deployed Python API provides raster/PDF recognition and optional server compilation.

The diagram is a program specification, not a license to invent the implementation of named business tasks. The supported language is intentionally small. Clean visual recognition remains best-effort and must be reviewed.

## File intake

FR-01. The user can choose or drop exactly one file. Supported browser-only files are JSON, Modulo-annotated SVG, uncompressed single-page draw.io XML, and the documented Mermaid subset. PNG/JPEG and exactly one-page PDF require the Python API. Reject empty, unsupported and greater-than-10-MiB files with actionable messages. The Python intake checks byte signatures and image/PDF validity; image recognition is capped at 16 megapixels.

FR-02. The original file can be previewed, replaced or removed. Removing the preview retains the reconstructed graph. Originals remain in memory only and are not persisted with browser projects. A reload must not imply that a missing original was retained.

## Recognition and review

FR-03. Recognize candidate node shapes, printed labels and simple arrowed connectors using local computer vision/OCR. Conservatively label uncertain regions and omit directions without sufficient evidence. Return the actual method and a review-required flag. Do not claim success for arbitrary handwriting, crossings or unavailable services.

FR-04. Reconstruct the graph on an interactive canvas. The user can select nodes/connections, drag nodes, pan/zoom/fit the graph, edit labels and types, add/remove nodes and connections, attach notes, and undo/redo graph edits. A graph may have at most 100 nodes and 300 edges. Nodes and edges have stable IDs.

FR-05. Validate exactly one Start, at least one End, unique identifiers, defined connection endpoints, reachability, outgoing edge cardinality, labeled binary decisions and a possible route to End. Warn about cycles and uncertainty. Validate executable label syntax and definite variable assignment before browser compilation. Every image/PDF import requires an explicit review acknowledgment before generation.

## Logic, source and tracing

FR-06. Support explicit inputs, assignments, outputs, comparisons, arithmetic, Boolean expressions, sequence, binary branches, merges and loops. Unknown operations such as “Send email” block generation. Decisions must use Yes/No or True/False. Preserve graph control flow using a bounded state-machine representation.

FR-07. Generate readable state-machine pseudocode and executable Python or JavaScript. Clearly identify the language and artifact state. Provide source/pseudocode/trace-map tabs, copy and downloads. Changes to logic invalidate source and tracing until regeneration. Surface API/compiler errors without replacing them with fabricated output.

FR-08. Trace node and connection IDs to one-based code and pseudocode regions. Selecting any mapped artifact highlights the corresponding graph element and source region. Both branches of a decision can share a conditional code region. Selection on code and pseudocode follows the containing node.

FR-09. Provide a bounded browser graph interpreter for local execution with typed input values. Show outputs, final variables and the visited node sequence. Enforce a 10,000-step limit. Do not evaluate uploaded source or run it on the server.

## Workspace and interaction

FR-10. Provide a guided progression: import, recognize, review/validate, generate and completion; generation internally includes logic interpretation, pseudocode and trace generation. Status indicators reflect real work, not staged fake recognition. Provide responsive diagram/source panels and a keyboard-operable dialog interface.

FR-11. Keep multiple graphs and notes in local browser storage; expose saving failures. JSON/SVG exports support backups and manual file sharing. No live collaboration, cloud account synchronization or public sharing URLs are implied.

## Nonfunctional requirements

NFR-01. All frontend assets use relative URLs and no client secrets. The frontend deploys as `frontend/` through GitHub Actions and runs without npm dependencies. Python is not required in Pages mode.

NFR-02. Parse only the supported expression grammar. Reject calls, indexing, property access and dangerous identifiers. Escape user content before rendering. Avoid rendering arbitrary uploaded SVG markup. Restrict static serving to `frontend/`. Protect publicly hosted OCR through deployment-level authentication/rate/resource limits; CORS alone is not protection.

NFR-03. Provide stable IDs, documented one-based trace indexing, independent services and reusable fixtures. Include SRS, SDS and editable UML, MIT license, a drawing guide, service-level tests and portable regression tests.

NFR-04. Follow the approved Blueprint Terminal design with navy #123B5D, teal #39D0C3, IBM Plex Mono for code and IBM Plex Sans for interface text. Respect reduced motion, accessible labels, contrast and mobile stacking.

## Feature scope

The FlowMapp reference informs common visual mapping functions, not proprietary implementation or branding. Live multiplayer, its full icon library, embedded collaborative image objects, sitemap integration and hosted sharing are outside this delivered static release. See [FLOWMAPP.md](FLOWMAPP.md) for the sourced mapping.
