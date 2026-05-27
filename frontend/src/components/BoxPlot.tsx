"use client";

import type { BoxplotStats } from "@/types/api";

interface Props {
  stats: BoxplotStats;
}

export function BoxPlot({ stats }: Props) {
  const { whisker_low, q1, median, q3, whisker_high, mean, std, total_customers, outlier_count, outliers } = stats;

  const W = 560;
  const H = 140;
  const PL = 16;
  const PR = 16;
  const PT = 28;
  const PB = 28;
  const plotW = W - PL - PR;
  const midY = PT + (H - PT - PB) / 2;
  const boxH = (H - PT - PB) * 0.42;

  const range = whisker_high - whisker_low || 1;
  const sx = (val: number) => PL + ((val - whisker_low) / range) * plotW;

  const wlX  = sx(whisker_low);
  const q1X  = sx(q1);
  const medX = sx(median);
  const q3X  = sx(q3);
  const whX  = sx(whisker_high);
  const mnX  = sx(mean);

  const visible = outliers.slice(0, 120);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>

      {/* SVG */}
      <div style={{ overflowX: "auto" }}>
        <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ overflow: "visible" }}>

          {/* Bigotes */}
          <line x1={wlX} y1={midY} x2={q1X} y2={midY} stroke="#94a3b8" strokeWidth={1.5} />
          <line x1={q3X} y1={midY} x2={whX} y2={midY} stroke="#94a3b8" strokeWidth={1.5} />
          <line x1={wlX} y1={midY - boxH * 0.5} x2={wlX} y2={midY + boxH * 0.5} stroke="#94a3b8" strokeWidth={1.5} />
          <line x1={whX} y1={midY - boxH * 0.5} x2={whX} y2={midY + boxH * 0.5} stroke="#94a3b8" strokeWidth={1.5} />

          {/* Caja IQR */}
          <rect
            x={q1X} y={midY - boxH}
            width={q3X - q1X} height={boxH * 2}
            fill="#dbeafe" stroke="#3b82f6" strokeWidth={1.5} rx={2}
          />

          {/* Mediana */}
          <line x1={medX} y1={midY - boxH} x2={medX} y2={midY + boxH} stroke="#1d4ed8" strokeWidth={2.5} />

          {/* Media — rombo */}
          <polygon
            points={`${mnX},${midY - 7} ${mnX + 6},${midY} ${mnX},${midY + 7} ${mnX - 6},${midY}`}
            fill="#f59e0b" stroke="#d97706" strokeWidth={1}
          />

          {/* Outliers */}
          {visible.map((val, i) => (
            <circle
              key={i}
              cx={sx(val)}
              cy={midY + ((i * 13 + 5) % 19 - 9) * 1.3}
              r={2.5}
              fill="#ef4444"
              fillOpacity={0.45}
            />
          ))}

          {/* Etiquetas */}
          <text x={wlX}  y={midY + boxH + 14} textAnchor="middle" fontSize={9} fill="#9ca3af">{whisker_low.toFixed(0)}</text>
          <text x={q1X}  y={midY - boxH - 6}  textAnchor="middle" fontSize={9} fill="#6b7280">Q1 · {q1.toFixed(0)}</text>
          <text x={medX} y={midY - boxH - 16} textAnchor="middle" fontSize={9} fill="#1d4ed8" fontWeight="600">Med · {median.toFixed(0)}</text>
          <text x={q3X}  y={midY - boxH - 6}  textAnchor="middle" fontSize={9} fill="#6b7280">Q3 · {q3.toFixed(0)}</text>
          <text x={whX}  y={midY + boxH + 14} textAnchor="middle" fontSize={9} fill="#9ca3af">{whisker_high.toFixed(0)}</text>
          <text x={mnX}  y={midY + boxH + 14} textAnchor="middle" fontSize={9} fill="#d97706">x̄ · {mean.toFixed(1)}</text>
        </svg>
      </div>

      {/* Leyenda */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: "8px 20px", fontSize: 11, color: "#6b7280" }}>
        {[
          { color: "#dbeafe", border: "#3b82f6", label: "Rango intercuartílico (Q1 – Q3)" },
          { color: "#1d4ed8", border: "#1d4ed8", label: "Mediana", line: true },
          { color: "#f59e0b", border: "#d97706", label: "Media (rombo)" },
          { color: "#ef4444", border: "none",    label: "Valores atípicos" },
        ].map(({ color, border, label, line }) => (
          <span key={label} style={{ display: "flex", alignItems: "center", gap: 6 }}>
            {line ? (
              <span style={{ width: 3, height: 14, background: color, display: "inline-block", borderRadius: 1 }} />
            ) : (
              <span style={{ width: 12, height: 12, background: color, border: `1.5px solid ${border}`, display: "inline-block", borderRadius: 2 }} />
            )}
            {label}
          </span>
        ))}
      </div>

      {/* Estadísticas */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10 }}>
        {[
          { label: "Media",           value: mean.toFixed(1) },
          { label: "Desv. estándar",  value: std.toFixed(1) },
          { label: "Total clientes",  value: total_customers.toLocaleString("es-CO") },
          { label: "Valores atípicos", value: outlier_count.toLocaleString("es-CO") },
        ].map(({ label, value }) => (
          <div key={label} style={{
            background: "#f8f9fb", border: "1px solid #e5e7eb",
            borderRadius: 6, padding: "10px 14px", textAlign: "center",
          }}>
            <p style={{ fontSize: 11, color: "#9ca3af", marginBottom: 4 }}>{label}</p>
            <p style={{ fontSize: 18, fontWeight: 700, color: "#111827" }}>{value}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
