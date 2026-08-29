import json

from src.config import Config
from src.ingestion import _parse_json, extract_graph, run_ingestion
from src.progress import snapshot
from tests.fakes import FakeGraphStore, FakeOpenAI, FakeVectorStore

ENTITY_PAYLOAD = json.dumps(
    {
        "entities": [
            {"name": "Alpha", "type": "protein", "description": "binds beta receptors"},
            {"name": "Beta", "type": "receptor", "description": "activated by alpha"},
        ],
        "relations": [
            {"source": "Alpha", "target": "Beta", "type": "binds", "description": "physical binding"}
        ],
    }
)


def test_parse_json_plain():
    assert _parse_json('{"a": 1}') == {"a": 1}


def test_parse_json_with_markdown_fence():
    payload = f"```json\n{ENTITY_PAYLOAD}\n```"
    assert _parse_json(payload)["entities"][0]["name"] == "Alpha"


def test_parse_json_with_generic_fence():
    payload = f"```\n{ENTITY_PAYLOAD}\n```"
    assert _parse_json(payload)["entities"][0]["name"] == "Alpha"


def test_extract_graph_parses_entities_and_relations():
    entities, relations = extract_graph(FakeOpenAI(ENTITY_PAYLOAD), "gpt-test", "some chunk")
    assert [entity["name"] for entity in entities] == ["Alpha", "Beta"]
    assert relations[0]["source"] == "Alpha"
    assert relations[0]["target"] == "Beta"


def test_run_ingestion_end_to_end(tmp_path, monkeypatch):
    data_dir = tmp_path / "docs"
    data_dir.mkdir()
    (data_dir / "one.txt").write_text(
        "Alpha cells bind beta receptors. Gamma inhibits delta.", encoding="utf-8"
    )
    (data_dir / "two.txt").write_text(
        "Beta receptors activate epsilon pathway. Delta is a hormone.", encoding="utf-8"
    )

    config = Config(
        data_dir=str(data_dir),
        graph_path=str(tmp_path / "graph.gpickle"),
        chroma_dir=str(tmp_path / "chroma"),
        llm_model="gpt-test",
    )
    monkeypatch.setattr(Config, "client", lambda self: FakeOpenAI(ENTITY_PAYLOAD))

    graph = FakeGraphStore()
    vectors = FakeVectorStore()
    stats = run_ingestion(config, graph, vectors)

    assert stats["files"] == 2
    assert stats["chunks"] > 0
    assert stats["entities"] >= 2
    assert stats["relations"] > 0
    assert stats["communities"] >= 1
    assert stats["reports"] >= 1
    assert graph.node_count() >= 2
    assert graph.edge_count() >= 1
    assert vectors.count() > 0
    assert snapshot()["processed_files"] == 2

    kinds = {doc["metadata"]["kind"] for doc in vectors._documents}
    assert {"entity", "chunk", "report"} <= kinds


def test_run_ingestion_deduplicates_entities_across_files(tmp_path, monkeypatch):
    data_dir = tmp_path / "docs"
    data_dir.mkdir()
    (data_dir / "a.txt").write_text("Alpha binds beta.", encoding="utf-8")
    (data_dir / "b.txt").write_text("Alpha binds beta again.", encoding="utf-8")

    config = Config(
        data_dir=str(data_dir),
        graph_path=str(tmp_path / "graph.gpickle"),
        chroma_dir=str(tmp_path / "chroma"),
        llm_model="gpt-test",
    )
    monkeypatch.setattr(Config, "client", lambda self: FakeOpenAI(ENTITY_PAYLOAD))

    graph = FakeGraphStore()
    vectors = FakeVectorStore()
    stats = run_ingestion(config, graph, vectors)

    # "Alpha" is seen in both files but added to the graph only once.
    assert stats["entities"] == 2
    assert graph.node_count() == 2
