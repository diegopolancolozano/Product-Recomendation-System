"use client";

interface Props {
  totalUnits: number;
  totalTransactions: number;
  totalCustomers?: number;   // de boxplot.total_customers (VisualizacionesData)
  activeDays?: number;       // transactions_per_day.length
}

interface CardProps {
  label: string;
  value: string;
  sublabel: string;
  accent: string;
  icon: React.ReactNode;
}

function KPICard({ label, value, sublabel, accent, icon }: CardProps) {
  return (
    <div style={{
      background: "#ffffff",
      border: "1px solid #e5e7eb",
      borderTop: `3px solid ${accent}`,
      borderRadius: 8,
      padding: "20px 24px",
      display: "flex",
      flexDirection: "column",
      gap: 0,
    }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
        <p style={{ fontSize: 11, fontWeight: 600, color: "#6b7280", textTransform: "uppercase", letterSpacing: "0.06em" }}>
          {label}
        </p>
        <span style={{ color: accent, opacity: 0.7 }}>{icon}</span>
      </div>
      <p style={{ fontSize: 30, fontWeight: 700, color: "#111827", letterSpacing: "-0.5px", lineHeight: 1 }}>
        {value}
      </p>
      <p style={{ fontSize: 11, color: "#9ca3af", marginTop: 8 }}>
        {sublabel}
      </p>
    </div>
  );
}

// ── Iconos SVG inline (sin dependencias extra) ────────────────────────────────

const IconBox = (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
  </svg>
);

const IconCart = (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/>
    <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/>
  </svg>
);

const IconBasket = (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/>
    <path d="M16 10a4 4 0 0 1-8 0"/>
  </svg>
);

const IconUser = (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
    <circle cx="9" cy="7" r="4"/>
    <path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>
  </svg>
);

export function KPICards({ totalUnits, totalTransactions, totalCustomers, activeDays }: Props) {
  const avgBasket = totalTransactions > 0
    ? (totalUnits / totalTransactions).toFixed(1)
    : "—";

  const cards: CardProps[] = [
    {
      label:    "Total unidades vendidas",
      value:    totalUnits.toLocaleString("es-CO"),
      sublabel: "Suma de ítems en todas las transacciones",
      accent:   "#2563eb",
      icon:     IconBox,
    },
    {
      label:    "Transacciones únicas",
      value:    totalTransactions.toLocaleString("es-CO"),
      sublabel: "Órdenes de compra registradas",
      accent:   "#0891b2",
      icon:     IconCart,
    },
    {
      label:    "Canasta promedio",
      value:    avgBasket,
      sublabel: "Ítems por transacción — indicador de compra agrupada",
      accent:   "#059669",
      icon:     IconBasket,
    },
    ...(totalCustomers != null ? [{
      label:    "Clientes únicos",
      value:    totalCustomers.toLocaleString("es-CO"),
      sublabel: "Compradores con al menos una transacción",
      accent:   "#7c3aed",
      icon:     IconUser,
    }] : [
      {
        label:    "Días con actividad",
        value:    activeDays != null ? activeDays.toLocaleString("es-CO") : "—",
        sublabel: "Días del período con al menos una transacción",
        accent:   "#7c3aed",
        icon:     IconUser,
      },
    ]),
  ];

  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 14 }}>
      {cards.map((c) => <KPICard key={c.label} {...c} />)}
    </div>
  );
}
