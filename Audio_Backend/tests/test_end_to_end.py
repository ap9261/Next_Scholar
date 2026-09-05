import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_end_to_end_invalid_audio():
    response = client.post(
        "/api/audio/upload",
        files={"file": ("test.txt", b"not audio", "text/plain")},
    )
    assert response.status_code in (400, 422, 500)
