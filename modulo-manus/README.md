# Modulo

**Visual logic. Real code.** Modulo is an open-source, browser-first workspace that turns explicit flowchart logic into executable Python or JavaScript and lets you trace each generated region back to its node or connection.

The interface uses the Blueprint Terminal direction: a light drafting canvas, navy code surface, teal trace highlights, and IBM Plex typography. It follows common user-flow mapping principles described by [FlowMapp](https://www.flowmapp.com/features/user-flow-ux-tool), without copying its proprietary assets or claiming full feature parity.

## What works

Modulo imports a single flowchart file, reconstructs and validates its graph, lets you edit labels, node types, notes and connections, then generates pseudocode and executable source. Select a node, arrow, code line, pseudocode line or trace-map row to follow its origin. Pan the canvas, drag nodes, zoom, undo/redo edits, simulate execution, and copy or download artifacts. Multiple flows are saved locally in your browser. Export JSON or annotated SVG for backup and file-based sharing.

**GitHub Pages mode is fully static.** JSON, Modulo-annotated SVG, uncompressed draw.io XML and the documented Mermaid subset are processed in your browser. No build, API key or account is required. All asset paths are relative, including under `/repository-name/`.

**PNG/JPEG/PDF recognition requires the Python API.** It uses local OpenCV and Tesseract OCR—not a hosted AI model. It detects candidate shapes and text, and conservatively recognizes simple directed connectors when arrowhead evidence is present. Every raster/PDF import requires source review. Handwriting, crossing arrows, ambiguous directions and arbitrary SVG geometry are not reliably recognized. Uncertain labels, missing connections and unlabeled decision branches must be corrected before generation. It does not silently invent business logic.

This release does **not** include real-time multiplayer, cloud accounts, hosted project-sharing links, FlowMapp’s icon library, website sitemaps, or arbitrary natural-language task implementation. A single-page reference cannot establish every feature of a commercial product; [docs/FLOWMAPP.md](docs/FLOWMAPP.md) records the feature mapping and differences.

## Quick start: static frontend

With Python 3.10+ installed:

```bash
git clone <your-repository-url> modulo
cd modulo
python3 -m http.server 3000 --directory frontend
```

Open `http://localhost:3000`. Try **Example library → Number checker**, select its diamond, switch to Pseudocode or Trace map, and run it with `n = 8` or `n = 7`.

The optional font stylesheet loads from Google Fonts; system fonts are the fallback. No JavaScript runtime libraries or external CDNs are required for conversion. Local persistence uses `localStorage`; private modes and storage quotas can disable it. Export backups, since browser data is not a durable repository.

## Quick start: Python API + frontend

Use Python 3.10+ and a system Tesseract installation. On Ubuntu/Debian:

```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

On macOS, install Tesseract with `brew install tesseract`; on Windows, install a Tesseract distribution and add its executable to `PATH`. Open `http://localhost:3000`. The frontend detects the same-origin API automatically. Set `PORT` to change the listener. `.env.example` documents environment variables; the application reads the process environment, so export variables in your shell or configure them in your host. `.env` files are not loaded automatically.

For a production WSGI host, install your preferred WSGI server separately and serve `backend.app:app` (API only) or `run:app` (API plus frontend). For example, `gunicorn --bind 0.0.0.0:$PORT backend.app:app` after installing Gunicorn. The included Flask development server is **not** a production server. Configure HTTPS, authentication or an API gateway, request/CPU limits and rate limiting before exposing OCR to the public. No hosting service or credentials are bundled.

## Deploy to GitHub Pages

1. Upload this repository to GitHub with the default branch named `main`.
2. In **Settings → Pages → Build and deployment**, select **GitHub Actions** as the source.
3. The supplied `.github/workflows/pages.yml` runs the portable compiler tests and deploys only `frontend/`. It triggers on pushes to `main` or manually through Actions.
4. Open the URL returned by the deployment, typically `https://<owner>.github.io/<repository>/`.

[GitHub Pages is a static hosting service](https://docs.github.com/en/pages/getting-started-with-github-pages/about-github-pages); it cannot run `run.py`, Flask, Tesseract or Python services. To recognize raster/PDF uploads, deploy the API on a separate Python-capable host and set:

```bash
export MODULO_ALLOWED_ORIGINS=https://<owner>.github.io
```

In Modulo, open **API connection**, enter the API’s HTTPS base address, and click **Save & test connection**. An origin contains the scheme and host, **not** the repository subpath. The default CORS list allows only localhost origins; configured values are restricted to explicit localhost or GitHub Pages domains. Custom Pages domains need an intentional update to `backend/config.py` before use. CORS is not authentication and does not stop non-browser clients.

Never place provider keys or secrets in the frontend or GitHub Pages artifacts. Modulo uses no provider keys. The API URL is browser configuration, not a secret. Original uploads are kept in memory and are sent only to the connected recognition endpoint. Source previews do not survive a page reload; the reconstructed graph does.

## How to draw a proper flowchart

Use exactly one **Start** and at least one **End**. Start/End are rounded terminals, assignments are rectangles, decisions are diamonds, and inputs/outputs are parallelograms. Use clear, high-contrast boundaries, printed text, sufficient resolution and arrowheads. Avoid overlapping connectors and crossings. Attach one file, one page, no more than 10 MiB; image recognition is capped at 16 megapixels. Graphs are limited to 100 nodes and 300 connections.

Make every operation explicit:

```text
Start
INPUT n                   # number by default
INPUT name: string
INPUT approved: boolean
total = total + 1
n % 2 == 0?               # decision expression
OUTPUT "Even"
OUTPUT total
End
```

Comments above illustrate grammar; do not put those comments inside your node labels. Variables must be defined on every incoming path before use. Each decision needs exactly two outgoing connections, labeled **Yes/No** or **True/False**. Every other non-End node has exactly one outgoing connection. End nodes have no outgoing arrows. Branches may merge and loops are supported, but there must be a path to an End.

Expressions support numeric and quoted string literals, identifiers, `+ - * / %`, `== != > >= < <=`, parentheses, and `and/or/not` or `&&/||/!`. Use separate comparisons joined by Boolean operators rather than chained comparisons. Arithmetic is intended for finite numeric values; string concatenation uses `+` between strings. Calls, property access, indexing, arbitrary source and dangerous identifiers are rejected. Use numeric literals such as `1.8`, not exponents, in the portable subset.

**“Send email”, “Authorize a purchase”, and “Validate account” are not executable implementations.** This compiler deliberately blocks unspecified operations. Define an explicit supported algorithm or implement external application functions yourself.

A Mermaid example:

```mermaid
flowchart TD
S([Start]) --> I[/INPUT n/]
I --> D{n > 0?}
D -->|Yes| Y[OUTPUT "Positive"]
D -->|No| N[OUTPUT "Not positive"]
Y --> E([End])
N --> E
```

Save as `.mmd`, `.mermaid` or `.txt`. Only one edge per line is supported; subgraphs, chained arrows, style directives and complex node syntax are not. For draw.io, use **File → Export as → XML**, uncheck **Compressed**, and keep one page. Ordinary SVG files must be exported with Modulo’s embedded `metadata#modulo-graph`; the importer does not pretend SVG geometry is a semantic graph.

## Generated programs and traceability

Modulo emits a bounded **graph state machine** instead of trying to force arbitrary control-flow graphs into nested `if` blocks. Each node corresponds to a state; decisions select their Yes/No targets, and back edges preserve loops. This is executable code, not placeholders. The default runtime limit is 10,000 node steps.

The portable compiler’s Python and JavaScript `run` function returns the output list:

```python
# After saving the Number checker Python output as number_checker.py:
from number_checker import run
print(run({"n": 8}))  # ["Even"]
```

```javascript
// After loading/pasting the generated JavaScript:
console.log(run({ n: 7 })); // ["Odd"]
```

The separately callable Python API’s generated programs return `{output, variables, steps}` instead. Extract `result["output"]` in Python or `result.output` in JavaScript. The interface may use this API compiler when an explicitly configured API is connected. The local **Run flow** feature always uses the browser’s bounded graph interpreter and presents the output plus final variables separately; no server or browser evaluates user-supplied source. Tests execute only trusted generated fixtures.

A trace entry contains a `nodeId` (or `edgeId` with its source node) and one-based `codeLines`/`pseudoLines`. Selecting an arrow traces its transition; both branches of one decision may map to the same conditional region. Imported node IDs survive editing and exporting. Editing logic clears generated artifacts; regenerate before using traces or downloads.

## Repository layout

The requested skeleton is preserved:

```text
modulo/
├── README.md, LICENSE, requirements.txt, run.py
├── docs/                     SRS, SDS, UML, reference feature mapping
├── samples/                  importable flows and generated Python demos
├── frontend/
│   ├── index.html
│   ├── css/styles.css, responsive.css
│   └── js/
│       ├── app.js, api.js, upload.js
│       ├── flowchart-view.js, code-view.js, highlighter.js, status.js
│       └── engine.js, icons.js, samples.js, guide.js
├── backend/
│   ├── app.py, pipeline.py, models.py, config.py, errors.py
│   └── services/
│       ├── intake_service.py, vision_service.py, graph_service.py
│       ├── validation_service.py, logic_service.py, pseudocode_service.py
│       └── codegen_service.py, trace_service.py
└── tests/                    service tests, portable compiler tests, fixtures
```

## Tests

```bash
pip install -r requirements.txt
pytest -q
# Node.js 20+; no npm dependencies or install step required:
npm test
```

Backend tests cover file checks, graph import, malformed requests, CORS, vision fixtures, structure, expression safety, executable output and trace mappings. Portable tests cover branches, loops, variable assignment, source injection, imports and trace bounds. See [docs/SRS.md](docs/SRS.md), [docs/SDS.md](docs/SDS.md), and [docs/UML.md](docs/UML.md) for requirements, design and editable diagrams.

## License

[MIT](LICENSE). FlowMapp is a third-party reference, not a partner or dependency of Modulo.

### Optional UI regression check

With the development server running, install Playwright (`pip install playwright`) and a Chromium browser (`playwright install chromium`, or use a system Chromium). Run `python tests/ui_smoke.py`. Set `CHROMIUM_PATH` if using a nonstandard executable. This focused regression covers invalid-import recovery, node/edge trace selection, atomic replacement, in-flight API compilation controls, SVG export, graph simulation and local persistence. It captures no screenshots.

`samples/temperature_converter.svg` contains semantic graph metadata and can be imported browser-only. Its PNG and single-page PDF versions demonstrate the review-required visual recognition path; they do not contain a hidden graph shortcut for the raster recognizer. Additional JSON, Mermaid and uncompressed draw.io demos are included.
