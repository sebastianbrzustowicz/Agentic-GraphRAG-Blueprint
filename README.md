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
            GraphDB[("Graph DB - Cosmos DB Gremlin / Neo4j<br/><i>(Nodes, Edges & Leiden Clusters)</i>")]
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
- Incremental Document Upload: Supports delta ingestion. New documents undergo entity/relationship extraction without re-processing existing files. The system merges new nodes/edges into the Knowledge Graph, runs Leiden re-clustering in memory, and triggers LLM Community Summarization only for affected communities, minimizing API token costs.

- Agentic Routing (LangGraph): Dynamically chooses between Local Search (entity-level traversing for detailed facts) and Global Search (hierarchical Map-Reduce summarization for cross-document synthesis).

- Interactive Graph Visualizer: Renders subgraphs and agent execution trajectories in real time within the UI container.

## Processing Workflows

### 1. Ingestion Process (Database Creation & Incremental Updates)

```mermaid
flowchart TD
    subgraph Ingestion ["1. INGESTION PROCESS (Database Creation & Updates)"]
        A[Source PDF / TXT Documents] --> B["1. Text Chunking<br/>⚙️ Code / Static (Cheap)"]
        B --> C["2. Entity & Relationship Extraction<br/>🤖 LLM Model (Very Expensive)"]
        C --> D["3. Knowledge Graph Construction<br/>💾 Graph DB / Code (Cheap)"]
        D --> E["4. Leiden Clustering<br/>🧮 Graph Algorithm / Static (Cheap)"]
        E --> F["5. Community Reports Generation<br/>🤖 LLM Model (Very Expensive)"]
        F --> G["6. Vectorization of Reports & Chunks<br/>📐 Vector / Embedding Model (Cheap)"]
    end

    class B,D,E,G cheap;
    class C,F expensive;

    classDef cheap fill:#1e4620,stroke:#4caf50,color:#fff,stroke-width:2px;
    classDef expensive fill:#5c0606,stroke:#ef5350,color:#fff,stroke-width:2px;
```

### 2. Query Process (User Interaction)

```mermaid
flowchart TD
    subgraph Query ["2. QUERY PROCESS (User Interaction)"]
        H[User Query] --> I["1. Intent Classifier / Router<br/>🤖 LLM Model - short prompt (Cheap)"]
        I -->|Detailed Query| J["2a. Local Search<br/>📐 Embedding + 💾 DB + 🤖 1x LLM (Cheap)"]
        I -->|Synthesized Query| K["2b. Global Search<br/>💾 DB + 🤖 Map-Reduce LLM Cascade (Expensive)"]
        J --> L[Final Answer]
        K --> L
    end

    class I,J cheap;
    class K expensive;

    classDef cheap fill:#1e4620,stroke:#4caf50,color:#fff,stroke-width:2px;
    classDef expensive fill:#5c0606,stroke:#ef5350,color:#fff,stroke-width:2px;
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
