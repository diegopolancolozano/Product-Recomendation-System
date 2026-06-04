"use client";

import { useState } from "react";
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  Tooltip, ResponsiveContainer, Legend,
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, TooltipProps,
} from "recharts";
import type {
  AvanzadoData, ClusterSummary, ScatterPoint,
  ProductRecoResponse, CustomerRecoResponse,
} from "@/types/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Props { data: AvanzadoData }

const CLUSTER_COLORS = ["#2563eb", "#dc2626", "#059669", "#d97706"];

const FEATURE_LABELS: Record<string, string> = {
  frequency:          "Frecuencia",
  total_units:        "Vol. total",
  unique_products:    "Prod. unicos",
  unique_categories:  "Categorias",
  avg_basket_size:    "Canasta prom.",
};

const FEATURES = ["frequency", "total_units", "unique_products", "unique_categories", "avg_basket_size"] as const;

const CARD: React.CSSProperties = {
  background: "#ffffff", border: "1px solid #e5e7eb", borderRadius: 8, padding: "20px 24px",
};
const BADGE: React.CSSProperties = {
  display: "inline-block", fontSize: 10, fontWeight: 600, color: "#374151",
  background: "#f3f4f6", border: "1px solid #e5e7eb", borderRadius: 4,
  padding: "2px 8px", letterSpacing: "0.04em", textTransform: "uppercase", marginBottom: 8,
};

function interpretCluster(s: ClusterSummary, all: ClusterSummary[]): string {
  const maxFreq  = Math.max(...all.map(x => x.frequency));
  const maxUnits = Math.max(...all.map(x => x.total_units));
  const maxDiv   = Math.max(...all.map(x => x.unique_categories));
  const hiFreq   = s.frequency        >= maxFreq  * 0.55;
  const hiUnits  = s.total_units      >= maxUnits  * 0.55;
  const hiDiv    = s.unique_categories >= maxDiv   * 0.55;
  if (hiFreq && hiUnits)  return "Compradores frecuentes de alto volumen";
  if (hiFreq && !hiUnits) return "Compradores frecuentes de bajo volumen";
  if (hiDiv)              return "Compradores diversificados";
  if (hiUnits)            return "Compradores ocasionales de alto volumen";
  return "Compradores ocasionales";
}

// ── Radar chart de segmentos ──────────────────────────────────────────────────
function ClusterRadar({ summary }: { summary: ClusterSummary[] }) {
  // Normalizar cada feature a 0-100 según el máximo entre clusters
  const maxOf = (key: typeof FEATURES[number]) =>
    Math.max(...summary.map(s => s[key]), 0.001);

  const radarData = FEATURES.map((f) => {
    const mx = maxOf(f);
    const row: Record<string, string | number> = { feature: FEATURE_LABELS[f] };
    summary.forEach(s => {
      row[`c${s.cluster}`] = Math.round((s[f] / mx) * 100);
    });
    return row;
  });

  return (
    <ResponsiveContainer width="100%" height={420}>
      <RadarChart data={radarData} margin={{ top: 20, right: 50, left: 50, bottom: 20 }}>
        <PolarGrid stroke="#e5e7eb" />
        <PolarAngleAxis
          dataKey="feature"
          tick={{ fontSize: 11, fill: "#374151", fontWeight: 500 }}
        />
        <PolarRadiusAxis
          angle={90}
          domain={[0, 100]}
          tick={{ fontSize: 9, fill: "#9ca3af" }}
          tickFormatter={(v: number) => `${v}%`}
        />
        {summary.map((s) => (
          <Radar
            key={s.cluster}
            name={`Cluster ${s.cluster}`}
            dataKey={`c${s.cluster}`}
            stroke={CLUSTER_COLORS[s.cluster]}
            fill={CLUSTER_COLORS[s.cluster]}
            fillOpacity={0.12}
            strokeWidth={2}
          />
        ))}
        <Legend
          formatter={(value) => (
            <span style={{ fontSize: 11, color: "#374151" }}>{value}</span>
          )}
        />
        <Tooltip
          formatter={(val: number, name: string) => [`${val}%`, name]}
          contentStyle={{ fontSize: 12, borderRadius: 6, border: "1px solid #e5e7eb" }}
        />
      </RadarChart>
    </ResponsiveContainer>
  );
}

