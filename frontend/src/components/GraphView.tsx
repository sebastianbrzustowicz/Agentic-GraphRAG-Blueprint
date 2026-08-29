import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { useColorScheme } from "@mui/joy/styles";
import Box from "@mui/joy/Box";
import Typography from "@mui/joy/Typography";
import ForceGraph2D, { type ForceGraphMethods } from "react-force-graph-2d";
import { colorForType } from "../colors";
import type { GraphNode, Subgraph } from "../types";

interface GraphViewProps {
  subgraph: Subgraph;
  selectedNodeId: string | null;
  onNodeClick: (node: GraphNode) => void;
}

function useContainerWidth() {
  const ref = useRef<HTMLDivElement | null>(null);
  const [width, setWidth] = useState(0);
  useLayoutEffect(() => {
    const element = ref.current;
    if (!element) {
      return;
    }
    const measure = () => setWidth(element.clientWidth);
    measure();
    const observer = new ResizeObserver(() => {
      measure();
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, []);
  return { ref, width };
}

export default function GraphView({ subgraph, selectedNodeId, onNodeClick }: GraphViewProps) {
  const { ref, width } = useContainerWidth();
  const graphRef = useRef<ForceGraphMethods | null>(null);
  const fittedRef = useRef(false);
  const { mode, systemMode } = useColorScheme();
  const isDark = mode === "dark" || (mode === "system" && systemMode === "dark");
  const linkColor = isDark ? "#c9d1d9" : "#9e9e9e";
  const height = 560;
  const hasData = subgraph.nodes.length > 0;

  const graphData = useMemo(
    () => ({
      nodes: subgraph.nodes.map((node) => ({ id: node.id, type: node.type ?? "", ...node })),
      links: subgraph.edges.map((edge) => ({
        source: edge.source,
        target: edge.target,
        relation: edge.relation ?? "",
        color: linkColor,
        ...edge,
      })),
    }),
    [subgraph, linkColor]
  );

  useEffect(() => {
    fittedRef.current = false;
  }, [graphData]);

  return (
    <Box
      ref={ref}
      sx={{
        width: "100%",
        height,
        border: "1px solid",
        borderColor: "divider",
        borderRadius: "md",
        overflow: "hidden",
        position: "relative",
      }}
    >
      {!hasData ? (
        <Typography level="body-md" sx={{ p: 3 }}>
          Run a query to visualize the knowledge graph subgraph.
        </Typography>
      ) : width === 0 ? (
        <Box sx={{ width: "100%", height: "100%" }} />
      ) : (
        <ForceGraph2D
          ref={graphRef}
          graphData={graphData}
          width={width}
          height={height}
          nodeRelSize={9}
          enableZoom
          enablePan
          enableNodeDrag
          nodeColor={(node) => (selectedNodeId === node.id ? "#ffeb3b" : colorForType(node.type as string | undefined))}
          nodeLabel={(node) => node.id ?? ""}
          linkColor={(link) => (link.color as string | undefined) ?? linkColor}
          linkDirectionalArrowColor={(link) => (link.color as string | undefined) ?? linkColor}
          linkDirectionalArrowLength={4}
          linkDirectionalArrowRelPos={0.9}
          linkLabel={(link) => (link.relation as string | undefined) ?? ""}
          onNodeClick={(node) => onNodeClick(node as unknown as GraphNode)}
          onEngineStop={() => {
            if (!fittedRef.current && graphRef.current) {
              graphRef.current.zoomToFit(400, 60);
              fittedRef.current = true;
            }
          }}
          cooldownTicks={120}
        />
      )}
    </Box>
  );
}
