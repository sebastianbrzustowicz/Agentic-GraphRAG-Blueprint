import os
import tempfile

# Point the application's file/vector/graph storage at a throwaway location
# BEFORE `app` / `src.config` are imported, so tests never touch repo state.
_TMP = tempfile.mkdtemp(prefix="graphrag-tests-")
os.environ.setdefault("DATA_DIR", os.path.join(_TMP, "data"))
os.environ.setdefault("CHROMA_DIR", os.path.join(_TMP, "chroma"))
os.environ.setdefault("GRAPH_PATH", os.path.join(_TMP, "graph.gpickle"))
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("OPENAI_BASE_URL", "")
