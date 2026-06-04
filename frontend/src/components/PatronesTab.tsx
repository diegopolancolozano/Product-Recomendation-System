"use client";

import {
  BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid,
  ResponsiveContainer, Cell, TooltipProps,
} from "recharts";
import type { PatronesData } from "@/types/api";

interface Props { data: PatronesData }

const CARD: React.CSSProperties = {
  background: "#ffffff", border: "1px solid #e5e7eb", borderRadius: 8, padding: "20px 24px",
};
const CARD_TITLE: React.CSSProperties = { fontSize: 13, fontWeight: 600, color: "#111827", marginBottom: 2 };
const CARD_SUB:   React.CSSProperties = { fontSize: 11, color: "#9ca3af", marginBottom: 16 };
const BADGE:      React.CSSProperties = {
  display: "inline-block", fontSize: 10, fontWeight: 600, color: "#374151",
  background: "#f3f4f6", border: "1px solid #e5e7eb", borderRadius: 4,
  padding: "2px 8px", letterSpacing: "0.04em", textTransform: "uppercase", marginBottom: 8,
};

function SimpleTooltip({ active, payload, label, unit }: TooltipProps<number, string> & { unit: string }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: 6, padding: "10px 14px", fontSize: 12, boxShadow: "0 4px 12px rgba(0,0,0,0.08)" }}>
      <p style={{ fontWeight: 600, color: "#111827", marginBottom: 4 }}>{label}</p>
      <p style={{ color: "#6b7280" }}>{payload[0].value?.toLocaleString("es-CO")} {unit}</p>
    </div>
  );
}

export function PatronesTab({ data }: Props) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>

      {/* Por dia de semana + Por tienda */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <div style={CARD}>
          <span style={BADGE}>Dia de la semana</span>
          <p style={CARD_TITLE}>Promedio de Transacciones por Dia</p>
          <p style={CARD_SUB}>Promedio diario de transacciones segun el dia de la semana</p>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={data.by_weekday} margin={{ top: 4, right: 16, left: 4, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" vertical={false} />
              <XAxis dataKey="day_name" tick={{ fontSize: 10, fill: "#6b7280" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 10, fill: "#9ca3af" }} axisLine={false} tickLine={false}
                tickFormatter={(v: number) => v >= 1000 ? `${(v/1000).toFixed(0)}k` : String(v)} width={36} />
              <Tooltip content={<SimpleTooltip unit="transacciones" />} cursor={{ fill: "#f9fafb" }} />
              <Bar dataKey="avg_transactions" radius={[4, 4, 0, 0]} maxBarSize={40}>
                {data.by_weekday.map((_, i) => (
                  <Cell key={i} fill={i >= 5 ? "#2563eb" : "#93c5fd"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <p style={{ fontSize: 11, color: "#9ca3af", marginTop: 8 }}>Azul oscuro = fin de semana</p>
        </div>

        <div style={CARD}>
          <span style={BADGE}>Por tienda</span>
          <p style={CARD_TITLE}>Volumen por Punto de Venta</p>
          <p style={CARD_SUB}>Total de transacciones registradas en cada tienda</p>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={data.by_store} layout="vertical" margin={{ top: 4, right: 24, left: 8, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" horizontal={false} />
              <XAxis type="number" tick={{ fontSize: 10, fill: "#9ca3af" }} axisLine={false} tickLine={false}
                tickFormatter={(v: number) => v >= 1000 ? `${(v/1000).toFixed(0)}k` : String(v)} />
              <YAxis type="category" dataKey="store_id" tick={{ fontSize: 11, fill: "#6b7280" }}
                tickFormatter={(v: string) => `Tienda ${v}`} width={72} axisLine={false} tickLine={false} />
              <Tooltip content={<SimpleTooltip unit="transacciones" />} cursor={{ fill: "#f9fafb" }} />
              <Bar dataKey="transactions" fill="#0891b2" radius={[0, 4, 4, 0]} maxBarSize={28} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Histograma de frecuencia */}
      <div style={CARD}>
        <span style={BADGE}>Frecuencia de compra</span>
        <p style={CARD_TITLE}>Distribucion de Clientes por Numero de Visitas</p>
        <p style={CARD_SUB}>Cuantos clientes compraron exactamente N veces en el periodo analizado</p>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={data.freq_histogram} margin={{ top: 4, right: 16, left: 4, bottom: 4 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" vertical={false} />
            <XAxis dataKey="bucket" tick={{ fontSize: 10, fill: "#6b7280" }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 10, fill: "#9ca3af" }} axisLine={false} tickLine={false}
              tickFormatter={(v: number) => v >= 1000 ? `${(v/1000).toFixed(0)}k` : String(v)} width={44} />
            <Tooltip content={<SimpleTooltip unit="clientes" />} cursor={{ fill: "#f9fafb" }} />
            <Bar dataKey="customers" fill="#7c3aed" radius={[4, 4, 0, 0]} maxBarSize={40} />
          </BarChart>
        </ResponsiveContainer>
        <p style={{ fontSize: 11, color: "#9ca3af", marginTop: 8 }}>
          La mayoria de clientes visita pocas veces. La cola derecha indica compradores muy frecuentes.
        </p>
      </div>
    </div>
  );
}
