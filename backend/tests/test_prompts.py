import json

from src.prompts import DEFAULT_PROMPTS, load_prompts


def test_bundled_prompts_are_domain_agnostic(tmp_path, monkeypatch):
    monkeypatch.delenv("PROMPTS_PATH", raising=False)
    prompts = load_prompts()
    assert "medical" not in prompts["extraction"]["system"].lower()
    assert "knowledge graph extraction engine" in prompts["extraction"]["system"]
    assert "medical" not in prompts["local_search"]["system"].lower()


def test_custom_prompts_partially_override(tmp_path, monkeypatch):
    custom = {"extraction": {"system": "Extract medical entities only."}}
    path = tmp_path / "prompts.custom.json"
    path.write_text(json.dumps(custom), encoding="utf-8")
    monkeypatch.setenv("PROMPTS_PATH", str(path))
    prompts = load_prompts()
    assert prompts["extraction"]["system"] == "Extract medical entities only."
    # Keys not mentioned in the custom file fall back to the defaults.
    assert prompts["local_search"]["system"] == DEFAULT_PROMPTS["local_search"]["system"]
