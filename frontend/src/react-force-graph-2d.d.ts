import type { FC, MouseEvent, Ref } from "react";

declare module "react-force-graph-2d" {
  export interface NodeObject {
    id?: string;
    [key: string]: unknown;
  }

  export interface LinkObject {
    source: string | NodeObject;
    target: string | NodeObject;
    [key: string]: unknown;
  }

  export interface ForceGraphMethods {
    zoomToFit(transitionMs?: number, padding?: number): void;
    centerAt(x?: number, y?: number, transitionMs?: number): void;
    zoom(zoom?: number, transitionMs?: number): void;
  }

  export interface ForceGraphProps {
    graphData: { nodes: NodeObject[]; links: LinkObject[] };
    width?: number;
    height?: number;
    nodeRelSize?: number;
    enableZoom?: boolean;
    enablePan?: boolean;
    enableNodeDrag?: boolean;
    nodeColor?: (node: NodeObject) => string;
    nodeLabel?: string | ((node: NodeObject) => string);
    linkLabel?: string | ((link: LinkObject) => string);
    linkDirectionalArrowLength?: number | ((link: LinkObject) => number);
    linkDirectionalArrowRelPos?: number | ((link: LinkObject) => number);
    onNodeClick?: (node: NodeObject, event: MouseEvent) => void;
    onEngineStop?: () => void;
    cooldownTicks?: number;
    [key: string]: unknown;
  }

  const ForceGraph2D: FC<ForceGraphProps & { ref?: Ref<ForceGraphMethods> }>;
  export default ForceGraph2D;
}
