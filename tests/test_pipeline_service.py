import pytest

from backend.errors import ValidationAPIError
from backend.pipeline import convert


def test_pipeline_returns_contract_and_trace(conversion_payload):
    result = convert(conversion_payload)
    assert result["language"] == "python"
    assert result["validation"] == {"errors": [], "warnings": []}
    assert len([item for item in result["trace"] if "edgeId" not in item]) == len(result["graph"]["nodes"])
    assert len([item for item in result["trace"] if "edgeId" in item]) == len(result["graph"]["edges"])


def test_pipeline_blocks_unknown_named_process(conversion_payload):
    conversion_payload["graph"]["nodes"].append({"id": "bad", "type": "process", "label": "launch missiles"})
    conversion_payload["graph"]["edges"][-1]["target"] = "bad"
    conversion_payload["graph"]["edges"].append({"id": "e7", "source": "bad", "target": "end", "label": ""})
    with pytest.raises(ValidationAPIError, match="operation"):
        convert(conversion_payload)


def test_pipeline_blocks_undefined_variable_with_node_specific_error(conversion_payload):
    conversion_payload["graph"]["nodes"][3]["label"] = "DISPLAY missing"

    with pytest.raises(ValidationAPIError, match="operation") as raised:
        convert(conversion_payload)

    assert "Node positive" in raised.value.details[0]
    assert "missing" in raised.value.details[0]
    assert "INPUT or assignment" in raised.value.details[0]
