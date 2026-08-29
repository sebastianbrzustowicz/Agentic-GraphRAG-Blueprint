from src.config import Config
from src.search import _build_local_context, global_search, local_search
from tests.fakes import FakeGraphStore, FakeOpenAI, FakeVectorStore


def test_build_local_context_assembles_sections():
    context = _build_local_context(
        entity_hits=[
            {"id": "entity-Alpha", "text": "Alpha description", "metadata": {"name": "Alpha"}}
        ],
        chunk_hits=[
            {"id": "chunk-0-0", "text": "Alpha binds Beta.", "metadata": {"source": "one.txt"}}
        ],
        subgraph={"nodes": [{"id": "Alpha"}], "edges": []},
    )
    assert "Knowledge graph context:" in context
    assert "Alpha: Alpha description" in context
    assert "Relevant source chunks:" in context
    assert "[one.txt] Alpha binds Beta." in context


def test_global_search_returns_message_without_reports():
    config = Config(data_dir="/tmp/x", graph_path="/tmp/x/g", chroma_dir="/tmp/x/c")
    result = global_search("anything", config, FakeGraphStore(), FakeVectorStore())
    assert "No community reports found" in result["answer"]
    assert result["subgraph"] == {"nodes": [], "edges": []}


def test_local_search_end_to_end(tmp_path, monkeypatch):
    config = Config(
        data_dir=str(tmp_path / "data"),
        graph_path=str(tmp_path / "graph.gpickle"),
        chroma_dir=str(tmp_path / "chroma"),
        llm_model="gpt-test",
    )
    graph = FakeGraphStore()
    graph.add_node("Alpha", type="protein", description="binds beta receptors")
    graph.add_node("Beta", type="receptor", description="activated by alpha")
    graph.add_edge("Alpha", "Beta", relation="binds")

    vectors = FakeVectorStore()
    vectors.add_documents(
        ["entity-Alpha"],
        ["Alpha is a protein that binds beta receptors."],
        [{"kind": "entity", "name": "Alpha"}],
    )
    vectors.add_documents(
        ["chunk-0-0"],
        ["Alpha binds Beta in the membrane."],
        [{"kind": "chunk", "source": "one.txt"}],
    )

    monkeypatch.setattr(Config, "client", lambda self: FakeOpenAI("Alpha binds Beta."))
    result = local_search("Alpha", config, graph, vectors)

    assert result["answer"] == "Alpha binds Beta."
    assert {node["id"] for node in result["subgraph"]["nodes"]} == {"Alpha", "Beta"}
