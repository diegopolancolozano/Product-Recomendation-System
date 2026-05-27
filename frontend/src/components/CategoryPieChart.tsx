"use client";

import {
  PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer,
  TooltipProps,
} from "recharts";

interface DataPoint {
  name: string;
  value: number;
}

interface Props {
  data: DataPoint[];
  height?: number;
}

// Paleta corporativa — suficientes colores para 10 categorías
const COLORS = [
  "#2563eb", "#0891b2", "#059669", "#7c3aed", "#db2777",
  "#d97706", "#dc2626", "#475569", "#16a34a", "#9333ea",
];

function CustomTooltip({ active, payload }: TooltipProps<number, string>) {
  if (!active || !payload?.length) return null;
  const item = payload[0];
  return (
    <div style={{
      background: "#fff",
      border: "1px solid #e5e7eb",
      borderRadius: 6,
      padding: "10px 14px",
      boxShadow: "0 4px 12px rgba(0,0,0,0.08)",
      fontSize: 12,
    }}>
      <p style={{ fontWeight: 600, color: "#111827", marginBottom: 4 }}>{item.name}</p>
      <p style={{ color: "#6b7280" }}>
        {(item.value as number).toLocaleString("es-CO")}{" "}
        <span style={{ color: "#9ca3af" }}>unidades</span>
      </p>
      <p style={{ color: item.payload.fill, fontWeight: 600, marginTop: 2 }}>
        {item.payload.pct}% del total
      </p>
    </div>
  );
}

function CustomLegend({ payload }: { payload?: Array<{ color: string; value: string }> }) {
  if (!payload) return null;
  return (
    <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: 5 }}>
      {payload.map((entry, i) => (
        <li key={i} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 11, color: "#374151" }}>
          <span style={{
            width: 10, height: 10, borderRadius: 2,
            background: entry.color, flexShrink: 0,
          }} />
          <span style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", maxWidth: 160 }}>
            {entry.value}
          </span>
        </li>
      ))}
    </ul>
  );
}

export function CategoryPieChart({ data, height = 300 }: Props) {
  const total = data.reduce((s, d) => s + d.value, 0);

  // Añadir porcentaje a cada punto para el tooltip
  const enriched = data.map((d) => ({
    ...d,
    pct: total > 0 ? ((d.value / total) * 100).toFixed(1) : "0",
  }));

  return (
    <ResponsiveContainer width="100%" height={height}>
      <PieChart>
        <Pie
          data={enriched}
          cx="40%"
          cy="50%"
          innerRadius="38%"
          outerRadius="70%"
          dataKey="value"
          strokeWidth={1.5}
          stroke="#ffffff"
        >
          {enriched.map((_, i) => (
            <Cell key={i} fill={COLORS[i % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip content={<CustomTooltip />} />
        <Legend
          layout="vertical"
          align="right"
          verticalAlign="middle"
          content={<CustomLegend />}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}
