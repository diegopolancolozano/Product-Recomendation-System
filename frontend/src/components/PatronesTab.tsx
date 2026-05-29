"use client";

import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell,
} from "recharts";
import type { PatronesData } from "@/types/api";

interface Props {
  data: PatronesData;
}

// ── Estilos ────────────────────────────────────────────────────────────────────

const CARD: React.CSSProperties = {
  background: "#ffffff",
  border: "1px solid #e5e7eb",
  borderRadius: 8,
  padding: "20px 24px",
};

const CARD_TITLE: React.CSSProperties = {
  fontSize: 13,
  fontWeight: 600,
  color: "#111827",
  marginBottom: 2,
};

const CARD_SUB: React.CSSProperties = {
  fontSize: 11,
  color: "#9ca3af",
  marginBottom: 16,
};

const BADGE: React.CSSProperties = {
  display: "inline-block",
  fontSize: 10,
  fontWeight: 600,
  color: "#374151",
  background: "#f3f4f6",
  border: "1px solid #e5e7eb",
  borderRadius: 4,
  padding: "2px 8px",
  letterSpacing: "0.04em",
  textTransform: "uppercase",
  marginBottom: 8,
};

const AXIS_STYLE = { fontSize: 11, fill: "#9ca3af" };

// ── Colores semáforo weekday (más activo = más oscuro) ─────────────────────────
function weekdayColor(value: number, max: number): string {
  const ratio = max > 0 ? value / max : 0;
  if (ratio >= 0.85) return "#1d4ed8";
  if (ratio >= 0.65) return "#3b82f6";
  if (ratio >= 0.45) return "#93c5fd";
  return "#dbeafe";
}

// Tooltip personalizado
function CustomTooltip({ active, payload, label, unit }: {
  active?: boolean; payload?: { value: number }[]; label?: string; unit?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: "#fff", border: "1px solid #e5e7eb",
      borderRadius: 6, padding: "8px 12px",
      fontSize: 12, boxShadow: "0 2px 8px rgba(0,0,0,.08)",
    }}>
      <p style={{ fontWeight: 600, color: "#111827", marginBottom: 2 }}>{label}</p>
      <p style={{ color: "#6b7280" }}>{payload[0].value.toLocaleString("es-CO")} {unit}</p>
    </div>
  );
}

// ── Componente principal ───────────────────────────────────────────────────────

export function PatronesTab({ data }: Props) {
  const { by_weekday, by_store, num_stores, freq_histogram } = data;

  const maxTxn  = Math.max(...by_weekday.map((d) => d.avg_transactions), 1);
  const maxFreq = Math.max(...freq_histogram.map((d) => d.customers), 1);
  const multiStore = num_stores > 1;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>

      {/* ── Fila superior: Día de semana + Frecuencia de compra ── */}
      <div style={{ display: "grid", gridTemplateColumns: multiStore ? "1fr 1fr" : "1fr", gap: 16 }}>

        {/* Día de la semana */}
        <div style={CARD}>
          <span style={BADGE}>Temporalidad</span>
          <p style={CARD_TITLE}>Actividad por Día de la Semana</p>
          <p style={CARD_SUB}>
            Promedio de transacciones por día — identifica cuándo compran más los clientes.
          </p>
          {by_weekday.length === 0 ? (
            <p style={{ fontSize: 12, color: "#9ca3af" }}>Sin datos de fecha disponibles.</p>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={by_weekday} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
                <XAxis dataKey="day_name" tick={AXIS_STYLE} />
                <YAxis tick={AXIS_STYLE} width={36} />
                <Tooltip
                  content={<CustomTooltip unit="transacciones / día" />}
                />
                <Bar dataKey="avg_transactions" radius={[4, 4, 0, 0]} maxBarSize={48}>
                  {by_weekday.map((entry) => (
                    <Cell
                      key={entry.day_name}
                      fill={weekdayColor(entry.avg_transactions, maxTxn)}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Frecuencia de compra por cliente */}
        <div style={CARD}>
          <span style={BADGE}>Fidelización</span>
          <p style={CARD_TITLE}>¿Cuántas Veces Compra Cada Cliente?</p>
          <p style={CARD_SUB}>
            Número de clientes según su frecuencia de visitas — mide recurrencia y lealtad.
          </p>
          {freq_histogram.length === 0 ? (
            <p style={{ fontSize: 12, color: "#9ca3af" }}>Sin datos de clientes.</p>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={freq_histogram} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
                <XAxis dataKey="bucket" tick={AXIS_STYLE} label={{ value: "compras", position: "insideBottom", offset: -2, style: AXIS_STYLE }} height={38} />
                <YAxis tick={AXIS_STYLE} width={40} />
                <Tooltip content={<CustomTooltip unit="clientes" />} />
                <Bar dataKey="customers" fill="#0891b2" radius={[4, 4, 0, 0]} maxBarSize={52}>
                  {freq_histogram.map((entry) => (
                    <Cell
                      key={entry.bucket}
                      fill={entry.customers === maxFreq ? "#0e7490" : "#0891b2"}
                      fillOpacity={0.75 + (entry.customers / maxFreq) * 0.25}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* ── Actividad por tienda (solo si hay varias) ── */}
      {multiStore && by_store.length > 0 && (
        <div style={CARD}>
          <span style={BADGE}>Distribución espacial</span>
          <p style={CARD_TITLE}>Actividad por Tienda</p>
          <p style={CARD_SUB}>
            Volumen de transacciones por cada punto de venta — {num_stores} tiendas en total.
          </p>
          <ResponsiveContainer width="100%" height={by_store.length > 8 ? 340 : 220}>
            <BarChart
              data={by_store}
              layout="vertical"
              margin={{ top: 4, right: 24, left: 8, bottom: 0 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" horizontal={false} />
              <XAxis type="number" tick={AXIS_STYLE} />
              <YAxis type="category" dataKey="store_id" tick={AXIS_STYLE} width={72} />
              <Tooltip content={<CustomTooltip unit="transacciones" />} />
              <Bar dataKey="transactions" fill="#7c3aed" radius={[0, 4, 4, 0]} maxBarSize={28} fillOpacity={0.82} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* ── Nota metodológica ── */}
      <div style={{
        background: "#f8f9fb", border: "1px solid #e5e7eb",
        borderRadius: 8, padding: "16px 20px",
      }}>
        <p style={{ fontSize: 12, fontWeight: 600, color: "#374151", marginBottom: 10 }}>
          Notas metodológicas
        </p>
        <ul style={{ fontSize: 12, color: "#6b7280", margin: 0, paddingLeft: 18, lineHeight: 1.8 }}>
          <li>
            <strong>Día de semana:</strong> se promedia sobre los días reales del período, no sobre un total
            acumulado — evita que semanas con más lunes distorsionen el resultado.
          </li>
          <li>
            <strong>Frecuencia de compra:</strong> cada cliente se cuenta una sola vez en el bucket
            correspondiente a su número total de transacciones únicas en el dataset.
          </li>
          {multiStore && (
            <li>
              <strong>Tienda:</strong> identificador extraído directamente del campo{" "}
              <code style={{ fontFamily: "monospace", background: "#f3f4f6", padding: "1px 4px", borderRadius: 3 }}>
                store_id
              </code>{" "}
              de los archivos de transacciones.
            </li>
          )}
        </ul>
      </div>
    </div>
  );
}
