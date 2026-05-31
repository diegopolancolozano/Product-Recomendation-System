"use client";

import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import type { SegmentacionData, ClusterProfile } from "@/types/api";

// ─── Colores y etiquetas por cluster ─────────────────────────────────────────
const COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#8b5cf6"];
const CLUSTER_NAMES = ["Segmento A", "Segmento B", "Segmento C", "Segmento D"];

/** Genera una descripción automática basada en la posición relativa del cluster. */
function describeCluster(profile: ClusterProfile, all: ClusterProfile[]): string {
  const byFreq    = [...all].sort((a, b) => b.frequency    - a.frequency);
  const byBasket  = [...all].sort((a, b) => b.avg_basket_size - a.avg_basket_size);
  const byUniq    = [...all].sort((a, b) => b.unique_products - a.unique_products);

  const freqRank   = byFreq.findIndex(p  => p.cluster === profile.cluster) + 1;
  const basketRank = byBasket.findIndex(p => p.cluster === profile.cluster) + 1;
  const uniqRank   = byUniq.findIndex(p  => p.cluster === profile.cluster) + 1;

  if (freqRank === 1 && basketRank <= 2)   return "Alta frecuencia y alto volumen — clientes premium";
  if (freqRank === 1 && basketRank >= 3)   return "Visitas frecuentes con cesta pequeña";
  if (freqRank >= 3 && basketRank === 1)   return "Compras esporádicas pero de gran volumen";
  if (freqRank <= 2 && uniqRank <= 2)      return "Compradores activos con variedad de productos";
  if (freqRank >= 3 && basketRank >= 3)    return "Baja actividad general — clientes ocasionales";
  return "Perfil mixto — comportamiento moderado";
}

// ─── Tooltip personalizado ────────────────────────────────────────────────────
function ScatterTooltip({ active, payload }: { active?: boolean; payload?: { payload: Record<string, unknown> }[] }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload as {
    customer_id: string;
    frequency: number;
    avg_basket_size: number;
    unique_products: number;
  };
  return (
    <div style={{
      background: "#fff", border: "1px solid #e5e7eb",
      borderRadius: 8, padding: "10px 14px", fontSize: 12, boxShadow: "0 4px 12px rgba(0,0,0,.08)",
    }}>
      <p style={{ fontWeight: 600, marginBottom: 4 }}>{d.customer_id}</p>
      <p style={{ color: "#6b7280" }}>Visitas: <strong>{d.frequency}</strong></p>
      <p style={{ color: "#6b7280" }}>Canasta prom.: <strong>{d.avg_basket_size}</strong></p>
      <p style={{ color: "#6b7280" }}>Productos únicos: <strong>{d.unique_products}</strong></p>
    </div>
  );
}

