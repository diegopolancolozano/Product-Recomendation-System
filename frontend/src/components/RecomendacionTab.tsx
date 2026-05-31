"use client";

import { useState } from "react";
import type { RecomendacionData, RecomendacionItem } from "@/types/api";

// ─── Barra de score ───────────────────────────────────────────────────────────
function ScoreBar({ value, max, color }: { value: number; max: number; color: string }) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0;
  return (
    <div style={{ flex: 1, background: "#f3f4f6", borderRadius: 4, height: 6, overflow: "hidden" }}>
      <div style={{ width: `${pct}%`, background: color, height: "100%", borderRadius: 4, transition: "width .3s" }} />
    </div>
  );
}

// ─── Lista de resultados ──────────────────────────────────────────────────────
function ResultsList({ data, color }: { data: RecomendacionData; color: string }) {
  if (!data.results.length) {
    return (
      <div style={{
        textAlign: "center", padding: "40px 20px",
        color: "#9ca3af", background: "#f9fafb",
        borderRadius: 10, border: "1px solid #e5e7eb",
      }}>
        <p style={{ fontSize: 22 }}>🔍</p>
        <p style={{ fontWeight: 600, marginTop: 8 }}>Sin recomendaciones</p>
        <p style={{ fontSize: 12, marginTop: 4 }}>
          No hay suficientes co-ocurrencias en el historial para este {data.query.type === "product" ? "producto" : "cliente"}.
        </p>
      </div>
    );
  }

  const maxScore = Math.max(...data.results.map(r => r.score));

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {data.results.map((item: RecomendacionItem, i) => (
        <div key={item.product_id} style={{
          background: "#fff", border: "1px solid #e5e7eb",
          borderRadius: 8, padding: "12px 16px",
          display: "flex", alignItems: "center", gap: 16,
        }}>
          {/* Posición */}
          <span style={{
            width: 24, height: 24, borderRadius: "50%",
            background: i < 3 ? color : "#f3f4f6",
            color: i < 3 ? "#fff" : "#9ca3af",
            fontSize: 11, fontWeight: 700,
            display: "flex", alignItems: "center", justifyContent: "center",
            flexShrink: 0,
          }}>
            {i + 1}
          </span>

          {/* Label */}
          <div style={{ flex: 1, minWidth: 0 }}>
            <p style={{ fontWeight: 600, fontSize: 13, color: "#111827", marginBottom: 4, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
              {item.label}
            </p>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <ScoreBar value={item.score} max={maxScore} color={color} />
              <span style={{ fontSize: 11, color: "#6b7280", flexShrink: 0 }}>
                {item.score_label}: {item.score.toFixed(3)}
              </span>
            </div>
          </div>

          {/* Support */}
          <div style={{ textAlign: "right", flexShrink: 0 }}>
            <p style={{ fontSize: 12, color: "#6b7280" }}>Soporte</p>
            <p style={{ fontWeight: 700, color: "#111827" }}>{item.support}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── Componente principal ─────────────────────────────────────────────────────
interface Props {
  apiBase: string;
}

type Mode = "product" | "customer";

export function RecomendacionTab({ apiBase }: Props) {
  const [mode, setMode]       = useState<Mode>("product");
  const [query, setQuery]     = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult]   = useState<RecomendacionData | null>(null);
  const [error, setError]     = useState<string | null>(null);

  const color = mode === "product" ? "#2563eb" : "#7c3aed";

  async function handleSearch() {
    const val = query.trim();
    if (!val) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const param = mode === "product" ? `product_id=${encodeURIComponent(val)}` : `customer_id=${encodeURIComponent(val)}`;
      const res = await fetch(`${apiBase}/api/recomendacion?${param}&top_n=10`);
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `HTTP ${res.status}`);
      }
      setResult(await res.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error desconocido");
    } finally {
      setLoading(false);
    }
  }

  function handleKey(e: React.KeyboardEvent) {
    if (e.key === "Enter") handleSearch();
  }

  const placeholder = mode === "product"
    ? "Ej. 1234  — ID del producto"
    : "Ej. C001  — ID del cliente";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 28 }}>

      {/* Cabecera */}
      <div>
        <h2 style={{ fontSize: 20, fontWeight: 700, color: "#111827", margin: 0 }}>
          Recomendador de Productos
        </h2>
        <p style={{ color: "#6b7280", fontSize: 13, marginTop: 6 }}>
          Basado en co-ocurrencia de productos en transacciones. Busca por producto (qué se
          compra junto) o por cliente (qué debería comprar según su historial).
        </p>
      </div>

      {/* Selector de modo + buscador */}
      <div style={{
        background: "#fff", border: "1px solid #e5e7eb",
        borderRadius: 12, padding: "20px 24px",
      }}>
        {/* Toggle */}
        <div style={{ display: "flex", gap: 8, marginBottom: 18 }}>
          {(["product", "customer"] as Mode[]).map(m => {
            const active = mode === m;
            return (
              <button
                key={m}
                onClick={() => { setMode(m); setResult(null); setError(null); setQuery(""); }}
                style={{
                  padding: "7px 18px", borderRadius: 8,
                  border: `1px solid ${active ? (m === "product" ? "#2563eb" : "#7c3aed") : "#e5e7eb"}`,
                  background: active ? (m === "product" ? "#eff6ff" : "#f5f3ff") : "#fff",
                  color: active ? (m === "product" ? "#2563eb" : "#7c3aed") : "#6b7280",
                  fontWeight: active ? 600 : 400,
                  fontSize: 13, cursor: "pointer", transition: "all .15s",
                }}
              >
                {m === "product" ? "Por Producto" : "Por Cliente"}
              </button>
            );
          })}
        </div>

        {/* Input */}
        <div style={{ display: "flex", gap: 10 }}>
          <input
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={handleKey}
            placeholder={placeholder}
            style={{
              flex: 1, padding: "10px 14px", borderRadius: 8,
              border: "1px solid #d1d5db", fontSize: 13, outline: "none",
              fontFamily: "inherit",
            }}
          />
          <button
            onClick={handleSearch}
            disabled={loading || !query.trim()}
            style={{
              padding: "10px 22px", borderRadius: 8, border: "none",
              background: loading || !query.trim() ? "#e5e7eb" : color,
              color: loading || !query.trim() ? "#9ca3af" : "#fff",
              fontWeight: 600, fontSize: 13, cursor: loading ? "wait" : "pointer",
              transition: "all .15s",
            }}
          >
            {loading ? "Buscando…" : "Buscar"}
          </button>
        </div>

        {/* Descripción del modo */}
        <p style={{ fontSize: 11, color: "#9ca3af", marginTop: 10, marginBottom: 0 }}>
          {mode === "product"
            ? "Ingresa el ID numérico del producto. Se mostrarán los productos con mayor co-ocurrencia en el mismo carrito."
            : "Ingresa el ID del cliente. Se sugerirán productos afines que aún no ha comprado, ponderados por su historial."}
        </p>
      </div>

      {/* Error */}
      {error && (
        <div style={{
          background: "#fff5f5", border: "1px solid #fecaca",
          borderRadius: 8, padding: "12px 16px", color: "#dc2626", fontSize: 13,
        }}>
          {error}
        </div>
      )}

      {/* Resultados */}
      {result && (
        <div>
          <p style={{ fontSize: 13, fontWeight: 600, color: "#374151", marginBottom: 12 }}>
            Recomendaciones para{" "}
            <span style={{ color }}>
              {result.query.type === "product" ? `Product ${result.query.id}` : `Customer ${result.query.id}`}
            </span>
            {" "}— {result.results.length} resultado{result.results.length !== 1 ? "s" : ""}
          </p>
          <ResultsList data={result} color={color} />
        </div>
      )}

      {/* Estado vacío inicial */}
      {!result && !loading && !error && (
        <div style={{
          textAlign: "center", padding: "48px 20px",
          color: "#9ca3af", background: "#f9fafb",
          borderRadius: 10, border: "1px dashed #e5e7eb",
        }}>
          <p style={{ fontSize: 28 }}>🛒</p>
          <p style={{ fontWeight: 600, marginTop: 8, color: "#6b7280" }}>
            Ingresa un ID para ver recomendaciones
          </p>
        </div>
      )}

      {/* Nota metodológica */}
      <div style={{
        background: "#f8fafc", border: "1px solid #e2e8f0",
        borderRadius: 8, padding: "14px 18px",
      }}>
        <p style={{ fontSize: 12, color: "#64748b", margin: 0 }}>
          <strong>Metodología:</strong> Se construye una matriz de co-ocurrencia de pares de productos
          (soporte mínimo = 5). La <em>confianza</em> para el par (A,B) es P(B|A) = ocurrencias(A,B) / ocurrencias(A).
          Para clientes, se suman las confianzas de todos sus productos comprados y se filtran los ya adquiridos.
        </p>
      </div>
    </div>
  );
}
