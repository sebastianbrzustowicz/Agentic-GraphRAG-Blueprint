import json

import pytest

from src.config import Config
from src.ingestion import _parse_json, extract_graph, extract_graph_batch, run_ingestion
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


def test_extract_graph_batch_one_call_per_batch():
    chunks = ["Alpha binds beta.", "Gamma inhibits delta.", "Epsilon activates zeta."]
    fake = FakeOpenAI(ENTITY_PAYLOAD, batched=True)
    results = extract_graph_batch(fake, "gpt-test", chunks, batch_size=2)
    assert len(results) == 3
    assert fake.calls == 2  # ceil(3 / 2)
    assert all(entities for entities, _ in results)


def test_extract_graph_batch_raises_when_batch_is_unparseable():
    chunks = ["Alpha binds beta.", "Gamma inhibits delta."]
    fake = FakeOpenAI(ENTITY_PAYLOAD)  # single-chunk payload, not a batch response
    with pytest.raises(ValueError):
        extract_graph_batch(fake, "gpt-test", chunks, batch_size=2)
    assert fake.calls == 1


def test_run_ingestion_incremental_skips_unchanged_files(tmp_path, monkeypatch):
    data_dir = tmp_path / "docs"
    data_dir.mkdir()
    document = data_dir / "one.txt"
    document.write_text("Alpha binds beta receptors.", encoding="utf-8")

    config = Config(
        data_dir=str(data_dir),
        graph_path=str(tmp_path / "graph.gpickle"),
        chroma_dir=str(tmp_path / "chroma"),
        llm_model="gpt-test",
    )
    fake = FakeOpenAI(ENTITY_PAYLOAD)
    monkeypatch.setattr(Config, "client", lambda self: fake)

    # First run: full rebuild.
    graph = FakeGraphStore()
    vectors = FakeVectorStore()
    first = run_ingestion(config, graph, vectors)
    assert first["entities"] >= 2
    assert fake.calls > 0
    calls_after_first = fake.calls

    # Second run with the same content, persisted stores: nothing to do.
    persisted_graph = FakeGraphStore()
    persisted_graph.add_node("Alpha", type="protein", description="binds beta receptors")
    persisted_graph.add_node("Beta", type="receptor", description="activated by alpha")
    persisted_graph.add_edge("Alpha", "Beta", relation="binds")
    persisted_vectors = FakeVectorStore()
    persisted_vectors.add_documents(
        ["entity-Alpha"], ["binds beta receptors"], [{"kind": "entity", "name": "Alpha"}]
    )
    persisted_vectors.add_documents(
        ["chunk-one.txt-0"], ["Alpha binds beta receptors."], [{"kind": "chunk", "source": "one.txt"}]
    )
    second = run_ingestion(config, persisted_graph, persisted_vectors)
    assert second["entities"] == 0
    assert fake.calls == calls_after_first  # no LLM calls at all

    # Third run after the file changes: only the new entity is extracted and
    # only its community report is regenerated.
    document.write_text("Alpha binds beta receptors. Gamma is a kinase.", encoding="utf-8")
    gamma_fake = FakeOpenAI(
        {
            "entities": [
                {"name": "Gamma", "type": "protein", "description": "a kinase"}
            ],
            "relations": [],
        }
    )
    monkeypatch.setattr(Config, "client", lambda self: gamma_fake)
    third_graph = FakeGraphStore()
    third_graph.add_node("Alpha", type="protein", description="binds beta receptors")
    third_graph.add_node("Beta", type="receptor", description="activated by alpha")
    third_graph.add_edge("Alpha", "Beta", relation="binds")
    third_vectors = FakeVectorStore()
    third_vectors.add_documents(
        ["entity-Alpha"], ["binds beta receptors"], [{"kind": "entity", "name": "Alpha"}]
    )
    third_vectors.add_documents(
        ["chunk-one.txt-0"], ["Alpha binds beta receptors."], [{"kind": "chunk", "source": "one.txt"}]
    )
    third = run_ingestion(config, third_graph, third_vectors)
    assert third["entities"] == 1  # only Gamma is new
    assert third["relations"] == 0
    assert third["reports"] == 1  # only Gamma's community is regenerated
    assert gamma_fake.calls == 2  # extraction + one community report
