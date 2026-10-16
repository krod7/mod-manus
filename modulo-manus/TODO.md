# Modulo — approved outcomes

- [x] Single-page flowchart file intake with drag-and-drop or file selection, file-type and page-count checks, replacement/removal controls, and clear validation errors. PNG/JPEG/PDF images use the separately hosted Python recognition API; JSON, annotated SVG, draw.io XML and the documented Mermaid subset work on static Pages.
- [x] Guided stages: upload, recognition, graph extraction, validation, logic interpretation, pseudocode, code generation, completion. Never fabricate successful recognition or silently assume an uncertain branch.
- [x] Recognition identifies nodes, labels, connectors, directions, decisions, branches, start/end points and relationships. Image recognition is best-effort OCR/computer vision and requires explicit graph review; arbitrary handwriting and crossing connectors are not guaranteed.
- [x] Interactive inferred-graph review: selection, element inspection, correction of labels/types/connections, structural and ambiguous-region feedback, pan/zoom, notes and local multiple projects.
- [x] Graph and logic validation: disconnected/unreachable nodes, missing paths, decisions, loops, uncertainty and actionable errors. Preserve sequence, branches and loops in a graph state-machine compiler.
- [x] Pseudocode and executable Python/JavaScript with language label, formatted source, copy/download, surfaced errors and bounded local graph simulation without executing user source.
- [x] Bidirectional node/edge-to-code/pseudocode traceability, responsive split view, synchronization, progress and errors in the confirmed Blueprint Terminal design (navy #123B5D, teal #39D0C3, IBM Plex Mono).
- [x] Exact requested frontend/backend service skeleton, MIT license, README install/run/proper drawing guide, requirements, runner, SRS/SDS/UML, examples, fixtures and a test file per service. Include GitHub Actions Pages deployment workflow using only frontend static output; document separate API CORS and no frontend secrets.
- [x] Complete independent read-only integration review and correct confirmed defects. Preserve clear distinctions from FlowMapp: functional inspiration, no copied proprietary UI/assets and no claimed live collaboration parity.

## Reference findings

FlowMapp's reference describes shapes/lines/icons, embedded images, custom attributes, flexible connections, an 80+ icon library, notes, multiple flows, export, sharing and realtime collaboration. Modulo applies visual shapes/connections, editable node appearance/notes, imported source preview, multiple local projects and portable exports. Real-time multiplayer and hosted sharing require a separate service and are not included in the static application.

Sources read: https://www.flowmapp.com/features/user-flow-ux-tool and https://docs.github.com/en/pages/getting-started-with-github-pages/about-github-pages (2026-10-16). GitHub Pages serves static HTML/CSS/JS, not the Python service.

## Delivery evidence

29 Python tests and 15 portable compiler tests passed. Repository-root Pyright reports zero errors/warnings. Focused Chromium regressions passed for actual node/edge traces, invalid import recovery, atomic replacement, API generation locking, SVG export, simulation and persistence. Real OCR sample detects five candidates and four directed edges; recognition remains review-required. Detailed evidence and release boundaries are in docs/VALIDATION.md and docs/RELEASE.md.
