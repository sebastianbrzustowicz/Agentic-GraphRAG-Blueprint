import os

from src.config import ROOT, Config


def test_defaults(monkeypatch):
    for key in (
        "LLM_MODEL",
        "EMBEDDING_MODEL",
        "CHUNK_SIZE",
        "CHUNK_OVERLAP",
        "TOP_K",
        "DATA_DIR",
        "CHROMA_DIR",
        "GRAPH_PATH",
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
    ):
        monkeypatch.delenv(key, raising=False)
    config = Config()
    assert config.llm_model == "gpt-4o-mini"
    assert config.embedding_model == "text-embedding-3-small"
    assert config.chunk_size == 400
    assert config.chunk_overlap == 50
    assert config.top_k == 5
    assert config.data_dir == os.path.join(ROOT, "data")
    assert config.chroma_dir == os.path.join(ROOT, ".chroma_db")


def test_env_overrides(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "gpt-4o")
    monkeypatch.setenv("EMBEDDING_MODEL", "text-embedding-3-large")
    monkeypatch.setenv("CHUNK_SIZE", "800")
    monkeypatch.setenv("TOP_K", "9")
    monkeypatch.setenv("DATA_DIR", "/custom/data")
    config = Config()
    assert config.llm_model == "gpt-4o"
    assert config.embedding_model == "text-embedding-3-large"
    assert config.chunk_size == 800
    assert config.top_k == 9
    assert config.data_dir == "/custom/data"
