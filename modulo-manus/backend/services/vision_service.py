"""Best-effort local raster/PDF flowchart recognition.

This is deliberately conservative: a connector becomes a directed graph edge only when an
arrowhead-like Hough-line pattern indicates direction.  Unoriented lines are reported for
human review instead of guessed.
"""
from __future__ import annotations

from io import BytesIO
from math import acos, degrees, hypot
from typing import Any

import numpy as np
from PIL import Image

from backend.config import MAX_PIXELS
from backend.errors import APIError, ValidationAPIError
from backend.models import Edge, Graph, Node
from backend.services.intake_service import Intake

try:  # Imports are optional only for an explanatory service-unavailable response.
    import cv2
    import pytesseract
except ImportError:  # pragma: no cover - exercised only when deployment is incomplete
    cv2 = None
    pytesseract = None


def _image_from_intake(intake: Intake) -> Image.Image:
    if intake.kind == "image":
        opened = Image.open(BytesIO(intake.data)).convert("RGBA")
        background = Image.new("RGBA", opened.size, (255, 255, 255, 255))
        return Image.alpha_composite(background, opened).convert("RGB")
    if intake.kind != "pdf":
        raise ValueError("vision service expects an image or PDF")
    try:
        import fitz
        document = fitz.open(stream=intake.data, filetype="pdf")
        if document.page_count != 1:
            raise ValidationAPIError("PDF uploads must contain exactly one page", ["pdf_page_count"])
        page = document[0]
        rect = page.rect
        base_pixels = max(1.0, rect.width * rect.height)
        # 144 DPI nominal rendering, reduced first if that would violate the pixel budget.
        scale = min(2.0, (MAX_PIXELS / base_pixels) ** 0.5)
        pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
        if pixmap.width * pixmap.height > MAX_PIXELS:
            raise ValidationAPIError("PDF rasterization exceeds the 16 megapixel limit", ["pixel_limit"])
        return Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
    except ValidationAPIError:
        raise
    except Exception as exc:
        raise APIError("The PDF could not be rasterized for recognition", 415, "pdf_render") from exc