// ── Scatter Frecuencia vs Volumen ─────────────────────────────────────────────
function FreqVolScatter({ points, summary }: { points: ScatterPoint[]; summary: ClusterSummary[] }) {
  const MAX = 1500;
  const sampled = points.length <= MAX
    ? points
    : points.filter((_, i) => i % Math.ceil(points.length / MAX) === 0);

  // Recortar outliers extremos al percentil 92 en ambos ejes
  const sortFreq  = [...sampled].map(p => p.frequency).sort((a, b) => a - b);
  const sortUnits = [...sampled].map(p => p.total_units).sort((a, b) => a - b);
  const p92 = (arr: number[]) => arr[Math.floor(arr.length * 0.92)];
  const maxFreq  = p92(sortFreq);
  const maxUnits = p92(sortUnits);
  const clipped  = sampled.filter(p => p.frequency <= maxFreq && p.total_units <= maxUnits);

  const byCluster: Record<number, ScatterPoint[]> = {};
  for (const p of clipped) {
    if (!byCluster[p.cluster]) byCluster[p.cluster] = [];
    byCluster[p.cluster].push(p);
  }

  const ScatterTooltip = ({ active, payload }: TooltipProps<number, string>) => {
    if (!active || !payload?.length) return null;
    const d = payload[0].payload as ScatterPoint;
    return (
      <div style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: 6, padding: "8px 12px", fontSize: 11, boxShadow: "0 4px 12px rgba(0,0,0,0.08)" }}>
        <p style={{ fontWeight: 600, color: "#111827", marginBottom: 4 }}>Cliente {d.customer_id}</p>
        <p style={{ color: "#6b7280" }}>Visitas: <strong>{d.frequency}</strong></p>
        <p style={{ color: "#6b7280" }}>Unidades: <strong>{d.total_units}</strong></p>
        <p style={{ color: "#6b7280" }}>Prod. distintos: <strong>{d.unique_products}</strong></p>
      </div>
    );
  };

  return (
    <div>
      <ResponsiveContainer width="100%" height={380}>
        <ScatterChart margin={{ top: 12, right: 20, left: 0, bottom: 24 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
          <XAxis
            type="number" dataKey="frequency" name="Frecuencia"
            tick={{ fontSize: 10, fill: "#9ca3af" }} axisLine={false} tickLine={false}
            label={{ value: "Frecuencia (visitas)", position: "insideBottom", offset: -8, fontSize: 10, fill: "#9ca3af" }}
          />
          <YAxis
            type="number" dataKey="total_units" name="Unidades"
            tick={{ fontSize: 10, fill: "#9ca3af" }} axisLine={false} tickLine={false} width={38}
            tickFormatter={(v: number) => v >= 1000 ? `${(v/1000).toFixed(0)}k` : String(v)}
          />
          <Tooltip content={<ScatterTooltip />} />
          <Legend
            wrapperStyle={{ fontSize: 11, paddingTop: 8 }}
            formatter={(v) => <span style={{ color: "#374151" }}>{v}</span>}
          />
          {summary.map((s) => (
            <Scatter
              key={s.cluster}
              name={`Cluster ${s.cluster}`}
              data={byCluster[s.cluster] ?? []}
              fill={CLUSTER_COLORS[s.cluster]}
              fillOpacity={0.5}
              r={2}
            />
          ))}
        </ScatterChart>
      </ResponsiveContainer>
      <p style={{ fontSize: 10, color: "#9ca3af", textAlign: "right", marginTop: 4 }}>
        Se excluye el 8% de valores extremos para mejor visualizacion.
        Eje X: visitas al supermercado · Eje Y: unidades compradas en total.
      </p>
    </div>
  );
}

// ── Tabla de resumen de clusters ─────────────────────────────────────────────
function ClusterTable({ summary }: { summary: ClusterSummary[] }) {
  const COL: React.CSSProperties  = { padding: "10px 14px", textAlign: "right", fontSize: 12 };
  const HEAD: React.CSSProperties = { ...COL, fontSize: 10, fontWeight: 600, color: "#6b7280", textTransform: "uppercase", letterSpacing: "0.05em", background: "#f9fafb" };

  return (
    <div style={{ overflowX: "auto", borderRadius: 6, border: "1px solid #e5e7eb" }}>
      <table style={{ borderCollapse: "collapse", width: "100%", fontSize: 12 }}>
        <thead>
          <tr>
            <th style={{ ...HEAD, textAlign: "left" }}>Cluster</th>
            <th style={HEAD}>Clientes</th>
            <th style={HEAD}>Frecuencia prom.</th>
            <th style={HEAD}>Unidades prom.</th>
            <th style={HEAD}>Prod. distintos</th>
            <th style={HEAD}>Categorias</th>
            <th style={HEAD}>Canasta prom.</th>
            <th style={{ ...HEAD, textAlign: "left", minWidth: 200 }}>Perfil</th>
          </tr>
        </thead>
        <tbody>
          {summary.map((s) => (
            <tr key={s.cluster} style={{ borderTop: "1px solid #f3f4f6" }}>
              <td style={{ padding: "10px 14px", display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{
                  width: 10, height: 10, borderRadius: "50%",
                  background: CLUSTER_COLORS[s.cluster],
                  flexShrink: 0, display: "inline-block",
                }} />
                <span style={{ fontWeight: 600 }}>Cluster {s.cluster}</span>
              </td>
              <td style={COL}>{s.size.toLocaleString("es-CO")}</td>
              <td style={COL}>{s.frequency}</td>
              <td style={COL}>{s.total_units}</td>
              <td style={COL}>{s.unique_products}</td>
              <td style={COL}>{s.unique_categories}</td>
              <td style={COL}>{s.avg_basket_size}</td>
              <td style={{ ...COL, textAlign: "left", color: "#374151" }}>
                {interpretCluster(s, summary)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Recomendador por producto ─────────────────────────────────────────────────
function ProductRecommender({ productOptions }: { productOptions: AvanzadoData["product_options"] }) {
  const [selectedId, setSelectedId] = useState<number | "">("");
  const [result, setResult]         = useState<ProductRecoResponse | null>(null);
  const [loading, setLoading]       = useState(false);

  const fetchReco = async (pid: number) => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/recomendar/producto?product_id=${pid}&top_n=10`);
      setResult(await res.json());
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
        <select
          value={selectedId}
          onChange={(e) => {
            const pid = Number(e.target.value);
            setSelectedId(pid);
            if (pid) fetchReco(pid);
          }}
          style={{ flex: 1, padding: "8px 12px", borderRadius: 6, border: "1px solid #d1d5db", fontSize: 12, color: "#111827", background: "#fff" }}
        >
          <option value="">Selecciona un producto...</option>
          {productOptions.map((p) => (
            <option key={p.product_id} value={p.product_id}>{p.label}</option>
          ))}
        </select>
        {loading && <span style={{ fontSize: 12, color: "#9ca3af" }}>Calculando...</span>}
      </div>

      {result && result.recommendations.length > 0 && (
        <div>
          <p style={{ fontSize: 11, color: "#6b7280", marginBottom: 8 }}>
            Productos que se compran junto con <strong>{result.product_label}</strong>:
          </p>
          <table style={{ borderCollapse: "collapse", width: "100%", fontSize: 12 }}>
            <thead>
              <tr style={{ background: "#f9fafb" }}>
                <th style={{ padding: "8px 12px", textAlign: "left", fontSize: 10, fontWeight: 600, color: "#6b7280", textTransform: "uppercase" }}>#</th>
                <th style={{ padding: "8px 12px", textAlign: "left", fontSize: 10, fontWeight: 600, color: "#6b7280", textTransform: "uppercase" }}>Producto recomendado</th>
                <th style={{ padding: "8px 12px", textAlign: "right", fontSize: 10, fontWeight: 600, color: "#6b7280", textTransform: "uppercase" }}>Soporte</th>
                <th style={{ padding: "8px 12px", textAlign: "right", fontSize: 10, fontWeight: 600, color: "#6b7280", textTransform: "uppercase" }}>Confianza</th>
              </tr>
            </thead>
            <tbody>
              {result.recommendations.map((r, i) => (
                <tr key={r.product_id} style={{ borderTop: "1px solid #f3f4f6" }}>
                  <td style={{ padding: "8px 12px", color: "#9ca3af" }}>{i + 1}</td>
                  <td style={{ padding: "8px 12px", color: "#111827" }}>{r.label}</td>
                  <td style={{ padding: "8px 12px", textAlign: "right", color: "#6b7280" }}>{r.support.toLocaleString("es-CO")}</td>
                  <td style={{ padding: "8px 12px", textAlign: "right", fontWeight: 600, color: "#2563eb" }}>{(r.confidence * 100).toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p style={{ fontSize: 11, color: "#9ca3af", marginTop: 8 }}>
            Confianza = % de transacciones con el producto base que tambien incluyen el recomendado.
          </p>
        </div>
      )}

      {result && result.recommendations.length === 0 && (
        <p style={{ fontSize: 12, color: "#9ca3af", fontStyle: "italic" }}>
          No hay recomendaciones para este producto con el nivel de soporte actual.
        </p>
      )}
    </div>
  );
}

// ── Recomendador por cliente ──────────────────────────────────────────────────
function CustomerRecommender() {
  const [customerId, setCustomerId] = useState("");
  const [result, setResult]         = useState<CustomerRecoResponse | null>(null);
  const [loading, setLoading]       = useState(false);
  const [notFound, setNotFound]     = useState(false);

  const fetchReco = async () => {
    if (!customerId.trim()) return;
    setLoading(true);
    setNotFound(false);
    try {
      const res = await fetch(`${API_BASE}/api/recomendar/cliente?customer_id=${encodeURIComponent(customerId.trim())}&top_n=10`);
      const data: CustomerRecoResponse = await res.json();
      setResult(data);
      setNotFound(data.recommendations.length === 0);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div style={{ display: "flex", gap: 8 }}>
        <input
          type="text"
          value={customerId}
          onChange={(e) => setCustomerId(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && fetchReco()}
          placeholder="ID del cliente (ej: 530)"
          style={{ flex: 1, padding: "8px 12px", borderRadius: 6, border: "1px solid #d1d5db", fontSize: 12, color: "#111827", outline: "none" }}
        />
        <button
          onClick={fetchReco}
          disabled={loading || !customerId.trim()}
          style={{
            padding: "8px 18px", borderRadius: 6, border: "none",
            background: loading ? "#e5e7eb" : "#2563eb", color: "#fff",
            fontSize: 12, fontWeight: 600, cursor: loading ? "not-allowed" : "pointer",
          }}
        >
          {loading ? "Calculando..." : "Buscar"}
        </button>
      </div>

      {result && result.recommendations.length > 0 && (
        <div>
          <p style={{ fontSize: 11, color: "#6b7280", marginBottom: 8 }}>
            Recomendaciones para el cliente <strong>{result.customer_id}</strong>:
          </p>
          <table style={{ borderCollapse: "collapse", width: "100%", fontSize: 12 }}>
            <thead>
              <tr style={{ background: "#f9fafb" }}>
                <th style={{ padding: "8px 12px", textAlign: "left", fontSize: 10, fontWeight: 600, color: "#6b7280", textTransform: "uppercase" }}>#</th>
                <th style={{ padding: "8px 12px", textAlign: "left", fontSize: 10, fontWeight: 600, color: "#6b7280", textTransform: "uppercase" }}>Producto recomendado</th>
                <th style={{ padding: "8px 12px", textAlign: "right", fontSize: 10, fontWeight: 600, color: "#6b7280", textTransform: "uppercase" }}>Score</th>
              </tr>
            </thead>
            <tbody>
              {result.recommendations.map((r, i) => (
                <tr key={r.product_id} style={{ borderTop: "1px solid #f3f4f6" }}>
                  <td style={{ padding: "8px 12px", color: "#9ca3af" }}>{i + 1}</td>
                  <td style={{ padding: "8px 12px", color: "#111827" }}>{r.label}</td>
                  <td style={{ padding: "8px 12px", textAlign: "right", fontWeight: 600, color: "#059669" }}>{r.score.toFixed(3)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p style={{ fontSize: 11, color: "#9ca3af", marginTop: 8 }}>
            Score = suma ponderada de confianzas de los pares de co-ocurrencia del cliente.
          </p>
        </div>
      )}

      {notFound && (
        <p style={{ fontSize: 12, color: "#9ca3af", fontStyle: "italic" }}>
          Cliente no encontrado o sin historial suficiente para generar recomendaciones.
        </p>
      )}
    </div>
  );
}

// ── Tab principal ─────────────────────────────────────────────────────────────
export function AvanzadoTab({ data }: Props) {
  const [recoTab, setRecoTab] = useState<"producto" | "cliente">("producto");

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>

      {/* Fila 1: Radar + Scatter lado a lado — proporcion igual */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>

        {/* Radar chart — más grande */}
        <div style={CARD}>
          <span style={BADGE}>Segmentacion K-Means</span>
          <p style={{ fontSize: 13, fontWeight: 600, color: "#111827", marginBottom: 2 }}>
            Perfil de Segmentos — Variables Normalizadas
          </p>
          <p style={{ fontSize: 11, color: "#9ca3af", marginBottom: 12 }}>
            Cada eje representa una variable del cliente normalizada al maximo del grupo.
            Un segmento con poligono mas grande es mas activo en esa dimension.
          </p>
          <ClusterRadar summary={data.cluster_summary} />
        </div>

        {/* Scatter Frecuencia vs Volumen */}
        <div style={CARD}>
          <span style={BADGE}>Distribucion de clientes</span>
          <p style={{ fontSize: 13, fontWeight: 600, color: "#111827", marginBottom: 2 }}>
            Frecuencia vs Volumen Total
          </p>
          <p style={{ fontSize: 11, color: "#9ca3af", marginBottom: 16 }}>
            Cada punto es un cliente coloreado por segmento. Permite ver la separacion real entre grupos.
          </p>
          <FreqVolScatter points={data.scatter} summary={data.cluster_summary} />
        </div>
      </div>

      {/* Fila 2: Tabla ancho completo */}
      <div style={CARD}>
        <span style={BADGE}>Descripcion de segmentos</span>
        <p style={{ fontSize: 13, fontWeight: 600, color: "#111827", marginBottom: 2 }}>
          Caracteristicas Promedio por Segmento
        </p>
        <p style={{ fontSize: 11, color: "#9ca3af", marginBottom: 16 }}>
          Valores promedio de cada variable. El perfil se infiere comparando cada cluster con el resto.
        </p>
        <ClusterTable summary={data.cluster_summary} />
      </div>

      {/* Recomendador */}
      <div style={CARD}>
        <span style={BADGE}>Recomendador</span>
        <p style={{ fontSize: 13, fontWeight: 600, color: "#111827", marginBottom: 2 }}>
          Recomendacion de Productos — Reglas de Asociacion
        </p>
        <p style={{ fontSize: 11, color: "#9ca3af", marginBottom: 16 }}>
          Basado en co-ocurrencia de productos en transacciones (soporte minimo: 30 transacciones).
        </p>

        <div style={{ display: "flex", gap: 0, marginBottom: 20, borderBottom: "1px solid #e5e7eb" }}>
          {(["producto", "cliente"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setRecoTab(t)}
              style={{
                padding: "8px 18px", border: "none", background: "none", cursor: "pointer",
                fontSize: 12, fontWeight: recoTab === t ? 600 : 400,
                color: recoTab === t ? "#2563eb" : "#6b7280",
                borderBottom: recoTab === t ? "2px solid #2563eb" : "2px solid transparent",
                marginBottom: -1, transition: "all 0.15s",
              }}
            >
              {t === "producto" ? "Por producto" : "Por cliente"}
            </button>
          ))}
        </div>

        {recoTab === "producto" && <ProductRecommender productOptions={data.product_options} />}
        {recoTab === "cliente"  && <CustomerRecommender />}
      </div>
    </div>
  );
}
