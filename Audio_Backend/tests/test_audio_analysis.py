from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_analyze_missing_audio():
    response = client.post("/api/audio/analyze", params={"audio_id": "nonexistent"})
    assert response.status_code == 404


def test_status_missing_job():
    response = client.get("/api/audio/status/nonexistent")
    assert response.status_code == 404


def test_result_missing_job():
    response = client.get("/api/audio/result/nonexistent")
    assert response.status_code == 404


def test_get_audio_missing():
    response = client.get("/api/audio/nonexistent")
    assert response.status_code == 404
