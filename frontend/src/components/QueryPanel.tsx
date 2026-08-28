import { useState } from "react";
import Alert from "@mui/joy/Alert";
import Box from "@mui/joy/Box";
import Button from "@mui/joy/Button";
import Card from "@mui/joy/Card";
import CardContent from "@mui/joy/CardContent";
import Radio from "@mui/joy/Radio";
import RadioGroup from "@mui/joy/RadioGroup";
import Sheet from "@mui/joy/Sheet";
import Textarea from "@mui/joy/Textarea";
import Typography from "@mui/joy/Typography";
import SendIcon from "@mui/icons-material/Send";
import { runQuery } from "../api";
import type { SearchMode, Subgraph } from "../types";

interface QueryPanelProps {
  onResult: (subgraph: Subgraph) => void;
}

export default function QueryPanel({ onResult }: QueryPanelProps) {
  const [mode, setMode] = useState<SearchMode>("local");
  const [query, setQuery] = useState("");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    if (!query.trim() || loading) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const result = await runQuery(query.trim(), mode);
      setAnswer(result.answer);
      onResult(result.subgraph);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Query failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card variant="outlined">
      <CardContent>
        <Typography level="title-md" sx={{ mb: 2 }}>
          Query
        </Typography>
        <RadioGroup
          orientation="horizontal"
          value={mode}
          onChange={(event) => setMode(event.target.value as SearchMode)}
        >
          <Radio value="local" label="Local Search" />
          <Radio value="global" label="Global Search" />
        </RadioGroup>
        <Textarea
          minRows={3}
          value={query}
          placeholder="Ask a medical question…"
          onChange={(event) => setQuery(event.target.value)}
          sx={{ mt: 1 }}
        />
        <Button onClick={submit} loading={loading} startDecorator={<SendIcon />} sx={{ mt: 1 }}>
          Ask
        </Button>
        {error ? (
          <Alert color="danger" sx={{ mt: 1 }}>
            {error}
          </Alert>
        ) : null}
        {answer ? (
          <Box sx={{ mt: 2 }}>
            <Typography level="title-sm" sx={{ mb: 1 }}>
              Answer
            </Typography>
            <Sheet variant="soft" sx={{ p: 1.5, borderRadius: "sm" }}>
              <Typography level="body-sm" sx={{ whiteSpace: "pre-wrap" }}>
                {answer}
              </Typography>
            </Sheet>
          </Box>
        ) : null}
      </CardContent>
    </Card>
  );
}
