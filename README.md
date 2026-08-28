## Enterprise Agentic GraphRAG Infrastructure
An enterprise-grade reference architecture for an Agentic GraphRAG (Knowledge Graph + Vector Search) solution deployed on Microsoft Azure using Terraform (IaC), LangGraph, FastAPI, and Streamlit/React.

## Architecture (C4 Model)
### Level 1: System Context Diagram
High-level overview of user interaction with the Enterprise Agentic GraphRAG system.

```mermaid
flowchart TD
    User([User / Client])
    
    subgraph SystemBoundary ["Enterprise Agentic GraphRAG System [Azure]"]
        GraphRAGSystem["Enterprise Agentic GraphRAG System<br/><i>(LangGraph Agent Orchestration, Knowledge Graph, Hybrid Search, LLM Synthesis)</i>"]
    end

    User -->|"Sends analytical queries & receives synthesized responses"| GraphRAGSystem
```

### Level 2: Container Diagram
View of infrastructure components mapped to Azure resources defined via Terraform.

```mermaid
flowchart TD
    User([User / Client])

    subgraph Azure ["Azure Resource Group (rg-enterprise-graphrag-dev)"]
        
        subgraph Compute ["Compute (Azure Container Apps)"]
            UI["Container App: graphrag-ui<br/><i>(Streamlit / Python or React)</i>"]
            API["Container App: graphrag-agent-api<br/><i>(FastAPI / LangGraph / Python)</i>"]
        end

        subgraph Security ["Security & Registry"]
            KV[("Azure Key Vault<br/><i>(Secrets & Keys)</i>")]
            ACR["Azure Container Registry<br/><i>(Docker Images)</i>"]
        end

        subgraph AIServices ["AI Services & Models"]
            AOAI["Azure OpenAI Service<br/><i>(LLM: Agents, Extraction, Reports + Embeddings)</i>"]
        end

        subgraph Databases ["Databases & Search (Graph + Vector)"]
            GraphDB[("Graph DB - Cosmos DB Gremlin / Neo4j<br/><i>(Nodes, Edges & Louvain Clusters)</i>")]
            Search["Azure AI Search<br/><i>(Vector Index of Chunks & Reports)</i>"]
            StateDB[("Azure Cosmos DB SQL<br/><i>(LangGraph Agent State & History)</i>")]
        end

        subgraph StorageData ["Files & Documents"]
            Blob[("Azure Blob Storage<br/><i>(Raw PDF/TXT Files & Cache)</i>")]
        end
    end

    User -->|"1. Web Interface in browser (Port 443 / 80)"| UI
    UI -->|"2. HTTP / REST API (Queries, Responses & Graph JSON)"| API
    ACR -.->|"Pulls container images"| Compute
    API -.->|"Fetches secrets on startup"| KV
    
    API -->|"3. Agent loop, entity extraction & synthesis"| AOAI
    API -->|"4. Fetches subgraphs & relationships"| GraphDB
    API -->|"5. Hybrid search & Community Reports"| Search
    API -->|"6. Reads/Writes LangGraph State Loop & Sessions"| StateDB
    API -->|"7. Reads raw documents for Ingestion / Incremental Updates"| Blob
```

## Core Features & Incremental Ingestion
- Incremental Document Upload: Supports delta ingestion. New documents undergo entity/relationship extraction without re-processing existing files. The system merges new nodes/edges into the Knowledge Graph, runs Louvain re-clustering in memory, and triggers LLM Community Summarization only for affected communities, minimizing API token costs.

- Agentic Routing (LangGraph): Dynamically chooses between Local Search (entity-level traversing for detailed facts) and Global Search (hierarchical Map-Reduce summarization for cross-document synthesis).

- Interactive Graph Visualizer: Renders subgraphs and agent execution trajectories in real time within the UI container.

## Processing Workflows

### 1. Ingestion Process (Database Creation & Incremental Updates)

