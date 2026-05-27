"use client";

import type { CorrelationPoint } from "@/types/api";

interface Props {
  matrix: CorrelationPoint[];
  labels: string[];
}

const LABEL_MAP: Record<string, string> = {
  frequency:         "Frecuencia",
  total_units:       "Unidades",
  unique_products:   "Prod. únicos",
  unique_categories: "Categorías",
  avg_basket_size:   "Canasta prom.",
};

function corrToColor(val: number): { bg: string; text: string } {
  const v = Math.max(-1, Math.min(1, val));
  if (v >= 0) {
    const t = v;
    const r = Math.round(219 + (59  - 219) * t);
    const g = Math.round(234 + (130 - 234) * t);
    const b = Math.round(254 + (246 - 254) * t);
    return { bg: `rgb(${r},${g},${b})`, text: t > 0.6 ? "#1e3a8a" : "#374151" };
  }
  const t = Math.abs(v);
  const r = Math.round(219 + (254 - 219) * (1 - t));
  const g = Math.round(234 + (202 - 234) * t);
  const b = Math.round(254 + (202 - 254) * t);
  return { bg: `rgb(${r},${g},${b})`, text: t > 0.6 ? "#7f1d1d" : "#374151" };
}

export function CorrelationHeatmap({ matrix, labels }: Props) {
  if (!matrix.length || !labels.length) {
    return <p style={{ color: "#9ca3af", fontSize: 13, fontStyle: "italic" }}>Sin datos de correlación.</p>;
  }

  const lookup: Record<string, Record<string, number>> = {};
  for (const pt of matrix) {
    if (!lookup[pt.y]) lookup[pt.y] = {};
    lookup[pt.y][pt.x] = pt.value;
  }

  const short = (l: string) => LABEL_MAP[l] || l;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>

      {/* Tabla */}
      <div style={{ overflowX: "auto" }}>
        <table style={{ borderCollapse: "collapse", fontSize: 12, width: "100%" }}>
          <thead>
            <tr>
              <th style={{ padding: "6px 8px", minWidth: 110 }} />
              {labels.map((col) => (
                <th
                  key={col}
                  style={{
                    padding: "6px 8px", textAlign: "center",
                    fontSize: 11, fontWeight: 600, color: "#6b7280",
                    minWidth: 86,
                  }}
                >
                  {short(col)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {labels.map((row) => (
              <tr key={row}>
                <td style={{
                  padding: "6px 10px 6px 0", textAlign: "right",
                  fontSize: 11, fontWeight: 600, color: "#6b7280",
                  whiteSpace: "nowrap",
                }}>
                  {short(row)}
                </td>
                {labels.map((col) => {
                  const val = lookup[row]?.[col] ?? 0;
                  const { bg, text } = corrToColor(val);
                  return (
                    <td
                      key={col}
                      title={`${short(row)} × ${short(col)}: ${val.toFixed(3)}`}
                      style={{
                        padding: "8px",
                        textAlign: "center",
                        fontWeight: 600,
                        background: bg,
                        color: text,
                        border: "2px solid #ffffff",
                        borderRadius: 2,
                        cursor: "default",
                        transition: "opacity 0.15s",
                      }}
                    >
                      {val.toFixed(2)}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Barra de escala */}
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <span style={{ fontSize: 11, color: "#9ca3af", flexShrink: 0 }}>−1.00</span>
        <div style={{
          height: 8, flex: 1, borderRadius: 4,
          background: "linear-gradient(to right, rgb(254,202,202), rgb(254,226,226), rgb(219,234,254), rgb(59,130,246))",
        }} />
        <span style={{ fontSize: 11, color: "#9ca3af", flexShrink: 0 }}>+1.00</span>
      </div>
      <p style={{ fontSize: 11, color: "#9ca3af", margin: 0 }}>
        Azul: correlación positiva · Rojo: correlación negativa · La diagonal siempre vale 1.00
      </p>
    </div>
  );
}
