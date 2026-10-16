"""Optional Playwright regression script; install playwright and Chromium to run.
Run against python run.py: python tests/ui_smoke.py
It verifies concrete integration defects and never captures screenshots.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright
import json
import time
import os
import shutil

ROOT = Path(__file__).resolve().parents[1]
with sync_playwright() as p:
    executable = os.getenv("CHROMIUM_PATH") or shutil.which("chromium")
    browser = p.chromium.launch(headless=True, executable_path=executable, args=["--no-sandbox"])
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto("http://localhost:3000", wait_until="networkidle")
    assert page.locator("#flow-title").inner_text() == "Number checker"
    assert page.locator("#graph-svg [data-node]").count() == 6
    page.locator('#graph-svg [data-node="check"]').click()
    assert page.locator(".code-line.selected").count() > 0
    page.locator('#graph-svg [data-edge="e3"] .edge-hit').click(force=True)
    assert page.locator("#inspector .inspector-id").inner_text() == "e3"
    assert page.locator(".code-line.selected").count() > 0
    assert "SOURCE L" in page.locator("#inspector").inner_text()
    # Invalid file must restore the dialog's usable chooser.
    page.locator("#import-button").click()
    page.locator("#file-input").set_input_files({"name":"bad.json", "mimeType":"application/json", "buffer":b"not JSON"})
    page.locator("#import-error").wait_for()
    assert "Invalid JSON" in page.locator("#import-error").inner_text()
    assert page.locator("#browse-file").count() == 1
    # Structured import, generation and replacement keep correct project identity.
    page.locator("#file-input").set_input_files(str(ROOT / "samples/number_checker.json"))
    page.wait_for_function("!document.querySelector('#modal').open")
    assert page.locator("#project-count").inner_text() == "2"
    page.locator("#generate-button").click()
    page.wait_for_function("document.querySelector('#code-content .code-line') !== null")
    page.locator("#source-tab").click()
    page.locator("#replace-source").click()
    page.locator("#file-input").set_input_files(str(ROOT / "samples/temperature_converter.json"))
    page.wait_for_function("!document.querySelector('#modal').open")
    assert page.locator("#project-count").inner_text() == "2"
    assert page.locator("#flow-title").inner_text() == "temperature converter"
    page.locator("#generate-button").click()
    page.wait_for_function("document.querySelector('#code-content .code-line') !== null")
    # API generation locks mutable controls and returns edge trace regions.
    page.locator("#settings-button").click()
    page.locator("#api-url").fill("http://localhost:3000")
    page.locator("#api-test").click()
    page.wait_for_function("document.querySelector('#api-result').textContent.startsWith('Connected')")
    page.locator("#close-modal").click()
    def delayed(route):
        time.sleep(.35)
        route.continue_()
    page.route("**/api/convert", delayed)
    page.locator("#generate-button").click()
    assert page.locator("#language").is_disabled()
    page.wait_for_function("!document.querySelector('#language').disabled")
    assert "Graph validated" in page.locator(".code-footer").inner_text()
    page.locator('#graph-svg [data-edge="e1"] .edge-hit').click(force=True)
    assert page.locator("#inspector .inspector-id").inner_text() == "e1"
    assert "SOURCE L" in page.locator("#inspector").inner_text()
    # Export a reproducible diagram sample with semantic metadata.
    with page.expect_download() as download:
        page.locator("#export-svg").click()
    download.value.save_as(str(ROOT / "samples/temperature_converter.svg"))
    # Simulation presents output and the actual path.
    page.locator("#run-flow").click()
    page.locator('[data-run-input="celsius"]').fill("0")
    page.locator("#simulate-button").click()
    assert "32" in page.locator("#simulation-results").inner_text()
    assert page.locator("[data-run-node]").count() == 5
    page.locator("#close-modal").click()
    page.reload(wait_until="networkidle")
    assert page.locator("#project-count").inner_text() == "2"
    assert not errors, errors
    browser.close()
print("UI regressions passed: trace, invalid import recovery, replacement identity, API generation lock, SVG export, simulation and persistence")