```mermaid
flowchart TD
    subgraph Ingestion ["1. Ingestion Process (Database Creation & Updates)"]
        A["Source Documents<br/>(TXT files in data/)"] --> B["1. Text Chunking<br/>code / static (cheap)"]
        B --> C["2. Entity & Relationship Extraction<br/>LLM (expensive)"]
        C --> D["3. Knowledge Graph Construction<br/>graph store, NetworkX (cheap)"]
        D --> E["4. Community Detection (Louvain)<br/>graph algorithm, in-memory (cheap)"]
        E --> F["5. Community Reports Generation<br/>LLM (expensive)"]
        F --> G["6. Vectorization of Chunks, Entities & Reports<br/>embedding model (cheap)"]
    end

    class B,D,E,G cheap;
    class C,F expensive;

    classDef cheap fill:#e8f5e9,stroke:#2e7d32,stroke-width:1.5px,color:#1b5e20;
    classDef expensive fill:#fdecea,stroke:#c62828,stroke-width:1.5px,color:#b71c1c;
```

### 2. Query Process (User Interaction)

```mermaid
flowchart TD
    subgraph Query ["2. Query Process (User Interaction)"]
        H["User Query"] --> I["Search Mode<br/>(client-selected: local | global)"]
        I -->|"mode = local"| J["2a. Local Search<br/>vector search → subgraph traversal → 1× LLM synthesis (cheap)"]
        I -->|"mode = global"| K["2b. Global Search<br/>vector search → LLM map-reduce cascade (expensive)"]
        J --> L["Final Answer<br/>+ subgraph JSON"]
        K --> L
    end

    class I,J cheap;
    class K expensive;

    classDef cheap fill:#e8f5e9,stroke:#2e7d32,stroke-width:1.5px,color:#1b5e20;
    classDef expensive fill:#fdecea,stroke:#c62828,stroke-width:1.5px,color:#b71c1c;
```
## Local Prototype — Running the App

The repository contains a runnable prototype: `backend/` (FastAPI + NetworkX + ChromaDB + OpenAI) and `frontend/` (React + Vite + MUI Joy + react-force-graph-2d).

### Prerequisites
- `OPENAI_API_KEY` present in the root `.env` file (models used: `gpt-4o-mini`, `text-embedding-3-small`).
- Input documents in `data/` (TXT files). The knowledge graph persists in `data/graph.gpickle`, the vector index in `.chroma_db/`.

### Option A — Docker Compose (recommended)

```bash
docker compose up --build
```

- Frontend UI: http://localhost:5173
- Backend API: http://localhost:8000 (docs at `/docs`)
- The frontend talks to the backend through the Vite dev proxy (`/api` → `http://backend:8000`) on the internal Docker network `graphrag-net`.
- Volumes persist `./data` and `./.chroma_db` between container restarts.

### Option B — Local development

Backend (from the repository root):

```bash
python -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
cd backend
../.venv/bin/uvicorn app:app --host 0.0.0.0 --port 8000
```

Frontend (in a second terminal):

```bash
cd frontend
npm install
npm run dev
```

### API endpoints

| Method | Path        | Description                                              |
| ------ | ----------- | -------------------------------------------------------- |
| POST   | `/ingest`   | Run the full ingestion pipeline (chunk → extract → graph → communities → reports) |
| POST   | `/query`    | `{"query": "...", "mode": "local" \| "global"}` → `{answer, subgraph}` |
| POST   | `/upload`   | Multipart upload of a `.txt` file into `data/`           |
| GET    | `/stats`    | Node / edge / vector-document counts                     |
| GET    | `/health`   | Liveness probe                                           |

### Repository Pattern (migration path)

`backend/src/storage/base.py` defines `AbstractGraphStore` and `AbstractVectorStore`. `NetworkXGraphStore` (→ Azure Cosmos DB Gremlin) and `ChromaVectorStore` (→ Azure AI Search) implement them; `ingestion.py` and `search.py` depend only on the abstractions, so the Azure migration is a drop-in replacement of the two store classes.
