"use client";

import { SimpleLineChart } from "./SimpleLineChart";
import { BoxPlot } from "./BoxPlot";
import { CorrelationHeatmap } from "./CorrelationHeatmap";
import type { VisualizacionesData } from "@/types/api";

interface Props {
  data: VisualizacionesData;
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

export function VisualizacionesTab({ data }: Props) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>

      {/* Serie de tiempo */}
      <div style={CARD}>
        <span style={BADGE}>Serie de tiempo</span>
        <p style={CARD_TITLE}>Ventas Diarias — Unidades Totales</p>
        <p style={CARD_SUB}>
          Evolución del volumen de ítems vendidos por día. La línea discontinua indica el promedio del período.
        </p>
        <SimpleLineChart
          data={data.units_per_day.map((d) => ({ date: d.date, units: d.units }))}
          dataKey="units"
          color="#2563eb"
          yLabel="unidades"
          height={320}
        />
      </div>

      {/* Boxplot + Heatmap */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <div style={CARD}>
          <span style={BADGE}>Boxplot</span>
          <p style={CARD_TITLE}>Distribución de Unidades por Cliente</p>
          <p style={CARD_SUB}>
            Método de Tukey (1.5 × IQR). Detecta clientes con comportamiento de compra atípico.
          </p>
          <BoxPlot stats={data.boxplot} />
        </div>

        <div style={CARD}>
          <span style={BADGE}>Heatmap de correlación</span>
          <p style={CARD_TITLE}>Correlación entre Variables del Cliente</p>
          <p style={CARD_SUB}>
            Correlación de Pearson entre frecuencia, volumen, diversidad de productos y canasta promedio.
          </p>
          <CorrelationHeatmap
            matrix={data.correlation_matrix}
            labels={data.correlation_labels}
          />
        </div>
      </div>

      {/* Notas metodológicas */}
      <div style={{
        background: "#f8f9fb",
        border: "1px solid #e5e7eb",
        borderRadius: 8,
        padding: "16px 20px",
      }}>
        <p style={{ fontSize: 12, fontWeight: 600, color: "#374151", marginBottom: 10 }}>
          Notas metodológicas
        </p>
        <ul style={{ fontSize: 12, color: "#6b7280", margin: 0, paddingLeft: 18, lineHeight: 1.8 }}>
          <li>
            <strong>Serie de tiempo:</strong> cada punto representa el total de ítems vendidos en ese día.
          </li>
          <li>
            <strong>Boxplot:</strong> los bigotes abarcan hasta 1.5 × IQR desde Q1 y Q3 respectivamente.
            Los puntos fuera de ese rango se consideran valores atípicos.
          </li>
          <li>
            <strong>Heatmap:</strong> valores cercanos a +1 indican relación lineal positiva fuerte;
            cercanos a −1, relación inversa fuerte. La diagonal siempre es 1.00.
          </li>
        </ul>
      </div>
    </div>
  );
}
