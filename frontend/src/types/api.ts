// ---------------------------------------------------------------------------
// Tipos que coinciden con los endpoints de FastAPI
// ---------------------------------------------------------------------------

export interface TopProduct {
  product_id: number;
  label: string;
  units: number;
}

export interface TopCustomer {
  customer_id: string;
  label: string;
  transactions: number;
}

export interface DayPoint {
  date: string;
  transactions: number;
}

export interface CategoryUnit {
  category_name: string;
  units: number;
}

/** Respuesta de GET /api/resumen */
export interface ResumenData {
  total_units: number;
  total_transactions: number;
  top_products: TopProduct[];
  top_customers: TopCustomer[];
  transactions_per_day: DayPoint[];
  category_units: CategoryUnit[];
}

// ---------------------------------------------------------------------------

export interface BoxplotStats {
  whisker_low: number;
  q1: number;
  median: number;
  q3: number;
  whisker_high: number;
  mean: number;
  std: number;
  total_customers: number;
  outlier_count: number;
  outliers: number[];
}

export interface UnitDay {
  date: string;
  units: number;
}

export interface CorrelationPoint {
  x: string;
  y: string;
  value: number;
}

/** Respuesta de GET /api/visualizaciones */
export interface VisualizacionesData {
  units_per_day: UnitDay[];
  boxplot: BoxplotStats;
  correlation_matrix: CorrelationPoint[];
  correlation_labels: string[];
}

// ---------------------------------------------------------------------------

export interface WeekdayPoint {
  weekday: number;       // 0=Lunes … 6=Domingo
  day_name: string;
  avg_transactions: number;
  avg_units: number;
  total_transactions: number;
}

export interface StorePoint {
  store_id: string;
  transactions: number;
  units: number;
}

export interface FreqBucket {
  bucket: string;   // "1","2",…,"21+"
  customers: number;
}

/** Respuesta de GET /api/patrones */
export interface PatronesData {
  by_weekday: WeekdayPoint[];
  by_store: StorePoint[];
  num_stores: number;
  freq_histogram: FreqBucket[];
}
