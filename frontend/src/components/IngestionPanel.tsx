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
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import { fetchStats, runIngest, uploadFiles } from "../api";
import type { GraphStats } from "../types";

interface IngestionPanelProps {
  onStatsChange: (stats: GraphStats) => void;
}

export default function IngestionPanel({ onStatsChange }: IngestionPanelProps) {
  const [files, setFiles] = useState<File[]>([]);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<GraphStats | null>(null);

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

  const upload = async () => {
    if (!files.length || busy) {
      return;
    }
    setBusy(true);
    setError(null);
    setStatus("Uploading files…");
    try {
      const names = await uploadFiles(files);
      setStatus(`Uploaded: ${names.join(", ")}. Run ingestion to index them.`);
      setFiles([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
      setStatus(null);
    } finally {
      setBusy(false);
    }
  };

  const ingest = async () => {
    if (busy) {
      return;
    }
    setBusy(true);
    setError(null);
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
      setBusy(false);
    }
  };

  return (
    <Card variant="outlined">
      <CardContent>
        <Typography level="title-md" sx={{ mb: 2 }}>
          Ingestion &amp; Data
        </Typography>
        <Button component="label" variant="outlined" color="neutral" startDecorator={<CloudUploadIcon />}>
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
        <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
          <Button onClick={upload} disabled={!files.length || busy} variant="soft">
            Upload
          </Button>
          <Button onClick={ingest} loading={busy} startDecorator={<PlayArrowIcon />}>
            Run /ingest
          </Button>
        </Stack>
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
