from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
ROOT = FIXTURES.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def valid_graph():
    return json.loads((FIXTURES / "valid_graph.json").read_text())


@pytest.fixture
def conversion_payload(valid_graph):
    return {"graph": copy.deepcopy(valid_graph), "language": "python"}


@pytest.fixture
def client():
    from backend.app import create_app
    app = create_app()
    app.config.update(TESTING=True)
    return app.test_client()
