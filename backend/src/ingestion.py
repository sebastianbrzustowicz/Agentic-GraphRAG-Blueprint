import glob
import json
import os
import re

import community
import networkx as nx

from src.config import Config
from src.storage.base import AbstractGraphStore, AbstractVectorStore

CHARS_PER_TOKEN = 4


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [part.strip() for part in parts if part.strip()]


def _take_overlap(sentences: list[str], overlap_tokens: int) -> list[str]:
    overlap = []
    used = 0
    for sentence in reversed(sentences):
        tokens = max(1, len(sentence) // CHARS_PER_TOKEN)
        if used + tokens > overlap_tokens:
            break
        overlap.insert(0, sentence)
        used += tokens
    return overlap


def chunk_text(text: str, chunk_tokens: int = 400, overlap_tokens: int = 50) -> list[str]:
    sentences = _split_sentences(text)
    chunks = []
    current = []
    current_tokens = 0
    for sentence in sentences:
        sentence_tokens = max(1, len(sentence) // CHARS_PER_TOKEN)
        if current and current_tokens + sentence_tokens > chunk_tokens:
            chunks.append(" ".join(current))
            overlap = _take_overlap(current, overlap_tokens)
            current = overlap
            current_tokens = sum(max(1, len(item) // CHARS_PER_TOKEN) for item in overlap)
        current.append(sentence)
        current_tokens += sentence_tokens
    if current:
        chunks.append(" ".join(current))
    return chunks


def _chat(client, model: str, system: str, user: str, json_mode: bool = False) -> str:
    kwargs = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
        kwargs["temperature"] = 0
    response = client.chat.completions.create(**kwargs)
    return response.choices[0].message.content or ""


def _parse_json(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").strip()
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
    return json.loads(cleaned)


def extract_graph(client, model: str, chunk: str) -> tuple[list[dict], list[dict]]:
    system = (
        "You are a medical knowledge graph extraction engine. "
        "Extract medical entities and their relationships from the provided text. "
        "Return JSON only with the keys 'entities' and 'relations'. "
        "Each entity is an object with keys 'name', 'type', 'description'. "
        "Each relation is an object with keys 'source', 'target', 'type', 'description'. "
        "Use canonical entity names and reuse the exact same name for the same entity across chunks."
    )
    raw = _chat(client, model, system, chunk, json_mode=True)
    data = _parse_json(raw)
    return data.get("entities", []), data.get("relations", [])


def generate_community_report(
    client,
    model: str,
    community_id: int,
    entities: list[str],
    relations: list[str],
) -> str:
    system = (
        "You are a medical knowledge graph analyst. "
        "Write a concise but information-dense community report covering key entities, "
        "relationships, treatments, risk factors and clinical implications. "
        "Write in the language of the input. Return plain text."
    )
    user = (
        f"Community {community_id}:\n"
        f"Entities:\n{chr(10).join(entities)}\n\n"
        f"Relations:\n{chr(10).join(relations)}"
    )
    return _chat(client, model, system, user)


def run_ingestion(
    config: Config,
    graph_store: AbstractGraphStore,
    vector_store: AbstractVectorStore,
) -> dict:
    graph_store.reset()
    vector_store.reset()
    files = sorted(glob.glob(os.path.join(config.data_dir, "*.txt")))
    client = config.client()
    stats = {
        "files": len(files),
        "chunks": 0,
        "entities": 0,
        "relations": 0,
        "communities": 0,
        "reports": 0,
    }
    known_entities = set()
    for file_index, path in enumerate(files):
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        chunks = chunk_text(text, config.chunk_size, config.chunk_overlap)
        for chunk_index, chunk in enumerate(chunks):
            try:
                entities, relations = extract_graph(client, config.llm_model, chunk)
            except Exception:
                continue
            chunk_entities = []
            for entity in entities:
                name = entity.get("name", "").strip()
                if not name:
                    continue
                if name not in known_entities:
                    graph_store.add_node(
                        name,
                        type=entity.get("type", ""),
                        description=entity.get("description", ""),
                    )
                    vector_store.add_documents(
                        [f"entity-{name}"],
                        [entity.get("description") or name],
                        [{"kind": "entity", "name": name, "type": entity.get("type", "")}],
                    )
                    known_entities.add(name)
                    stats["entities"] += 1
                chunk_entities.append(name)
            for relation in relations:
                source = relation.get("source", "").strip()
                target = relation.get("target", "").strip()
                relation_type = relation.get("type", "").strip()
                if source and target:
                    graph_store.add_edge(
                        source,
                        target,
                        relation=relation_type,
                        description=relation.get("description", ""),
                    )
                    stats["relations"] += 1
            vector_store.add_documents(
                [f"chunk-{file_index}-{chunk_index}"],
                [chunk],
                [
                    {
                        "kind": "chunk",
                        "source": os.path.basename(path),
                        "chunk_index": chunk_index,
                        "entities": ";".join(list(dict.fromkeys(chunk_entities))),
                    }
                ],
            )
            stats["chunks"] += 1

    nodes = graph_store.get_all_nodes()
    edges = graph_store.get_all_edges()
    cluster_graph = nx.Graph()
    cluster_graph.add_nodes_from([node["id"] for node in nodes])
    cluster_graph.add_edges_from(
        [(edge["source"], edge["target"]) for edge in edges if edge["source"] != edge["target"]]
    )
    partition = community.best_partition(cluster_graph) if cluster_graph.number_of_nodes() > 0 else {}
    communities: dict[int, list[str]] = {}
    for node, community_id in partition.items():
        communities.setdefault(community_id, []).append(node)
    node_by_id = {node["id"]: node for node in nodes}
    for community_id, members in sorted(communities.items(), key=lambda item: -len(item[1])):
        member_set = set(members)
        community_edges = [
            edge for edge in edges if edge["source"] in member_set and edge["target"] in member_set
        ]
        entity_lines = []
        for member in members:
            attrs = {key: value for key, value in node_by_id.get(member, {}).items() if key != "id"}
            entity_lines.append(f"{member} ({attrs.get('type', '')}): {attrs.get('description', '')}")
        relation_lines = [
            f"{edge['source']} -[{edge.get('relation', '')}]-> {edge['target']}: {edge.get('description', '')}"
            for edge in community_edges
        ]
        try:
            report = generate_community_report(
                client,
                config.llm_model,
                community_id,
                entity_lines,
                relation_lines,
            )
        except Exception:
            continue
        vector_store.add_documents(
            [f"report-{community_id}"],
            [report],
            [
                {
                    "kind": "report",
                    "community": str(community_id),
                    "node_count": len(members),
                    "entities": ";".join(members[:30]),
                }
            ],
        )
        stats["communities"] += 1
        stats["reports"] += 1

    graph_store.save(config.graph_path)
    return stats
