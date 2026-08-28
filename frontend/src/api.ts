import axios from "axios";
import type { GraphStats, IngestProgress, IngestStats, QueryResponse, SearchMode } from "./types";

const client = axios.create({ baseURL: "/api", timeout: 1800000 });

// Extract a readable message from an axios/fetch error, preferring the
// backend's `detail` field (e.g. FastAPI HTTPException) over the generic
// "Request failed with status code 5xx" text.
export function errorMessage(err: unknown): string {
  if (err && typeof err === "object" && "response" in err) {
    const detail = (err as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
    if (detail) {
      return String(detail);
    }
  }
  return err instanceof Error ? err.message : String(err);
}

export async function runQuery(query: string, mode: SearchMode): Promise<QueryResponse> {
  const response = await client.post<QueryResponse>("/query", { query, mode });
  return response.data;
}

export async function runIngest(): Promise<IngestStats> {
  const response = await client.post<IngestStats>("/ingest");
  return response.data;
}

export async function uploadFiles(files: File[]): Promise<string[]> {
  const form = new FormData();
  files.forEach((file) => form.append("file", file));
  const responses = await Promise.all(files.map((file) => {
    const single = new FormData();
    single.append("file", file);
    return client.post<{ filename: string }>("/upload", single);
  }));
  return responses.map((response) => response.data.filename);
}

export async function fetchStats(): Promise<GraphStats> {
  const response = await client.get<GraphStats>("/stats");
  return response.data;
}

export async function fetchProgress(): Promise<IngestProgress> {
  const response = await client.get<IngestProgress>("/progress");
  return response.data;
}
