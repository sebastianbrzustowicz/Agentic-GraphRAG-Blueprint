import os

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.config import Config
from src.ingestion import run_ingestion
from src.search import global_search, local_search
from src.storage.graph_store import NetworkXGraphStore
from src.storage.vector_store import ChromaVectorStore

config = Config()
graph_store = NetworkXGraphStore()
vector_store = ChromaVectorStore(config)

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
    target = os.path.join(config.data_dir, filename)
    with open(target, "wb") as handle:
        handle.write(await file.read())
    return {"filename": filename, "path": target}


@app.post("/ingest")
def ingest() -> dict:
    return run_ingestion(config, graph_store, vector_store)


@app.post("/query")
def query(request: QueryRequest) -> dict:
    if request.mode == "global":
        return global_search(request.query, config, graph_store, vector_store)
    return local_search(request.query, config, graph_store, vector_store)
