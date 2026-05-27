"use client";

import {
  LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid,
  ResponsiveContainer, ReferenceLine, TooltipProps,
} from "recharts";

interface DataPoint {
  date: string;
  [key: string]: string | number;
}

interface Props {
  data: DataPoint[];
  dataKey: string;
  color: string;
  yLabel: string;
  height?: number;
}

function subsample<T>(arr: T[], max: number): T[] {
  if (arr.length <= max) return arr;
  const step = Math.ceil(arr.length / max);
  return arr.filter((_, i) => i % step === 0);
}

function CustomTooltip({ active, payload, label, yLabel }: TooltipProps<number, string> & { yLabel: string }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: "#fff", border: "1px solid #e5e7eb",
      borderRadius: 6, padding: "10px 14px",
      boxShadow: "0 4px 12px rgba(0,0,0,0.08)", fontSize: 12,
    }}>
      <p style={{ color: "#6b7280", marginBottom: 4 }}>{label}</p>
      <p style={{ color: "#111827", fontWeight: 700 }}>
        {payload[0].value?.toLocaleString("es-CO")}
        <span style={{ color: "#6b7280", fontWeight: 400 }}> {yLabel}</span>
      </p>
    </div>
  );
}

export function SimpleLineChart({ data, dataKey, color, yLabel, height = 300 }: Props) {
  const displayed = subsample(data, 260);
  const values = displayed.map((d) => Number(d[dataKey])).filter((v) => !isNaN(v));
  const avg = values.length ? values.reduce((a, b) => a + b, 0) / values.length : 0;
  const interval = Math.ceil(displayed.length / 7);

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={displayed} margin={{ top: 8, right: 16, left: 4, bottom: 44 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" vertical={false} />
        <XAxis
          dataKey="date"
          tick={{ fontSize: 9, fill: "#9ca3af" }}
          angle={-40}
          textAnchor="end"
          interval={interval}
          tickLine={false}
          axisLine={{ stroke: "#e5e7eb" }}
        />
        <YAxis
          tick={{ fontSize: 10, fill: "#9ca3af" }}
          tickLine={false}
          axisLine={false}
          tickFormatter={(v: number) => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : String(v)}
          width={36}
        />
        <Tooltip content={<CustomTooltip yLabel={yLabel} />} />
        {avg > 0 && (
          <ReferenceLine
            y={avg}
            stroke="#d1d5db"
            strokeDasharray="4 4"
            label={{
              value: `Prom. ${Math.round(avg).toLocaleString("es-CO")}`,
              position: "insideTopRight",
              fontSize: 9,
              fill: "#9ca3af",
            }}
          />
        )}
        <Line
          type="monotone"
          dataKey={dataKey}
          stroke={color}
          strokeWidth={1.5}
          dot={false}
          activeDot={{ r: 3, fill: color, strokeWidth: 0 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