// ─── Tarjeta de perfil de cluster ─────────────────────────────────────────────
function ProfileCard({ profile, all, index }: { profile: ClusterProfile; all: ClusterProfile[]; index: number }) {
  const color = COLORS[index % COLORS.length];
  const name  = CLUSTER_NAMES[index % CLUSTER_NAMES.length];
  const desc  = describeCluster(profile, all);
  const total = all.reduce((s, p) => s + p.size, 0);
  const pct   = total > 0 ? ((profile.size / total) * 100).toFixed(1) : "0";

  const stat = (label: string, value: string | number) => (
    <div style={{ marginBottom: 6 }}>
      <span style={{ color: "#9ca3af", fontSize: 11, textTransform: "uppercase", letterSpacing: ".5px" }}>
        {label}
      </span>
      <p style={{ fontWeight: 600, fontSize: 15, color: "#111827", margin: "1px 0 0" }}>{value}</p>
    </div>
  );

  return (
    <div style={{
      background: "#fff",
      border: `1px solid ${color}33`,
      borderLeft: `4px solid ${color}`,
      borderRadius: 10,
      padding: "18px 20px",
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
        <div>
          <span style={{
            display: "inline-block", background: `${color}18`, color,
            borderRadius: 6, padding: "2px 10px", fontSize: 12, fontWeight: 700,
          }}>
            {name}
          </span>
          <p style={{ marginTop: 6, fontSize: 12, color: "#6b7280", maxWidth: 240 }}>{desc}</p>
        </div>
        <div style={{ textAlign: "right" }}>
          <p style={{ fontSize: 22, fontWeight: 700, color, lineHeight: 1 }}>{profile.size}</p>
          <p style={{ fontSize: 11, color: "#9ca3af" }}>{pct}% del total</p>
        </div>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
        {stat("Visitas prom.", profile.frequency)}
        {stat("Canasta prom.", profile.avg_basket_size)}
        {stat("Prod. únicos", profile.unique_products)}
      </div>
    </div>
  );
}

// ─── Componente principal ─────────────────────────────────────────────────────
interface Props { data: SegmentacionData }

export function SegmentacionTab({ data }: Props) {
  const { points, profiles, n_clusters } = data;

  // Agrupar puntos por cluster para el ScatterChart
  const series = Array.from({ length: n_clusters }, (_, i) => ({
    name: CLUSTER_NAMES[i],
    color: COLORS[i],
    data: points
      .filter(p => p.cluster === i)
      .map(p => ({
        x: p.pca1,
        y: p.pca2,
        customer_id: p.customer_id,
        frequency: p.frequency,
        avg_basket_size: p.avg_basket_size,
        unique_products: p.unique_products,
      })),
  }));

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 32 }}>

      {/* Cabecera */}
      <div>
        <h2 style={{ fontSize: 20, fontWeight: 700, color: "#111827", margin: 0 }}>
          Segmentación de Clientes — K-Means (k={n_clusters})
        </h2>
        <p style={{ color: "#6b7280", fontSize: 13, marginTop: 6 }}>
          Agrupación basada en frecuencia de compra, volumen total, diversidad de productos y
          tamaño de canasta. Las coordenadas son una proyección PCA (2 componentes) para
          visualización.
        </p>
      </div>

      {/* Scatter PCA */}
      <div style={{
        background: "#fff", border: "1px solid #e5e7eb",
        borderRadius: 12, padding: "24px 16px 12px",
      }}>
        <p style={{ fontSize: 13, fontWeight: 600, color: "#374151", marginBottom: 16, paddingLeft: 8 }}>
          Proyección PCA — {points.length.toLocaleString()} clientes
          {points.length >= 3000 && (
            <span style={{ color: "#9ca3af", fontWeight: 400 }}> (muestra de 3 000)</span>
          )}
        </p>
        <ResponsiveContainer width="100%" height={380}>
          <ScatterChart margin={{ top: 10, right: 20, bottom: 20, left: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
            <XAxis
              type="number" dataKey="x" name="PCA 1"
              domain={["auto", "auto"]}
              tick={{ fontSize: 11, fill: "#9ca3af" }}
              label={{ value: "PCA 1", position: "insideBottom", offset: -10, fontSize: 11, fill: "#9ca3af" }}
            />
            <YAxis
              type="number" dataKey="y" name="PCA 2"
              domain={["auto", "auto"]}
              tick={{ fontSize: 11, fill: "#9ca3af" }}
              label={{ value: "PCA 2", angle: -90, position: "insideLeft", fontSize: 11, fill: "#9ca3af" }}
            />
            <Tooltip content={<ScatterTooltip />} cursor={{ strokeDasharray: "3 3" }} />
            <Legend verticalAlign="top" height={36} />
            {series.map(s => (
              <Scatter
                key={s.name}
                name={s.name}
                data={s.data}
                fill={s.color}
                opacity={0.65}
                r={3}
              />
            ))}
          </ScatterChart>
        </ResponsiveContainer>
      </div>

      {/* Perfiles de cluster */}
      <div>
        <h3 style={{ fontSize: 15, fontWeight: 600, color: "#374151", marginBottom: 14 }}>
          Perfil de cada segmento
        </h3>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 16 }}>
          {profiles.map((p, i) => (
            <ProfileCard key={p.cluster} profile={p} all={profiles} index={i} />
          ))}
        </div>
      </div>

      {/* Nota metodológica */}
      <div style={{
        background: "#f8fafc", border: "1px solid #e2e8f0",
        borderRadius: 8, padding: "14px 18px",
      }}>
        <p style={{ fontSize: 12, color: "#64748b", margin: 0 }}>
          <strong>Metodología:</strong> Se normalizan las 5 variables con StandardScaler antes de K-Means
          (n_init=10, random_state=42). La visualización proyecta a 2D con PCA. Las variables son:
          frecuencia de visita, unidades totales, productos únicos, categorías únicas y tamaño de canasta promedio.
        </p>
      </div>
    </div>
  );
}
