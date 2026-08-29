import Card from "@mui/joy/Card";
import CardContent from "@mui/joy/CardContent";
import Chip from "@mui/joy/Chip";
import List from "@mui/joy/List";
import ListItem from "@mui/joy/ListItem";
import ListItemContent from "@mui/joy/ListItemContent";
import ListItemDecorator from "@mui/joy/ListItemDecorator";
import Typography from "@mui/joy/Typography";
import type { GraphEdge, GraphNode } from "../types";

interface NodeInspectorProps {
  node: GraphNode | null;
  edges: GraphEdge[];
}

export default function NodeInspector({ node, edges }: NodeInspectorProps) {
  if (!node) {
    return null;
  }
  const related = edges.filter((edge) => edge.source === node.id || edge.target === node.id);
  return (
    <Card variant="soft" sx={{ mt: 2 }}>
      <CardContent>
        <Typography level="title-md">{node.id}</Typography>
        <Chip size="sm" variant="outlined" sx={{ mt: 1, alignSelf: "flex-start" }}>
          {node.type ?? "unknown"}
        </Chip>
        {node.description ? (
          <Typography level="body-sm" sx={{ mt: 1 }}>
            {String(node.description)}
          </Typography>
        ) : null}
        <Typography level="title-sm" sx={{ mt: 2, mb: 1 }}>
          Relations ({related.length})
        </Typography>
        {related.length === 0 ? (
          <Typography level="body-xs">No relations in the current subgraph.</Typography>
        ) : (
          <List size="sm">
            {related.map((edge, index) => (
              <ListItem key={`${edge.source}-${edge.target}-${index}`}>
                <ListItemDecorator sx={{ color: "primary.plainColor", fontWeight: "bold" }}>
                  →
                </ListItemDecorator>
                <ListItemContent>
                  <Typography level="body-xs">
                    {edge.source} -[{edge.relation ?? ""}]→ {edge.target}
                  </Typography>
                  {edge.description ? (
                    <Typography level="body-xs" color="neutral">
                      {String(edge.description)}
                    </Typography>
                  ) : null}
                </ListItemContent>
              </ListItem>
            ))}
          </List>
        )}
      </CardContent>
    </Card>
  );
}
