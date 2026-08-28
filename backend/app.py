import logging
import os
import threading

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("graphrag")

from src.config import Config
from src.ingestion import run_ingestion
from src.progress import (
    set_error as progress_set_error,
    set_result as progress_set_result,
    snapshot as progress_snapshot,
    stop as progress_stop,
)
from src.search import global_search, local_search
from src.storage.graph_store import NetworkXGraphStore
from src.storage.vector_store import ChromaVectorStore

config = Config()
graph_store = NetworkXGraphStore()
vector_store = ChromaVectorStore(config)

os.makedirs(config.data_dir, exist_ok=True)

if os.path.exists(config.graph_path):
    graph_store.load(config.graph_path)

app = FastAPI(title="Agentic GraphRAG Prototype", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    query: str
    mode: str = "local"


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/stats")
def stats() -> dict:
    return {
        "nodes": graph_store.node_count(),
        "edges": graph_store.edge_count(),
        "documents": vector_store.count(),
    }


@app.post("/upload")
async def upload(file: UploadFile = File(...)) -> dict:
    filename = os.path.basename(file.filename or "upload.txt")
    os.makedirs(config.data_dir, exist_ok=True)
    target = os.path.join(config.data_dir, filename)
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail=f"Uploaded file '{filename}' is empty")
    with open(target, "wb") as handle:
        handle.write(data)
    logger.info("uploaded %s (%d bytes) -> %s", filename, len(data), target)
    return {"filename": filename, "path": target}


@app.post("/ingest")
def ingest() -> dict:
    if progress_snapshot()["running"]:
        raise HTTPException(status_code=409, detail="Ingestion is already running")
    thread = threading.Thread(target=_run_ingestion_async, daemon=True)
    thread.start()
    return {"started": True}


def _run_ingestion_async() -> None:
    try:
        stats = run_ingestion(config, graph_store, vector_store)
        progress_set_result(stats)
    except Exception as exc:
        logger.exception("ingestion failed")
        progress_set_error(str(exc))
    finally:
        progress_stop()


@app.get("/progress")
def ingest_progress() -> dict:
    return progress_snapshot()


@app.post("/query")
def query(request: QueryRequest) -> dict:
    try:
        if request.mode == "global":
            return global_search(request.query, config, graph_store, vector_store)
        return local_search(request.query, config, graph_store, vector_store)
    except Exception as exc:
        logger.exception("query failed")
        raise HTTPException(status_code=503, detail=f"Search unavailable: {exc}") from exc
