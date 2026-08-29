import glob
import hashlib
import json
import logging
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import igraph as ig
import leidenalg as la
from openai import APIConnectionError, APITimeoutError, BadRequestError, NotFoundError, RateLimitError

from src.config import Config
from src.progress import file_finished, file_started
from src.progress import start as progress_start
from src.storage.base import AbstractGraphStore, AbstractVectorStore

CHARS_PER_TOKEN = 4
BATCH_MARKER = "---CHUNK"

logger = logging.getLogger(__name__)

RETRYABLE = (NotFoundError, APIConnectionError, APITimeoutError, RateLimitError)

# Some models (e.g. gpt-5.6-luna) only accept the default temperature and reject
# temperature=0 with a 400. Once a model proves incompatible we remember it and
# skip the parameter for the rest of the process.
_NO_TEMP_MODELS: set[str] = set()


def _retry_call(fn, *args, attempts: int = 4, delay: float = 1.0, **kwargs):
    last_exc: Exception | None = None
    for attempt in range(attempts):
        try:
            return fn(*args, **kwargs)
        except RETRYABLE as exc:
            last_exc = exc
            if attempt < attempts - 1:
                time.sleep(delay * (2**attempt))
    assert last_exc is not None
    raise last_exc


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
        if model not in _NO_TEMP_MODELS:
            try:
                response = _retry_call(client.chat.completions.create, **{**kwargs, "temperature": 0})
                return response.choices[0].message.content or ""
            except BadRequestError as exc:
                if "temperature" not in str(exc).lower():
                    raise
                logger.info("model %s does not support temperature=0; using default", model)
                _NO_TEMP_MODELS.add(model)
    response = _retry_call(client.chat.completions.create, **kwargs)
    return response.choices[0].message.content or ""


