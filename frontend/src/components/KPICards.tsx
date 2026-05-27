"use client";

interface Props {
  totalUnits: number;
  totalTransactions: number;
}

interface CardProps {
  label: string;
  value: string;
  sublabel: string;
  accent: string;
}

function KPICard({ label, value, sublabel, accent }: CardProps) {
  return (
    <div style={{
      background: "#ffffff",
      border: "1px solid #e5e7eb",
      borderTop: `3px solid ${accent}`,
      borderRadius: 8,
      padding: "24px 28px",
    }}>
      <p style={{ fontSize: 12, fontWeight: 500, color: "#6b7280", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 12 }}>
        {label}
      </p>
      <p style={{ fontSize: 32, fontWeight: 700, color: "#111827", letterSpacing: "-0.5px", lineHeight: 1 }}>
        {value}
      </p>
      <p style={{ fontSize: 12, color: "#9ca3af", marginTop: 8 }}>
        {sublabel}
      </p>
    </div>
  );
}

export function KPICards({ totalUnits, totalTransactions }: Props) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 16 }}>
      <KPICard
        label="Total unidades vendidas"
        value={totalUnits.toLocaleString("es-CO")}
        sublabel="Suma de ítems en todas las transacciones"
        accent="#2563eb"
      />
      <KPICard
        label="Número de transacciones"
        value={totalTransactions.toLocaleString("es-CO")}
        sublabel="Transacciones únicas registradas"
        accent="#0891b2"
      />
    </div>
  );
}
