// Tipos que coinciden con los endpoints de FastAPI

// ── /api/resumen ─────────────────────────────────────────────────────────────

export interface TopProduct   { product_id: number; label: string; units: number }
export interface TopCustomer  { customer_id: string; label: string; transactions: number }
export interface DayPoint     { date: string; transactions: number }
export interface CategoryUnit { category_name: string; units: number }

export interface ResumenData {
  total_units: number;
  total_transactions: number;
  top_products: TopProduct[];
  top_customers: TopCustomer[];
  transactions_per_day: DayPoint[];
  category_units: CategoryUnit[];
}

// ── /api/visualizaciones ─────────────────────────────────────────────────────

export interface BoxplotStats {
  whisker_low: number; q1: number; median: number; q3: number; whisker_high: number;
  mean: number; std: number; total_customers: number; outlier_count: number; outliers: number[];
}
export interface UnitDay         { date: string; units: number }
export interface CorrelationPoint { x: string; y: string; value: number }

export interface VisualizacionesData {
  units_per_day: UnitDay[];
  boxplot: BoxplotStats;
  correlation_matrix: CorrelationPoint[];
  correlation_labels: string[];
}

// ── /api/patrones ─────────────────────────────────────────────────────────────

export interface WeekdayPoint {
  weekday: number; day_name: string;
  avg_transactions: number; avg_units: number; total_transactions: number;
}
export interface StorePoint  { store_id: string; transactions: number; units: number }
export interface FreqBucket  { bucket: string; customers: number }

export interface PatronesData {
  by_weekday: WeekdayPoint[];
  by_store: StorePoint[];
  num_stores: number;
  freq_histogram: FreqBucket[];
}

// ── /api/avanzado ─────────────────────────────────────────────────────────────

export interface ScatterPoint {
  customer_id: string; pca1: number; pca2: number; cluster: number;
  frequency: number; total_units: number; unique_products: number; avg_basket_size: number;
}
export interface ClusterSummary {
  cluster: number; frequency: number; total_units: number;
  unique_products: number; unique_categories: number; avg_basket_size: number; size: number;
}
export interface ProductOption { product_id: number; label: string }

export interface AvanzadoData {
  scatter: ScatterPoint[];
  cluster_summary: ClusterSummary[];
  k: number;
  product_options: ProductOption[];
  customer_ids: string[];
}

// ── /api/recomendar/* ─────────────────────────────────────────────────────────

export interface ProductRec {
  product_id: number; label: string; support: number; confidence: number;
}
export interface CustomerRec {
  product_id: number; label: string; support: number; score: number;
}
export interface ProductRecoResponse {
  product_id: number; product_label: string; recommendations: ProductRec[];
}
export interface CustomerRecoResponse {
  customer_id: string; recommendations: CustomerRec[];
}
