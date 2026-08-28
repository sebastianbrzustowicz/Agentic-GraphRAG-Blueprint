export interface GraphNode {
  id: string;
  type?: string;
  description?: string;
  [key: string]: unknown;
}

export interface GraphEdge {
  source: string;
  target: string;
  relation?: string;
  description?: string;
  [key: string]: unknown;
}

export interface Subgraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface QueryResponse {
  answer: string;
  subgraph: Subgraph;
}

export interface IngestStats {
  files: number;
  chunks: number;
  entities: number;
  relations: number;
  communities: number;
  reports: number;
}

export interface GraphStats {
  nodes: number;
  edges: number;
  documents: number;
}

export type SearchMode = "local" | "global";
