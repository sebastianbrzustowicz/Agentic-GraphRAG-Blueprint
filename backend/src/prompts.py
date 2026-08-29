"""Domain-agnostic LLM system prompts, overridable via a JSON file.

The blueprint ships with universal (non-medical) prompts in ``backend/prompts.json``.
To tailor the assistant to a specific domain, copy that file, edit the ``system``
strings, and point the ``PROMPTS_PATH`` environment variable at your copy. A
partial file only needs to contain the keys you want to override.
"""

import json
import os

DEFAULT_PROMPTS = {
    "extraction": {
        "system": (
            "You are a knowledge graph extraction engine. "
            "Extract entities and their relationships from the provided text. "
            "Return JSON only with the keys 'entities' and 'relations'. "
            "Each entity is an object with keys 'name', 'type', 'description'. "
            "Each relation is an object with keys 'source', 'target', 'type', 'description'. "
            "Use canonical entity names and reuse the exact same name for the same entity across chunks. "
            "Be thorough: capture every meaningful relationship between the entities you find."
        )
    },
    "community_report": {
        "system": (
            "You are a knowledge graph analyst. "
            "Write a concise but information-dense community report covering the key entities, "
            "relationships and implications of the community. "
            "Write in the language of the input. Return plain text."
        )
    },
    "local_search": {
        "system": (
            "You are an expert answering questions using only the provided knowledge graph context. "
            "Base your answer on the context, name the entities you cite, and state clearly when "
            "the context does not contain enough information."
        )
    },
    "map_report": {
        "system": (
            "You are an expert. From the community report below extract only the information "
            "relevant to the user's question. Return concise bullet points and keep entity names."
        )
    },
    "reduce_summaries": {
        "system": (
            "You are an expert. Synthesize the partial summaries below into one coherent, "
            "complete answer to the user's question. Merge overlapping facts, resolve "
            "contradictions, do not invent information."
        )
    },
}


def _bundled_path() -> str:
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "prompts.json")


def load_prompts() -> dict:
    """Resolve the prompt set: ``PROMPTS_PATH`` env > bundled ``prompts.json`` > built-in defaults."""
    candidates = [os.getenv("PROMPTS_PATH", ""), _bundled_path()]
    for path in candidates:
        if not path or not os.path.exists(path):
            continue
        try:
            with open(path, encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError):
            continue
        merged = {**DEFAULT_PROMPTS}
        for key, value in data.items():
            if key in merged and isinstance(value, dict):
                merged[key].update(value)
            else:
                merged[key] = value
        return merged
    return DEFAULT_PROMPTS
