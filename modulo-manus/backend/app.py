"""Flask API application for Modulo; it does not serve backend source files."""
from __future__ import annotations

from flask import Flask, jsonify, request
from werkzeug.exceptions import RequestEntityTooLarge

from backend.config import MAX_UPLOAD_BYTES, allowed_origins
from backend.errors import APIError
from backend.pipeline import analyze_upload, convert


def create_app() -> Flask:
    app = Flask(__name__)
    # The intake service repeats this check using actual bytes; this guards large requests early.
    app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES + 64 * 1024

    @app.after_request
    def cors(response):
        origin = request.headers.get("Origin", "").rstrip("/")
        if origin in allowed_origins():
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS, GET"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type"
            response.headers["Vary"] = "Origin"
        return response

    @app.errorhandler(APIError)
    def api_error(error: APIError):
        return jsonify(error.as_dict()), error.status_code

    @app.errorhandler(RequestEntityTooLarge)
    def request_too_large(_error):
        return jsonify({"error": "validation_error", "message": "Upload exceeds the 10 MiB limit", "details": ["upload_size"]}), 422

    @app.errorhandler(415)
    def unsupported_media(_error):
        return jsonify({"error": "unsupported_media", "message": "Unsupported media type", "details": []}), 415

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "service": "modulo-api"})

    @app.route("/api/analyze", methods=["POST", "OPTIONS"])
    def analyze():
        if request.method == "OPTIONS":
            return ("", 204)
        return jsonify(analyze_upload(request.files.get("file")))

    @app.route("/api/convert", methods=["POST", "OPTIONS"])
    def conversion():
        if request.method == "OPTIONS":
            return ("", 204)
        if not request.is_json:
            raise APIError("Content-Type must be application/json", 400, "invalid_json")
        payload = request.get_json(silent=True)
        if payload is None:
            raise APIError("Request body contains invalid JSON", 400, "invalid_json")
        return jsonify(convert(payload))

    return app


app = create_app()
