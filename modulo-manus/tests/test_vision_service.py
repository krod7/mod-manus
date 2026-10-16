from io import BytesIO

from PIL import Image, ImageDraw

from backend.services.intake_service import Intake
from backend.services.vision_service import recognize


def test_recognition_is_explicitly_best_effort_and_requires_review():
    image = Image.new("RGB", (320, 180), "white")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((30, 50, 140, 110), radius=25, outline="black", width=3)
    draw.text((60, 72), "Start", fill="black")
    draw.rectangle((190, 50, 290, 110), outline="black", width=3)
    draw.text((220, 72), "x = 1", fill="black")
    stream = BytesIO(); image.save(stream, "PNG")
    graph, warnings, recognition = recognize(Intake("test.png", "image", stream.getvalue(), 320, 180))
    assert recognition["needsReview"] is True
    assert "opencv" in recognition["method"]
    assert isinstance(graph.nodes, list) and warnings


def test_transparent_image_is_composited_over_white():
    from backend.services.vision_service import _image_from_intake
    image = Image.new('RGBA', (20, 20), (0, 0, 0, 0))
    stream = BytesIO(); image.save(stream, 'PNG')
    flattened = _image_from_intake(Intake('transparent.png', 'image', stream.getvalue(), 20, 20))
    assert flattened.mode == 'RGB'
    assert flattened.getpixel((0, 0)) == (255, 255, 255)


def test_clean_demo_extracts_five_candidates_and_four_directed_arrows():
    from pathlib import Path
    path = Path(__file__).resolve().parents[1] / 'samples' / 'temperature_converter.png'
    graph, warnings, recognition = recognize(Intake(path.name, 'image', path.read_bytes(), 900, 800))
    assert len(graph.nodes) == 5
    assert len(graph.edges) == 4
    assert recognition['needsReview'] is True
    assert warnings
