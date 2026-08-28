import { useState } from "react";
import Box from "@mui/joy/Box";
import Card from "@mui/joy/Card";
import CardContent from "@mui/joy/CardContent";
import Chip from "@mui/joy/Chip";
import Grid from "@mui/joy/Grid";
import Sheet from "@mui/joy/Sheet";
import Stack from "@mui/joy/Stack";
import Typography from "@mui/joy/Typography";
import GraphView from "./components/GraphView";
import IngestionPanel from "./components/IngestionPanel";
import NodeInspector from "./components/NodeInspector";
import QueryPanel from "./components/QueryPanel";
import ThemeToggle from "./components/ThemeToggle";
import type { GraphNode, GraphStats, Subgraph } from "./types";

export default function App() {
  const [subgraph, setSubgraph] = useState<Subgraph>({ nodes: [], edges: [] });
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [stats, setStats] = useState<GraphStats | null>(null);

  const handleResult = (result: Subgraph) => {
    setSubgraph(result);
    setSelectedNode(null);
  };

  return (
    <Box sx={{ p: 2, maxWidth: 1600, mx: "auto" }}>
      <Sheet variant="soft" sx={{ p: 2, borderRadius: "lg", mb: 2 }}>
        <Stack direction="row" justifyContent="space-between" alignItems="center" spacing={2}>
          <Box>
            <Typography level="h3">Agentic GraphRAG</Typography>
            <Typography level="body-sm">
              Local & Global search over the medical knowledge graph · FastAPI + NetworkX + ChromaDB
            </Typography>
          </Box>
          <ThemeToggle />
        </Stack>
      </Sheet>
      <Grid container spacing={2}>
        <Grid xs={12} lg={4}>
          <Stack spacing={2}>
            <QueryPanel onResult={handleResult} />
            <IngestionPanel onStatsChange={setStats} />
          </Stack>
        </Grid>
        <Grid xs={12} lg={8}>
          <Card variant="outlined">
            <CardContent>
              <Stack direction="row" spacing={2} sx={{ mb: 1, alignItems: "center" }}>
                <Typography level="title-md">Graph Explorer</Typography>
                {stats ? (
                  <Chip size="sm" variant="soft">
                    {stats.nodes} nodes · {stats.edges} edges
                  </Chip>
                ) : null}
              </Stack>
              <GraphView
                subgraph={subgraph}
                selectedNodeId={selectedNode ? selectedNode.id : null}
                onNodeClick={setSelectedNode}
              />
              <NodeInspector node={selectedNode} edges={subgraph.edges} />
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