def _parse_json(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").strip()
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
    return json.loads(cleaned)


_EXTRACTION_SYSTEM = (
    "You are a medical knowledge graph extraction engine. "
    "Extract medical entities and their relationships from the provided text. "
    "Return JSON only with the keys 'entities' and 'relations'. "
    "Each entity is an object with keys 'name', 'type', 'description'. "
    "Each relation is an object with keys 'source', 'target', 'type', 'description'. "
    "Use canonical entity names and reuse the exact same name for the same entity across chunks. "
    "Be thorough: capture every meaningful relationship between the entities you find."
)


def _extraction_system(known_entities: set[str] | None = None) -> str:
    system = _EXTRACTION_SYSTEM
    if known_entities:
        names = sorted(known_entities)[:150]
        system += (
            " Already-known entity names: "
            + ", ".join(names)
            + ". When you encounter one of these entities, reuse its exact already-known name"
            " so the graph can link documents."
        )
    return system


def extract_graph(
    client,
    model: str,
    chunk: str,
    known_entities: set[str] | None = None,
) -> tuple[list[dict], list[dict]]:
    raw = _chat(client, model, _extraction_system(known_entities), chunk, json_mode=True)
    data = _parse_json(raw)
    return data.get("entities", []), data.get("relations", [])


def extract_graph_batch(
    client,
    model: str,
    chunks: list[str],
    batch_size: int = 5,
    known_entities: set[str] | None = None,
) -> list[tuple[list[dict], list[dict]]]:
    """Extract entities/relations for several chunks in a single LLM call.

    The user message contains the chunks separated by ``---CHUNK <i>`` markers and the
    model is asked to return one result per chunk. Raises on any parse failure so the
    caller can fall back to one call per chunk.
    """
    system = (
        _extraction_system(known_entities)
        + " The user message contains several text chunks separated by '"
        + BATCH_MARKER
        + " <i>' markers. For EACH chunk return JSON only with the key 'chunks': "
        "a list of objects, one per chunk, each with keys 'chunk_index' (the number "
        "after the marker), 'entities' and 'relations'."
    )
    results: list[tuple[list[dict], list[dict]] | None] = [None] * len(chunks)
    for start in range(0, len(chunks), batch_size):
        batch = chunks[start : start + batch_size]
        payload = "\n\n".join(f"{BATCH_MARKER} {i}\n{text}" for i, text in enumerate(batch))
        raw = _chat(client, model, system, payload, json_mode=True)
        data = _parse_json(raw)
        parsed = data.get("chunks")
        if not isinstance(parsed, list):
            raise ValueError("expected a 'chunks' list in the batch response")
        for item in parsed:
            if not isinstance(item, dict) or "chunk_index" not in item:
                continue
            index = start + int(item["chunk_index"])
            if 0 <= index < len(chunks):
                results[index] = (item.get("entities", []), item.get("relations", []))
    if any(result is None for result in results):
        raise ValueError("batch response did not cover every chunk")
    return [result for result in results if result is not None]


def _extract_batch_with_fallback(
    client,
    model: str,
    batch: list[str],
    known_entities: set[str] | None = None,
) -> list[tuple[list[dict], list[dict]]]:
    if len(batch) == 1:
        # Single chunk: skip the batch round-trip entirely.
        return [extract_graph(client, model, batch[0], known_entities)]
    try:
        return extract_graph_batch(client, model, batch, known_entities=known_entities)
    except Exception as exc:
        logger.warning("batch extraction failed (%s); falling back to per-chunk calls", exc)
        return [extract_graph(client, model, chunk, known_entities) for chunk in batch]


def _extract_file(
    client,
    model: str,
    chunks: list[str],
    batch_size: int,
    max_concurrency: int,
    known_entities: set[str] | None = None,
) -> list[tuple[list[dict], list[dict]]]:
    """Extract all chunks of one file: batched LLM calls executed in parallel."""
    batches = [chunks[i : i + batch_size] for i in range(0, len(chunks), batch_size)]
    ordered: list[list[tuple[list[dict], list[dict]]]] = [None] * len(batches)  # type: ignore[list-item]
    with ThreadPoolExecutor(max_workers=max_concurrency) as executor:
        futures = {
            executor.submit(_extract_batch_with_fallback, client, model, batch, known_entities): index
            for index, batch in enumerate(batches)
        }
        for future in as_completed(futures):
            ordered[futures[future]] = future.result()
    results: list[tuple[list[dict], list[dict]]] = []
    for batch_results in ordered:
        results.extend(batch_results)
    return results


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


def _community_partition(
    nodes: list[dict],
    edges: list[dict],
) -> dict[int, list[str]]:
    """Detect communities with the Leiden algorithm (igraph + leidenalg)."""
    index: dict[str, int] = {}
    names: list[str] = []

    def _idx(name: str) -> int:
        if name not in index:
            index[name] = len(names)
            names.append(name)
        return index[name]

    # Every node must be a vertex, even isolated ones; edges may also
    # introduce endpoints that are not in the node list.
    for node in nodes:
        _idx(node["id"])
    edge_list = [
        (_idx(edge["source"]), _idx(edge["target"]))
        for edge in edges
        if edge["source"] != edge["target"]
    ]
    graph = ig.Graph(n=len(names), edges=edge_list)
    if len(names) == 0:
        return {}
    partition = la.find_partition(graph, la.ModularityVertexPartition, seed=0)
    communities: dict[int, list[str]] = {}
    for vertex, community_id in enumerate(partition.membership):
        communities.setdefault(community_id, []).append(names[vertex])
    return communities


def _community_fingerprint(members: list[str], community_edges: list[dict]) -> str:
    """Stable fingerprint of a community: membership + internal edges."""
    payload = json.dumps(
        {
            "members": sorted(members),
            "edges": sorted((edge["source"], edge["target"]) for edge in community_edges),
        },
        sort_keys=True,
    )
    return hashlib.sha1(payload.encode()).hexdigest()


def _file_hash(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def _state_path(config: Config) -> str:
    return os.path.join(config.data_dir, ".ingest_state.json")


def _load_state(config: Config) -> dict:
    path = _state_path(config)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        logger.warning("could not read ingest state at %s; starting fresh", path)
        return {}


def _save_state(config: Config, state: dict) -> None:
    with open(_state_path(config), "w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2)


def _add_in_batches(
    vector_store: AbstractVectorStore,
    ids: list[str],
    documents: list[str],
    metadatas: list[dict],
    batch_size: int,
) -> None:
    if not ids:
        return
    for start in range(0, len(ids), batch_size):
        vector_store.add_documents(
            ids[start : start + batch_size],
            documents[start : start + batch_size],
            metadatas[start : start + batch_size],
        )


def run_ingestion(
    config: Config,
    graph_store: AbstractGraphStore,
    vector_store: AbstractVectorStore,
) -> dict:
    files = sorted(glob.glob(os.path.join(config.data_dir, "*.txt")))
    logger.info("ingestion started: %d file(s) in %s", len(files), config.data_dir)

    state = _load_state(config)
    force_reset = config.force_reset or not state
    if force_reset:
        graph_store.reset()
        vector_store.reset()
        known_entities: set[str] = set()
        previous_files: dict[str, str] = {}
    else:
        known_entities = {node["id"] for node in graph_store.get_all_nodes()}
        previous_files = state.get("files", {})
        if vector_store.count() == 0 and graph_store.node_count() > 0:
            logger.warning("vector store is empty but the graph has data; forcing a full rebuild")
            force_reset = True
            graph_store.reset()
            vector_store.reset()
            known_entities = set()
            previous_files = {}

    to_process = []
    for path in files:
        digest = _file_hash(path)
        if force_reset or previous_files.get(os.path.basename(path)) != digest:
            to_process.append((path, digest))

    progress_start(len(files), [os.path.basename(path) for path in files], len(to_process))
    client = config.client()
    stats = {
        "files": len(files),
        "chunks": 0,
        "entities": 0,
        "relations": 0,
        "communities": 0,
        "reports": 0,
    }
    changed_nodes: set[str] = set()
    new_file_state: dict[str, str] = {}

    for path, digest in to_process:
        file_started(os.path.basename(path))
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        chunks = chunk_text(text, config.chunk_size, config.chunk_overlap)
        if not chunks:
            logger.warning(
                "file %s produced no chunks (size=%d bytes, read=%d chars)",
                path,
                os.path.getsize(path),
                len(text),
            )
        else:
            logger.info("chunked %s into %d chunks", path, len(chunks))
        if chunks:
            extraction = _extract_file(
                client,
                config.llm_model,
                chunks,
                config.extract_batch_size,
                config.max_concurrency,
                known_entities,
            )
        else:
            extraction = []

        entity_ids: list[str] = []
        entity_docs: list[str] = []
        entity_metas: list[dict] = []
        chunk_ids: list[str] = []
        chunk_docs: list[str] = []
        chunk_metas: list[dict] = []
        for chunk_index, chunk in enumerate(chunks):
            try:
                entities, relations = extraction[chunk_index]
            except IndexError:
                logger.warning("no extraction result for chunk %d of %s", chunk_index, path)
                continue
            chunk_entities = []
            for entity in entities:
                name = entity.get("name", "").strip()
                if not name:
                    continue
                chunk_entities.append(name)
                if name not in known_entities:
                    known_entities.add(name)
                    graph_store.add_node(
                        name,
                        type=entity.get("type", ""),
                        description=entity.get("description", ""),
                    )
                    entity_ids.append(f"entity-{name}")
                    entity_docs.append(entity.get("description") or name)
                    entity_metas.append(
                        {"kind": "entity", "name": name, "type": entity.get("type", "")}
                    )
                    stats["entities"] += 1
                    changed_nodes.add(name)
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
                    changed_nodes.add(source)
                    changed_nodes.add(target)
            basename = os.path.basename(path)
            chunk_ids.append(f"chunk-{basename}-{chunk_index}")
            chunk_docs.append(chunk)
            chunk_metas.append(
                {
                    "kind": "chunk",
                    "source": basename,
                    "chunk_index": chunk_index,
                    "entities": ";".join(list(dict.fromkeys(chunk_entities))),
                }
            )
            stats["chunks"] += 1

        _add_in_batches(vector_store, entity_ids, entity_docs, entity_metas, config.embed_batch_size)
        _add_in_batches(vector_store, chunk_ids, chunk_docs, chunk_metas, config.embed_batch_size)
        new_file_state[os.path.basename(path)] = digest
        file_finished()

    nodes = graph_store.get_all_nodes()
    edges = graph_store.get_all_edges()
    communities = _community_partition(nodes, edges)
    node_by_id = {node["id"]: node for node in nodes}
    previous_reports = state.get("reports", {}) if not force_reset else {}
    current_reports: dict[str, str] = {}
    to_report: list[dict] = []

    for community_id, members in sorted(communities.items(), key=lambda item: -len(item[1])):
        member_set = set(members)
        community_edges = [
            edge for edge in edges if edge["source"] in member_set and edge["target"] in member_set
        ]
        fingerprint = _community_fingerprint(members, community_edges)
        report_id = f"report-{fingerprint[:12]}"
        current_reports[report_id] = fingerprint
        stats["communities"] += 1
        if changed_nodes & member_set or report_id not in previous_reports:
            to_report.append(
                {
                    "report_id": report_id,
                    "community_id": community_id,
                    "members": members,
                    "community_edges": community_edges,
                    "node_by_id": node_by_id,
                }
            )
        else:
            logger.info("community %d unchanged; reusing report %s", community_id, report_id)

    def _generate(item: dict) -> tuple[str, str]:
        entity_lines = []
        for member in item["members"]:
            attrs = {key: value for key, value in item["node_by_id"].get(member, {}).items() if key != "id"}
            entity_lines.append(f"{member} ({attrs.get('type', '')}): {attrs.get('description', '')}")
        relation_lines = [
            f"{edge['source']} -[{edge.get('relation', '')}]-> {edge['target']}: {edge.get('description', '')}"
            for edge in item["community_edges"]
        ]
        return item["report_id"], generate_community_report(
            client,
            config.llm_model,
            item["community_id"],
            entity_lines,
            relation_lines,
        )

    if to_report:
        with ThreadPoolExecutor(max_workers=config.max_concurrency) as executor:
            futures = {executor.submit(_generate, item): item for item in to_report}
            for future in as_completed(futures):
                item = futures[future]
                try:
                    report_id, report = future.result()
                except Exception as exc:
                    logger.warning("community report generation failed for %s: %s", item["report_id"], exc)
                    continue
                vector_store.add_documents(
                    [report_id],
                    [report],
                    [
                        {
                            "kind": "report",
                            "community": report_id,
                            "node_count": len(item["members"]),
                            "entities": ";".join(item["members"][:30]),
                        }
                    ],
                )
                stats["reports"] += 1

    stale_ids = [report_id for report_id in previous_reports if report_id not in current_reports]
    if stale_ids:
        vector_store.delete(stale_ids)
        logger.info("removed %d stale community report(s)", len(stale_ids))

    graph_store.save(config.graph_path)
    merged_files = {**previous_files, **new_file_state} if not force_reset else new_file_state
    _save_state(config, {"files": merged_files, "reports": current_reports})
    return stats
