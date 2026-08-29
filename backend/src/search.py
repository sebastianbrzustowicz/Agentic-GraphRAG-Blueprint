import json

from src.config import Config
from src.storage.base import AbstractGraphStore, AbstractVectorStore


def _chat(client, model: str, system: str, user: str) -> str:
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return response.choices[0].message.content or ""


def _build_local_context(entity_hits: list[dict], chunk_hits: list[dict], subgraph: dict) -> str:
    parts = ["Knowledge graph context:"]
    if subgraph["nodes"] or subgraph["edges"]:
        parts.append(json.dumps(subgraph, ensure_ascii=False))
    if entity_hits:
        parts.append("Relevant entities:")
        for hit in entity_hits:
            parts.append(f"- {hit['metadata'].get('name', hit['id'])}: {hit['text']}")
    if chunk_hits:
        parts.append("Relevant source chunks:")
        for hit in chunk_hits:
            source = hit["metadata"].get("source", "")
            parts.append(f"- [{source}] {hit['text']}")
    return "\n".join(parts)


def local_search(
    query: str,
    config: Config,
    graph_store: AbstractGraphStore,
    vector_store: AbstractVectorStore,
) -> dict:
    client = config.client()
    entity_hits = vector_store.similarity_search(query, k=config.local_top_k, where={"kind": "entity"})
    chunk_hits = vector_store.similarity_search(query, k=config.top_k, where={"kind": "chunk"})
    seed_ids = [hit["metadata"]["name"] for hit in entity_hits if hit["metadata"].get("name")]
    subgraph = graph_store.get_subgraph(seed_ids, radius=config.subgraph_radius)
    context = _build_local_context(entity_hits, chunk_hits, subgraph)
    system = config.prompts["local_search"]["system"]
    user = f"Question: {query}\n\n{context}"
    answer = _chat(client, config.llm_model, system, user)
    return {"answer": answer, "subgraph": subgraph}


def _map_report(client, model: str, query: str, report: str, system: str) -> str:
    user = f"Question: {query}\n\nCommunity report:\n{report}"
    return _chat(client, model, system, user)


def _reduce_summaries(client, model: str, query: str, summaries: list[str], system: str) -> str:
    user = f"Question: {query}\n\nSummaries:\n" + "\n---\n".join(summaries)
    return _chat(client, model, system, user)


def global_search(
    query: str,
    config: Config,
    graph_store: AbstractGraphStore,
    vector_store: AbstractVectorStore,
) -> dict:
    client = config.client()
    reports = vector_store.similarity_search(query, k=config.global_top_k, where={"kind": "report"})
    if not reports:
        return {
            "answer": "No community reports found. Run the ingestion pipeline first.",
            "subgraph": {"nodes": [], "edges": []},
        }
    summaries = []
    for report in reports:
        try:
            summaries.append(
                _map_report(client, config.llm_model, query, report["text"], config.prompts["map_report"]["system"])
            )
        except Exception:
            summaries.append(report["text"])
    answer = _reduce_summaries(
        client, config.llm_model, query, summaries, config.prompts["reduce_summaries"]["system"]
    )
    seed_ids = []
    for report in reports:
        metadata = report["metadata"] or {}
        if metadata.get("entities"):
            seed_ids.extend(metadata["entities"].split(";"))
    subgraph = graph_store.get_subgraph(seed_ids, radius=0)
    return {"answer": answer, "subgraph": subgraph}
