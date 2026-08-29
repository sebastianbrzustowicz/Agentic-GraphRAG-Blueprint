import { useCallback, useEffect, useRef, useState } from "react";
import Alert from "@mui/joy/Alert";
import Box from "@mui/joy/Box";
import Button from "@mui/joy/Button";
import Card from "@mui/joy/Card";
import CardContent from "@mui/joy/CardContent";
import LinearProgress from "@mui/joy/LinearProgress";
import List from "@mui/joy/List";
import ListItem from "@mui/joy/ListItem";
import Typography from "@mui/joy/Typography";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import { errorMessage, fetchProgress, fetchStats, runIngest, uploadFiles } from "../api";
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
  const sawRunning = useRef(false);

  const busy = phase !== "idle";

  const refreshStats = useCallback(async () => {
    try {
      const current = await fetchStats();
      setStats(current);
      onStatsChange(current);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Stats request failed");
    }
  }, [onStatsChange]);

  useEffect(() => {
    refreshStats().catch(() => undefined);
  }, [refreshStats]);

  // While ingestion is running, poll /stats and /progress a few times per
  // second so the numbers update live and per-file progress is visible.
  // /ingest is async: the HTTP call returns immediately and the backend
  // processes in the background; this poll also detects completion
  // (running -> false) and surfaces the final result or error.
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
        if (p.running) {
          sawRunning.current = true;
          const toProcess = p.to_process > 0 ? p.to_process : p.total_files;
          if (toProcess > 0) {
            const done = p.processed_files;
            const currentLine = p.current_file ? ` · now: ${p.current_file}` : "";
            setStatus(`Processing ${Math.min(done + 1, toProcess)}/${toProcess} - ${done} file(s) done${currentLine}`);
          }
        } else if (sawRunning.current) {
          // ingestion finished (or failed)
          sawRunning.current = false;
          setPhase("idle");
          setProgress(null);
          if (p.error) {
            setError(p.error);
            setStatus(null);
          } else if (p.result) {
            const r = p.result;
            const skipped = Math.max(0, p.total_files - p.processed_files);
            const skippedLine = skipped > 0 ? ` · ${skipped} unchanged file(s) skipped` : "";
            setStatus(
              `Ingestion finished: ${r.entities} entities, ${r.relations} relations, ${r.chunks} chunks, ${r.communities} communities.${skippedLine}`
            );
          } else {
            setStatus("Ingestion finished.");
          }
          await refreshStats();
        }
      } catch {
        // transient poll failure: keep the previous state
      }
    };
    const timer = setInterval(poll, 3000);
    return () => clearInterval(timer);
  }, [phase, refreshStats, onStatsChange]);

  const process = async () => {
    if (busy) {
      return;
    }
    setError(null);
    setProgress(null);
    sawRunning.current = false;

    if (files.length > 0) {
      setPhase("uploading");
      setStatus(`Uploading ${files.length} file(s)…`);
      try {
        await uploadFiles(files);
        setFiles([]);
      } catch (err) {
        setError(errorMessage(err));
        setStatus(null);
        setPhase("idle");
        return;
      }
    }

    setPhase("ingesting");
    setStatus("Ingesting… this can take several minutes.");
    try {
      await runIngest();
    } catch (err) {
      setError(errorMessage(err));
      setStatus(null);
      setPhase("idle");
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
        {progress && progress.running && progress.to_process > 0 ? (
          <Typography level="body-xs" color="neutral" sx={{ mt: 0.5 }}>
            {progress.processed_files} of {progress.to_process} files processed
          </Typography>
        ) : null}
        {progress && progress.files && progress.files.length > 0 ? (
          <Typography level="body-xs" color="neutral" sx={{ mt: 0.5 }}>
            Files in data: {progress.files.join(", ")}
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
