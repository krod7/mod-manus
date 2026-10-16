import io
import json
from pathlib import Path


def test_health_and_convert_api(client, conversion_payload):
    health = client.get("/api/health")
    assert health.status_code == 200 and health.get_json()["status"] == "ok"
    response = client.post("/api/convert", json=conversion_payload, headers={"Origin": "http://localhost:3000"})
    assert response.status_code == 200
    assert response.get_json()["trace"][0]["nodeId"] == "start"
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"


def test_api_rejects_malformed_graph_and_no_wildcard_cors(client):
    response = client.post("/api/convert", json={"graph": {}, "language": "python"}, headers={"Origin": "https://evil.example"})
    assert response.status_code == 422
    body = response.get_json()
    assert set(body) == {"error", "message", "details"}
    assert "Access-Control-Allow-Origin" not in response.headers


def test_analyze_json_upload(client):
    fixture = Path(__file__).parent / "fixtures" / "valid_graph.json"
    response = client.post("/api/analyze", data={"file": (io.BytesIO(fixture.read_bytes()), "chart.json")})
    body = response.get_json()
    assert response.status_code == 200
    assert body["recognition"]["needsReview"] is True
    assert body["graph"]["name"] == "Positive number"
