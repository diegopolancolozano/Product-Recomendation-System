"use client";

import {
  BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, Cell, TooltipProps,
} from "recharts";

interface DataPoint {
  name: string;
  value: number;
}

interface Props {
  data: DataPoint[];
  color: string;
  valueLabel: string;
  height?: number;
}

function CustomTooltip({ active, payload, label, valueLabel }: TooltipProps<number, string> & { valueLabel: string }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: "#fff", border: "1px solid #e5e7eb",
      borderRadius: 6, padding: "10px 14px",
      boxShadow: "0 4px 12px rgba(0,0,0,0.08)",
      fontSize: 12, maxWidth: 240,
    }}>
      <p style={{ color: "#374151", fontWeight: 500, marginBottom: 4, wordBreak: "break-word" }}>{label}</p>
      <p style={{ color: "#111827", fontWeight: 700 }}>
        {payload[0].value?.toLocaleString("es-CO")}
        <span style={{ color: "#6b7280", fontWeight: 400 }}> {valueLabel}</span>
      </p>
    </div>
  );
}

export function HorizontalBarChart({ data, color, valueLabel, height = 300 }: Props) {
  const sorted = [...data].sort((a, b) => a.value - b.value);

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart
        data={sorted}
        layout="vertical"
        margin={{ top: 4, right: 20, left: 8, bottom: 4 }}
      >
        <XAxis
          type="number"
          tick={{ fontSize: 10, fill: "#9ca3af" }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v: number) => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : String(v)}
        />
        <YAxis
          type="category"
          dataKey="name"
          tick={{ fontSize: 10, fill: "#6b7280" }}
          width={155}
          tickLine={false}
          axisLine={false}
          tickFormatter={(v: string) => v.length > 24 ? v.slice(0, 24) + "…" : v}
        />
        <Tooltip content={<CustomTooltip valueLabel={valueLabel} />} cursor={{ fill: "#f9fafb" }} />
        <Bar dataKey="value" radius={[0, 4, 4, 0]} maxBarSize={22}>
          {sorted.map((_, i) => (
            <Cell key={i} fill={color} fillOpacity={0.55 + (i / sorted.length) * 0.45} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
