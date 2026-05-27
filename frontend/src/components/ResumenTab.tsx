"use client";

import { KPICards } from "./KPICards";
import { HorizontalBarChart } from "./HorizontalBarChart";
import { SimpleLineChart } from "./SimpleLineChart";
import { CategoryPieChart } from "./CategoryPieChart";
import type { ResumenData } from "@/types/api";

interface Props {
  data: ResumenData;
}

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

export function ResumenTab({ data }: Props) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>

      {/* KPIs */}
      <KPICards
        totalUnits={data.total_units}
        totalTransactions={data.total_transactions}
      />

      {/* Aviso */}
      <div style={{
        background: "#eff6ff", border: "1px solid #bfdbfe",
        borderRadius: 6, padding: "10px 16px",
        fontSize: 12, color: "#1d4ed8",
      }}>
        El dataset no incluye precios ni montos. Las métricas se basan en volumen de ítems y frecuencia de compra.
      </div>

      {/* Fila 1: Top productos + Top clientes */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <div style={CARD}>
          <p style={CARD_TITLE}>Top 10 Productos por Volumen</p>
          <p style={CARD_SUB}>Productos con mayor número de unidades vendidas</p>
          <HorizontalBarChart
            data={data.top_products.map((p) => ({ name: p.label, value: p.units }))}
            color="#2563eb"
            valueLabel="unidades"
          />
        </div>

        <div style={CARD}>
          <p style={CARD_TITLE}>Top 10 Clientes por Compras</p>
          <p style={CARD_SUB}>Clientes con mayor número de transacciones únicas</p>
          <HorizontalBarChart
            data={data.top_customers.map((c) => ({ name: c.label, value: c.transactions }))}
            color="#0891b2"
            valueLabel="transacciones"
          />
        </div>
      </div>

      {/* Fila 2: Días pico + Categorías */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <div style={CARD}>
          <p style={CARD_TITLE}>Días Pico de Compra</p>
          <p style={CARD_SUB}>Número de transacciones por día — identifica picos de demanda</p>
          <SimpleLineChart
            data={data.transactions_per_day.map((d) => ({
              date: d.date,
              transactions: d.transactions,
            }))}
            dataKey="transactions"
            color="#7c3aed"
            yLabel="transacciones"
          />
        </div>

        <div style={CARD}>
          <p style={CARD_TITLE}>Categorías más Relevantes</p>
          <p style={CARD_SUB}>Participación sobre el volumen total — excluye productos sin categoría asignada</p>
          <CategoryPieChart
            data={data.category_units
              .filter((c) => c.category_name !== "Sin categoría")
              .map((c) => ({ name: c.category_name, value: c.units }))}
          />
          {data.category_units.some((c) => c.category_name === "Sin categoría") && (() => {
            const sinCat = data.category_units.find((c) => c.category_name === "Sin categoría")!;
            const total  = data.category_units.reduce((s, c) => s + c.units, 0);
            const pct    = ((sinCat.units / total) * 100).toFixed(1);
            return (
              <p style={{ fontSize: 11, color: "#9ca3af", marginTop: 10, borderTop: "1px solid #f3f4f6", paddingTop: 10 }}>
                Nota: {pct}% de las unidades ({sinCat.units.toLocaleString("es-CO")}) corresponden a productos
                sin categoría asignada en el catálogo y se excluyen del gráfico.
              </p>
            );
          })()}
        </div>
      </div>
    </div>
  );
}
