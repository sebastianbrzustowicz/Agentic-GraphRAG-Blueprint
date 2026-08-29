import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

from src.prompts import load_prompts

load_dotenv()


def _find_root() -> str:
    current = os.path.dirname(os.path.abspath(__file__))
    while True:
        if os.path.isdir(os.path.join(current, "data")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return current
        current = parent


ROOT = _find_root()


@dataclass(frozen=True)
class Config:
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    openai_base_url: str = field(default_factory=lambda: os.getenv("OPENAI_BASE_URL", ""))
    llm_model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "gpt-4o-mini"))
    embedding_model: str = field(default_factory=lambda: os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"))
    data_dir: str = field(default_factory=lambda: os.path.join(ROOT, os.getenv("DATA_DIR", "data")))
    graph_path: str = field(default_factory=lambda: os.path.join(ROOT, os.getenv("GRAPH_PATH", "data/graph.gpickle")))
    chroma_dir: str = field(default_factory=lambda: os.path.join(ROOT, os.getenv("CHROMA_DIR", ".chroma_db")))
    chunk_size: int = field(default_factory=lambda: int(os.getenv("CHUNK_SIZE", "400")))
    chunk_overlap: int = field(default_factory=lambda: int(os.getenv("CHUNK_OVERLAP", "50")))
    top_k: int = field(default_factory=lambda: int(os.getenv("TOP_K", "5")))
    local_top_k: int = field(default_factory=lambda: int(os.getenv("LOCAL_TOP_K", "8")))
    global_top_k: int = field(default_factory=lambda: int(os.getenv("GLOBAL_TOP_K", "5")))
    subgraph_radius: int = field(default_factory=lambda: int(os.getenv("SUBGRAPH_RADIUS", "1")))
    max_concurrency: int = field(default_factory=lambda: int(os.getenv("LLM_MAX_CONCURRENCY", "4")))
    extract_batch_size: int = field(default_factory=lambda: int(os.getenv("EXTRACT_BATCH_SIZE", "1")))
    embed_batch_size: int = field(default_factory=lambda: int(os.getenv("EMBED_BATCH_SIZE", "32")))
    force_reset: bool = field(default_factory=lambda: os.getenv("FORCE_RESET", "").lower() in ("1", "true", "yes"))
    prompts: dict = field(default_factory=load_prompts)

    def client(self):
        from openai import OpenAI

        return OpenAI(api_key=self.openai_api_key, base_url=self.openai_base_url or None)