def _iou(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> float:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    overlap = max(0, min(ax + aw, bx + bw) - max(ax, bx)) * max(0, min(ay + ah, by + bh) - max(ay, by))
    return overlap / max(1, aw * ah + bw * bh - overlap)


def _shape_type(contour: np.ndarray, box: tuple[int, int, int, int], label: str) -> tuple[str, float, str | None]:
    assert cv2 is not None
    perimeter = cv2.arcLength(contour, True)
    approx = cv2.approxPolyDP(contour, 0.035 * perimeter, True) if perimeter else contour
    area = cv2.contourArea(contour)
    circularity = 4 * np.pi * area / max(perimeter * perimeter, 1)
    x, y, w, h = box
    lowered = label.strip().lower()
    if len(approx) == 4:
        points = approx.reshape(-1, 2)
        center = points.mean(axis=0)
        # A diamond normally has vertices near extrema rather than near bounding-box corners.
        diagonal = sum(abs(px - center[0]) < w * .22 or abs(py - center[1]) < h * .22 for px, py in points)
        if diagonal >= 3:
            return "decision", 0.78, None
        # A non-axis-aligned quadrilateral is recognized as I/O; rectangles remain process.
        slopes = []
        for idx in range(4):
            p, q = points[idx], points[(idx + 1) % 4]
            slopes.append(abs(float(q[1] - p[1])) / max(abs(float(q[0] - p[0])), 1))
        if any(.15 < slope < 6 for slope in slopes) and not all(slope < .15 or slope > 6 for slope in slopes):
            return "input_output", 0.7, "Quadrilateral shape is a tentative input/output classification"
        return "process", 0.82, None
    if len(approx) >= 5 or circularity > .68:
        if lowered in {"start", "begin"}:
            return "start", 0.85, None
        if lowered in {"end", "stop", "finish"}:
            return "end", 0.85, None
        return "process", 0.62, "Ellipse without a legible Start/End label was not assumed to be terminal"
    return "process", 0.55, "Shape is uncertain; review classification"


def _ocr_label(rgb: np.ndarray, box: tuple[int, int, int, int]) -> str:
    if pytesseract is None:
        return ""
    x, y, w, h = box
    # inset avoids most border strokes, and thresholding keeps OCR local to a candidate node.
    inset_x, inset_y = max(3, w // 45), max(3, h // 5)
    crop = rgb[y + inset_y:y + h - inset_y, x + inset_x:x + w - inset_x]
    if crop.size == 0:
        return ""
    try:
        text = pytesseract.image_to_string(crop, config="--psm 7")
        return " ".join(text.split()).strip(" :;|/")[:240]
    except (OSError, RuntimeError):
        return ""


def _near_node(point: tuple[float, float], boxes: list[tuple[int, int, int, int]]) -> int | None:
    px, py = point
    best: tuple[float, int] | None = None
    for index, (x, y, w, h) in enumerate(boxes):
        dx = max(x - px, 0, px - (x + w))
        dy = max(y - py, 0, py - (y + h))
        distance = hypot(dx, dy)
        if distance <= max(18, min(w, h) * .45) and (best is None or distance < best[0]):
            best = (distance, index)
    return best[1] if best else None


def _arrow_score(lines: list[tuple[int, int, int, int]], tip: tuple[float, float], direction: tuple[float, float]) -> int:
    """Count short oblique Hough segments meeting at a potential arrow tip."""
    dx, dy = direction
    norm = hypot(dx, dy) or 1
    dx, dy = dx / norm, dy / norm
    count = 0
    for x1, y1, x2, y2 in lines:
        for near, far in (((x1, y1), (x2, y2)), ((x2, y2), (x1, y1))):
            if hypot(near[0] - tip[0], near[1] - tip[1]) > 14:
                continue
            vx, vy = far[0] - near[0], far[1] - near[1]
            length = hypot(vx, vy)
            if not 4 <= length <= 45:
                continue
            # Arrow wings point backwards from the tip at an oblique angle.
            cosine = (vx * -dx + vy * -dy) / length
            if .25 <= cosine <= .93:
                count += 1
                break
    return count


def _recognize_connectors(mask: np.ndarray, boxes: list[tuple[int, int, int, int]], warnings: list[str]) -> list[Edge]:
    assert cv2 is not None
    removed = mask.copy()
    for x, y, w, h in boxes:
        cv2.rectangle(removed, (x - 2, y - 2), (x + w + 2, y + h + 2), 0, thickness=-1)
    lines_raw = cv2.HoughLinesP(removed, 1, np.pi / 180, threshold=22, minLineLength=18, maxLineGap=10)
    if lines_raw is None:
        return []
    lines = [(int(line[0][0]), int(line[0][1]), int(line[0][2]), int(line[0][3])) for line in lines_raw]
    wings_raw = cv2.HoughLinesP(removed, 1, np.pi / 180, threshold=5, minLineLength=4, maxLineGap=3)
    wings = [(int(line[0][0]), int(line[0][1]), int(line[0][2]), int(line[0][3])) for line in wings_raw] if wings_raw is not None else []
    edges: list[Edge] = []
    directed_pairs: set[tuple[int, int]] = set()
    ambiguous = 0
    for x1, y1, x2, y2 in lines:
        source_candidate, target_candidate = _near_node((x1, y1), boxes), _near_node((x2, y2), boxes)
        if source_candidate is None or target_candidate is None or source_candidate == target_candidate:
            continue
        forward = _arrow_score(wings, (x2, y2), (x2 - x1, y2 - y1))
        backward = _arrow_score(wings, (x1, y1), (x1 - x2, y1 - y2))
        if forward == backward or max(forward, backward) < 2:
            ambiguous += 1
            continue
        pair = (source_candidate, target_candidate) if forward > backward else (target_candidate, source_candidate)
        directed_pairs.add(pair)
    for count, (source, target) in enumerate(sorted(directed_pairs), 1):
        edges.append(Edge(f"e{count}", f"n{source + 1}", f"n{target + 1}", ""))
    if ambiguous:
        warnings.append(f"{ambiguous} connector candidate(s) had no reliable arrow direction and were not added")
    return edges


def recognize(intake: Intake) -> tuple[Graph, list[str], dict[str, Any]]:
    if cv2 is None:
        raise APIError("OpenCV and pytesseract must be installed for image recognition", 503, "recognition_unavailable")
    image = _image_from_intake(intake)
    if image.width * image.height > MAX_PIXELS:
        raise ValidationAPIError("Image exceeds the 16 megapixel recognition limit", ["pixel_limit"])
    rgb = np.array(image)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    mask = cv2.threshold(cv2.GaussianBlur(gray, (3, 3), 0), 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    raw_candidates: list[tuple[np.ndarray, tuple[int, int, int, int]]] = []
    image_area = image.width * image.height
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = cv2.contourArea(contour)
        if w < 42 or h < 24 or area < 600 or w * h > image_area * .82:
            continue
        # A very tall connected outline is often the entire chart plus arrows,
        # not one node. Keep conventional horizontal shapes and diamonds.
        if 0.6 < w / max(h, 1) < 9:
            raw_candidates.append((contour, (x, y, w, h)))
    # Prefer larger enclosing contours and remove nested/duplicate candidates.
    raw_candidates.sort(key=lambda item: item[1][2] * item[1][3], reverse=True)
    candidates: list[tuple[np.ndarray, tuple[int, int, int, int]]] = []
    for contour, box in raw_candidates:
        if any(_iou(box, other_box) > .72 for _, other_box in candidates):
            continue
        candidates.append((contour, box))
    candidates.sort(key=lambda item: (item[1][1], item[1][0]))

    warnings: list[str] = ["Recognition is best-effort OCR/computer vision. Review every node and connector before conversion."]
    if pytesseract is None:
        warnings.append("Tesseract OCR is unavailable; labels could not be read")
    nodes: list[Node] = []
    boxes: list[tuple[int, int, int, int]] = []
    for index, (contour, box) in enumerate(candidates[:100], 1):
        label = _ocr_label(rgb, box)
        node_type, confidence, note = _shape_type(contour, box, label)
        if not label:
            label = "<unreadable>"
            confidence = min(confidence, .45)
            note = (note + "; " if note else "") + "OCR could not read this label"
        if note:
            warnings.append(f"Node n{index}: {note}")
        x, y, w, h = box
        nodes.append(Node(f"n{index}", node_type, label, x + w / 2, y + h / 2, confidence, note))
        boxes.append(box)
    if not nodes:
        warnings.append("No bounded flowchart node contours were found")
    edges = _recognize_connectors(mask, boxes, warnings) if len(nodes) > 1 else []
    if not edges and len(nodes) > 1:
        warnings.append("No directed connectors were recognized; do not infer branches manually without review")
    graph = Graph(f"Recognized {intake.filename}", nodes, edges)
    return graph, warnings, {"method": "opencv+pytesseract best-effort", "needsReview": True}
