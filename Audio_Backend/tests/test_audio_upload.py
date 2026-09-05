import os
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_upload_missing_file():
    response = client.post("/api/audio/upload")
    assert response.status_code == 422


def test_upload_invalid_file(tmp_path):
    bad_file = tmp_path / "bad.txt"
    bad_file.write_text("not an audio file")
    with open(bad_file, "rb") as f:
        response = client.post(
            "/api/audio/upload",
            files={"file": ("bad.txt", f, "text/plain")},
        )
    assert response.status_code in (400, 422, 500)
