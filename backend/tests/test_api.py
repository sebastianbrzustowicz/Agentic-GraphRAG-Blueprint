import os

from fastapi.testclient import TestClient

from app import app, config
from src.config import Config
from src.progress import start as progress_start
from src.progress import stop as progress_stop
from tests.fakes import FakeOpenAI

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_stats_shape():
    response = client.get("/stats")
    assert response.status_code == 200
    assert set(response.json()) == {"nodes", "edges", "documents"}


def test_upload_empty_file_rejected():
    response = client.post("/upload", files={"file": ("empty.txt", b"")})
    assert response.status_code == 400


def test_upload_writes_file_to_data_dir():
    response = client.post("/upload", files={"file": ("hello.txt", b"hello world")})
    assert response.status_code == 200
    path = response.json()["path"]
    assert os.path.basename(path) == "hello.txt"
    with open(path, encoding="utf-8") as handle:
        assert handle.read() == "hello world"


def test_upload_sanitizes_path_traversal():
    response = client.post("/upload", files={"file": ("../../evil.txt", b"payload")})
    assert response.status_code == 200
    path = response.json()["path"]
    assert os.path.basename(path) == "evil.txt"
    assert os.path.dirname(path) == config.data_dir


def test_ingest_conflicts_when_already_running():
    progress_start(1, ["a.txt"])
    try:
        response = client.post("/ingest")
        assert response.status_code == 409
    finally:
        progress_stop()


def test_query_local_works_offline(monkeypatch):
    monkeypatch.setattr(Config, "client", lambda self: FakeOpenAI("canned answer"))
    response = client.post("/query", json={"query": "hello", "mode": "local"})
    assert response.status_code == 200
    assert response.json()["answer"] == "canned answer"
