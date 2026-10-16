from io import BytesIO

import pytest
from PIL import Image
from werkzeug.datastructures import FileStorage

from backend.errors import ValidationAPIError
from backend.services.intake_service import read_upload


def test_accepts_png_and_checks_dimensions():
    stream = BytesIO()
    Image.new("RGB", (40, 30), "white").save(stream, "PNG")
    intake = read_upload(FileStorage(BytesIO(stream.getvalue()), filename="chart.png"))
    assert (intake.kind, intake.width, intake.height) == ("image", 40, 30)


def test_rejects_unsupported_upload():
    with pytest.raises(Exception):
        read_upload(FileStorage(BytesIO(b"not a chart"), filename="chart.exe"))
