"""Secure, bounded upload intake.  Parsing is delegated to source-specific services."""
from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from PIL import Image, UnidentifiedImageError
from pypdf import PdfReader

from backend.config import MAX_PIXELS, MAX_UPLOAD_BYTES
from backend.errors import APIError, ValidationAPIError


@dataclass
class Intake:
    filename: str
    kind: str  # image, pdf, json, svg, drawio
    data: bytes
    width: int | None = None
    height: int | None = None


def _suffix(filename: str) -> str:
    return Path(filename or "upload").suffix.lower()


def _check_raster(data: bytes, filename: str) -> Intake:
    try:
        with Image.open(BytesIO(data)) as image:
            image.verify()
        with Image.open(BytesIO(data)) as image:
            width, height = image.size
            if width < 1 or height < 1 or width * height > MAX_PIXELS:
                raise ValidationAPIError("Image exceeds the 16 megapixel recognition limit", ["pixel_limit"])
    except UnidentifiedImageError as exc:
        raise APIError("The upload is not a readable PNG or JPEG image", 415, "unsupported_media") from exc
    return Intake(filename, "image", data, width, height)


def _check_pdf(data: bytes, filename: str) -> Intake:
    try:
        reader = PdfReader(BytesIO(data))
        if len(reader.pages) != 1:
            raise ValidationAPIError("PDF uploads must contain exactly one page", ["pdf_page_count"])
    except ValidationAPIError:
        raise
    except Exception as exc:  # encrypted/broken PDFs should not reach a renderer
        raise APIError("The upload is not a readable PDF", 415, "unsupported_media") from exc
    return Intake(filename, "pdf", data)


def read_upload(file_storage) -> Intake:
    """Read an upload once, rejecting oversized or unsupported content before parsing."""
    if file_storage is None or not getattr(file_storage, "filename", ""):
        raise APIError("A file field is required", 400, "missing_file")
    data = file_storage.read(MAX_UPLOAD_BYTES + 1)
    if not data:
        raise APIError("The uploaded file is empty", 400, "empty_file")
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValidationAPIError("Upload exceeds the 10 MiB limit", ["upload_size"])

    filename = file_storage.filename
    suffix = _suffix(filename)
    head = data.lstrip()[:300].lower()
    if suffix == ".pdf" or data.startswith(b"%PDF-"):
        return _check_pdf(data, filename)
    if suffix in {".png", ".jpg", ".jpeg"}:
        return _check_raster(data, filename)
    if suffix == ".json" or head.startswith(b"{"):
        return Intake(filename, "json", data)
    if suffix == ".svg" or head.startswith(b"<svg"):
        return Intake(filename, "svg", data)
    if suffix in {".drawio", ".xml"} or b"<mxfile" in head or b"<mxgraphmodel" in head:
        return Intake(filename, "drawio", data)
    raise APIError("Only PNG, JPEG, one-page PDF, JSON, SVG, and draw.io XML are supported", 415, "unsupported_media")
