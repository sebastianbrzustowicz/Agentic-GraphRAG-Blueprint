import { useEffect, useState } from "react";
import Alert from "@mui/joy/Alert";
import Box from "@mui/joy/Box";
import Button from "@mui/joy/Button";
import Card from "@mui/joy/Card";
import CardContent from "@mui/joy/CardContent";
import LinearProgress from "@mui/joy/LinearProgress";
import List from "@mui/joy/List";
import ListItem from "@mui/joy/ListItem";
import Stack from "@mui/joy/Stack";
import Typography from "@mui/joy/Typography";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import { fetchProgress, fetchStats, runIngest, uploadFiles } from "../api";
import type { GraphStats, IngestProgress } from "../types";

interface IngestionPanelProps {
  onStatsChange: (stats: GraphStats) => void;
}

type Phase = "idle" | "uploading" | "ingesting";

export default function IngestionPanel({ onStatsChange }: IngestionPanelProps) {
  const [files, setFiles] = useState<File[]>([]);
  const [phase, setPhase] = useState<Phase>("idle");
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<GraphStats | null>(null);
  const [progress, setProgress] = useState<IngestProgress | null>(null);

  const busy = phase !== "idle";

  const refreshStats = async () => {
    try {
      const current = await fetchStats();
      setStats(current);
      onStatsChange(current);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Stats request failed");
    }
  };

  useEffect(() => {
    refreshStats().catch(() => undefined);
  }, []);

  // While ingestion is running, poll /stats and /progress a few times per
  // second so the numbers update live and per-file progress is visible.
  useEffect(() => {
    if (phase !== "ingesting") {
      return;
    }
    const poll = async () => {
      try {
        const [current, p] = await Promise.all([fetchStats(), fetchProgress()]);
        setStats(current);
        onStatsChange(current);
        setProgress(p);
        if (p.running && p.total_files > 0) {
          const done = p.processed_files;
          const remaining = p.total_files - done;
          const currentLine = p.current_file ? ` · now: ${p.current_file}` : "";
          setStatus(
            `Processing ${done + 1}/${p.total_files} — ${done} file(s) done, ${remaining} left${currentLine}`
          );
        }
      } catch {
        // transient poll failure: keep the previous state
      }
    };
    const timer = setInterval(poll, 3000);
    return () => clearInterval(timer);
  }, [phase, onStatsChange]);

  const process = async () => {
    if (busy) {
      return;
    }
    setError(null);
    setProgress(null);

    if (files.length > 0) {
      setPhase("uploading");
      setStatus(`Uploading ${files.length} file(s)…`);
      try {
        await uploadFiles(files);
        setFiles([]);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Upload failed");
        setStatus(null);
        setPhase("idle");
        return;
      }
    }

    setPhase("ingesting");
    setStatus("Ingesting… this can take several minutes.");
    try {
      const result = await runIngest();
      setStatus(
        `Ingestion finished: ${result.entities} entities, ${result.relations} relations, ${result.chunks} chunks, ${result.communities} communities.`
      );
      await refreshStats();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ingestion failed");
      setStatus(null);
    } finally {
      setPhase("idle");
      setProgress(null);
    }
  };

  return (
    <Card variant="outlined">
      <CardContent>
        <Typography level="title-md" sx={{ mb: 2 }}>
          Ingestion &amp; Data
        </Typography>
        <Button
          component="label"
          variant="outlined"
          color="neutral"
          startDecorator={<CloudUploadIcon />}
        >
          Select .txt files
          <input
            type="file"
            multiple
            accept=".txt"
            hidden
            onChange={(event) => setFiles(Array.from(event.target.files ?? []))}
          />
        </Button>
        {files.length > 0 ? (
          <List size="sm" sx={{ mt: 1 }}>
            {files.map((file) => (
              <ListItem key={file.name}>{file.name}</ListItem>
            ))}
          </List>
        ) : null}
        <Button
          onClick={process}
          loading={busy}
          disabled={busy}
          startDecorator={<CloudUploadIcon />}
          sx={{ mt: 1 }}
        >
          {files.length > 0 ? "Upload & Ingest" : "Run /ingest"}
        </Button>
        {busy ? <LinearProgress sx={{ mt: 2 }} /> : null}
        {status ? (
          <Typography level="body-sm" sx={{ mt: 1 }}>
            {status}
          </Typography>
        ) : null}
        {error ? (
          <Alert color="danger" sx={{ mt: 1 }}>
            {error}
          </Alert>
        ) : null}
        {progress && progress.running && progress.total_files > 0 ? (
          <Typography level="body-xs" color="neutral" sx={{ mt: 0.5 }}>
            {progress.processed_files} of {progress.total_files} files processed
          </Typography>
        ) : null}
        {stats ? (
          <Box sx={{ mt: 2 }}>
            <Typography level="title-sm" sx={{ mb: 1 }}>
              Database
            </Typography>
            <Typography level="body-sm">
              {stats.nodes} nodes · {stats.edges} edges · {stats.documents} vector documents
            </Typography>
          </Box>
        ) : null}
      </CardContent>
    </Card>
  );
}
