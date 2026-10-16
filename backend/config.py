"""Runtime configuration for the Modulo API."""
from __future__ import annotations

import os
from urllib.parse import urlparse

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_NODES = 100
MAX_EDGES = 300
MAX_PIXELS = 16_000_000
MAX_LABEL_LENGTH = 240
MAX_ID_LENGTH = 64
DEFAULT_PORT = 3000

_DEFAULT_ORIGINS = {"http://localhost:3000", "http://127.0.0.1:3000"}


def _is_permitted_origin(origin: str) -> bool:
    """Allow only explicit localhost or GitHub Pages web origins (never wildcards)."""
    parsed = urlparse(origin)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.path not in {"", "/"}:
        return False
    host = (parsed.hostname or "").lower()
    return host in {"localhost", "127.0.0.1", "::1"} or host == "github.io" or host.endswith(".github.io")


def allowed_origins() -> set[str]:
    raw = os.getenv("MODULO_ALLOWED_ORIGINS", "")
    configured = {item.strip().rstrip("/") for item in raw.split(",") if item.strip()}
    # Invalid configured values are intentionally discarded rather than broadening CORS.
    return _DEFAULT_ORIGINS | {origin for origin in configured if _is_permitted_origin(origin)}
