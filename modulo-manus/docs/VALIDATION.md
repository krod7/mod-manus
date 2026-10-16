# Validation evidence

Verified on 2026-10-16 in Ubuntu with Python, Node.js 22, system Tesseract and Chromium.

`pytest -q`: **29 passed**. The Python service tests cover intake, structured import, visual recognition, structural/logic checks, pseudocode, executable code generation, trace mapping and API behavior. Cross-language regressions include undefined variables on merged branches, Boolean inputs, missing/finite input checks, denominator-signed negative modulo and division by zero.

`npm test`: **15 passed**. Portable regressions cover sequence/branch/loop behavior, definite assignment, hostile expressions, malformed imports, Mermaid syntax, trace bounds, legacy I/O canonicalization and Python-compatible JavaScript modulo.

`pyright --project pyrightconfig.json`: **0 errors, 0 warnings**. The repository-root check is the reliable Python diagnostic command; automatic editor checks in this environment used a different import root and reported unresolved imports, which do not reproduce with the configured project root. All JavaScript modules passed Node syntax checks.

The focused `tests/ui_smoke.py` Playwright script passed against the development runner. It verifies actual node and edge selection identity and highlights, invalid JSON recovery, generation, atomic replacement without duplicating a project, mutable-control locking during API generation, re-importable SVG export, simulation and browser persistence. It does not capture screenshots.

The final API health, frontend page and route manifest returned HTTP 200 locally and through the temporary HTTPS preview. Backend source returned HTTP 404. Live API conversion returned trace entries for all six edges in the Number checker example.

A clean, high-contrast temperature-converter raster demo produced **five node candidates and four directed connections** through real OpenCV/Tesseract recognition. OCR is still imperfect: border artifacts or characters can affect labels and shape classification. All visual imports remain review-required; this result is not evidence of arbitrary-chart accuracy. The same diagram is supplied in JSON, annotated SVG, PNG and single-page PDF formats for comparison.

The repository is **ready for** GitHub Pages deployment using its supplied Actions workflow. It has not been deployed to a user-owned GitHub repository or a permanent Python host. The default Flask server is for development only; public production OCR needs WSGI hosting, HTTPS and resource/rate/access controls.
