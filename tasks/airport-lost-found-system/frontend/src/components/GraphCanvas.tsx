import { useMemo } from "react";
import type { GraphContext, GraphEdge, GraphNode } from "../types";

const NODE_COLOR: Record<string, string> = {
  lost_report: "#0ea5e9",
  found_item: "#10b981",
  match_candidate: "#6366f1",
  claim_verification: "#f59e0b",
  custody_event: "#14b8a6",
  qr_label: "#8b5cf6",
  audit_log: "#64748b",
  passenger: "#0f172a",
  staff: "#0f172a",
  category: "#94a3b8",
  airport_location: "#0d9488",
  flight: "#0284c7",
  storage_location: "#0f766e",
};

function radialLayout(nodes: GraphNode[], width: number, height: number) {
  const positions: Record<string, { x: number; y: number }> = {};
  const cx = width / 2;
  const cy = height / 2;
  // Group by type so each type gets its own ring.
  const byType = new Map<string, GraphNode[]>();
  nodes.forEach((node) => {
    const list = byType.get(node.type) ?? [];
    list.push(node);
    byType.set(node.type, list);
  });
  let ring = 0;
  const rings = byType.size;
  byType.forEach((bucket) => {
    const radius = 60 + ring * Math.min(width, height) * 0.35 / Math.max(rings, 1);
    const step = (Math.PI * 2) / Math.max(bucket.length, 1);
    bucket.forEach((node, idx) => {
      const angle = idx * step;
      positions[node.id] = {
        x: cx + Math.cos(angle) * radius,
        y: cy + Math.sin(angle) * radius,
      };
    });
    ring += 1;
  });
  return positions;
}

type Props = {
  graph: GraphContext;
  width?: number;
  height?: number;
};

export function GraphCanvas({ graph, width = 720, height = 420 }: Props) {
  const positions = useMemo(() => radialLayout(graph.nodes, width, height), [graph.nodes, width, height]);
  const riskNodeIds = useMemo(() => {
    const set = new Set<string>();
    (graph.risk_signals || []).forEach((signal) => {
      // Best-effort: highlight any node whose label appears in a risk signal.
      graph.nodes.forEach((node) => {
        if (signal.toLowerCase().includes(String(node.label).toLowerCase()) && node.label) {
          set.add(node.id);
        }
      });
    });
    return set;
  }, [graph]);

  return (
    <figure className="overflow-hidden rounded-lg border border-slate-200 bg-white p-2 shadow-sm">
      <svg viewBox={`0 0 ${width} ${height}`} className="h-auto w-full" role="img" aria-label="Graph RAG context">
        {graph.edges.map((edge: GraphEdge, idx) => {
          const from = positions[edge.source];
          const to = positions[edge.target];
          if (!from || !to) return null;
          return (
            <g key={`${edge.source}-${edge.target}-${idx}`}>
              <line
                x1={from.x}
                y1={from.y}
                x2={to.x}
                y2={to.y}
                stroke="#cbd5e1"
                strokeWidth={1}
              />
            </g>
          );
        })}
        {graph.nodes.map((node) => {
          const pos = positions[node.id];
          if (!pos) return null;
          const fill = riskNodeIds.has(node.id) ? "#ef4444" : NODE_COLOR[node.type] ?? "#475569";
          return (
            <g key={node.id} transform={`translate(${pos.x}, ${pos.y})`}>
              <title>{`${node.type}: ${node.label}`}</title>
              <circle r={8} fill={fill} stroke="#ffffff" strokeWidth={1.5} />
              <text x={10} y={3} fontSize={9} fill="#0f172a">
                {String(node.label).slice(0, 28)}
              </text>
            </g>
          );
        })}
      </svg>
      <figcaption className="mt-2 grid grid-cols-2 gap-1 text-[10px] text-slate-600 sm:grid-cols-4">
        {Object.entries(NODE_COLOR).map(([type, color]) => (
          <span key={type} className="inline-flex items-center gap-1">
            <span className="inline-block h-2 w-2 rounded-full" style={{ background: color }} /> {type}
          </span>
        ))}
        <span className="inline-flex items-center gap-1 text-rose-700">
          <span className="inline-block h-2 w-2 rounded-full bg-rose-500" /> risk
        </span>
      </figcaption>
    </figure>
  );
}
