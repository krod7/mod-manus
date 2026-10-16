"""Development runner for the separately hostable Modulo Flask API and static frontend."""
from __future__ import annotations

import os
from pathlib import Path

from flask import abort, send_from_directory
from werkzeug.security import safe_join

from backend.app import create_app
from backend.config import DEFAULT_PORT

ROOT = Path(__file__).resolve().parent
FRONTEND = ROOT / "frontend"
app = create_app()


@app.route("/", defaults={"asset": ""})
@app.route("/<path:asset>")
def static_frontend(asset: str):
    # API routes are registered first; static serving is restricted to frontend/ only.
    candidate = safe_join(str(FRONTEND), asset) if asset else None
    if candidate and Path(candidate).is_file():
        return send_from_directory(FRONTEND, asset)
    index = FRONTEND / "index.html"
    if index.is_file() and not asset:
        return send_from_directory(FRONTEND, "index.html")
    abort(404)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", str(DEFAULT_PORT))), debug=False, use_reloader=False)
