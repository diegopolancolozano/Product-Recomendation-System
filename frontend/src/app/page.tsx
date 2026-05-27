"use client";

import { useState, useEffect } from "react";
import { ResumenTab } from "@/components/ResumenTab";
import { VisualizacionesTab } from "@/components/VisualizacionesTab";
import type { ResumenData, VisualizacionesData } from "@/types/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type Tab = "resumen" | "visualizaciones";

const TABS: { id: Tab; label: string }[] = [
  { id: "resumen",         label: "Resumen Ejecutivo" },
  { id: "visualizaciones", label: "Visualizaciones Analíticas" },
];

function Spinner() {
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: 280, gap: 16 }}>
      <div style={{
        width: 36, height: 36,
        border: "3px solid #e5e7eb",
        borderTopColor: "#2563eb",
        borderRadius: "50%",
        animation: "spin 0.75s linear infinite",
      }} />
      <p style={{ color: "#9ca3af", fontSize: 13 }}>Cargando datos...</p>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <div style={{
      background: "#fff5f5", border: "1px solid #fecaca",
      borderRadius: 8, padding: "24px 28px",
    }}>
      <p style={{ fontWeight: 600, color: "#dc2626", marginBottom: 8 }}>
        Error de conexión con el API
      </p>
      <p style={{ color: "#ef4444", fontSize: 13, marginBottom: 16 }}>{message}</p>
      <pre style={{
        background: "#fee2e2", borderRadius: 6, padding: "10px 14px",
        fontSize: 12, color: "#b91c1c", fontFamily: "monospace",
      }}>
        uvicorn api.main:app --reload --port 8000
      </pre>
    </div>
  );
}

export default function Dashboard() {
  const [activeTab, setActiveTab]     = useState<Tab>("resumen");
  const [resumenData, setResumenData] = useState<ResumenData | null>(null);
  const [vizData, setVizData]         = useState<VisualizacionesData | null>(null);
  const [loading, setLoading]         = useState(true);
  const [error, setError]             = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const [rRes, vRes] = await Promise.all([
          fetch(`${API_BASE}/api/resumen`),
          fetch(`${API_BASE}/api/visualizaciones`),
        ]);
        if (!rRes.ok || !vRes.ok) throw new Error(`HTTP ${rRes.status} / ${vRes.status}`);
        const [r, v] = await Promise.all([rRes.json(), vRes.json()]);
        setResumenData(r);
        setVizData(v);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Error desconocido");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const apiStatus = error ? "offline" : loading ? "connecting" : "online";

  return (
    <div style={{ minHeight: "100vh", background: "#f8f9fb" }}>

      {/* ── Header ────────────────────────────────────────────────────── */}
      <header style={{
        background: "#ffffff",
        borderBottom: "1px solid #e5e7eb",
        position: "sticky", top: 0, zIndex: 50,
      }}>
        <div style={{
          maxWidth: 1200, margin: "0 auto",
          padding: "0 32px",
          height: 60,
          display: "flex", alignItems: "center", justifyContent: "space-between",
        }}>
          <div>
            <span style={{ fontWeight: 700, fontSize: 15, color: "#111827", letterSpacing: "-0.2px" }}>
              Supermarket Analytics
            </span>
            <span style={{ color: "#d1d5db", margin: "0 10px" }}></span>
           
          </div>

          {/* Indicador de estado */}
          <div style={{
            display: "flex", alignItems: "center", gap: 6,
            fontSize: 12, fontWeight: 500,
            color: apiStatus === "online" ? "#16a34a" : apiStatus === "connecting" ? "#d97706" : "#dc2626",
          }}>
            <span style={{
              width: 7, height: 7, borderRadius: "50%",
              background: apiStatus === "online" ? "#22c55e" : apiStatus === "connecting" ? "#f59e0b" : "#ef4444",
              display: "inline-block",
              ...(apiStatus === "connecting" ? { animation: "pulse 1.5s ease-in-out infinite" } : {}),
            }} />
            {apiStatus === "online" ? "API conectado" : apiStatus === "connecting" ? "Conectando" : "API desconectado"}
            <style>{`@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.3} }`}</style>
          </div>
        </div>
      </header>

      {/* ── Contenido ─────────────────────────────────────────────────── */}
      <main style={{ maxWidth: 1200, margin: "0 auto", padding: "32px 32px 64px" }}>

        {/* Tabs */}
        <div style={{
          display: "flex", gap: 4,
          borderBottom: "1px solid #e5e7eb",
          marginBottom: 28,
        }}>
          {TABS.map((tab) => {
            const active = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                style={{
                  padding: "10px 20px",
                  border: "none",
                  background: "none",
                  cursor: "pointer",
                  fontSize: 13,
                  fontWeight: active ? 600 : 400,
                  color: active ? "#2563eb" : "#6b7280",
                  borderBottom: active ? "2px solid #2563eb" : "2px solid transparent",
                  marginBottom: -1,
                  transition: "all 0.15s",
                }}
              >
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* Contenido dinámico */}
        {loading && <Spinner />}
        {!loading && error && <ErrorState message={error} />}
        {!loading && !error && (
          <>
            {activeTab === "resumen"         && resumenData && (
              <ResumenTab
                data={resumenData}
                totalCustomers={vizData?.boxplot.total_customers}
              />
            )}
            {activeTab === "visualizaciones" && vizData     && <VisualizacionesTab data={vizData} />}
          </>
        )}
      </main>

      {/* ── Footer ────────────────────────────────────────────────────── */}
      <footer style={{
        borderTop: "1px solid #e5e7eb",
        padding: "16px 32px",
        display: "flex", justifyContent: "space-between",
        fontSize: 12, color: "#9ca3af",
        maxWidth: 1200, margin: "0 auto",
      }}>
        <span>Diego Polanco · Ricardo Chamorro — 2026</span>
      </footer>
    </div>
  );
}
