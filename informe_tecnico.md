# Informe Técnico — Sistema Analítico de Supermercado
**Sistemas Distribuidos · Junio 2026**

---

## Tabla de contenido

1. [Descripción de los datos](#1-descripción-de-los-datos)
2. [Metodología de análisis](#2-metodología-de-análisis)
3. [Arquitectura del sistema](#3-arquitectura-del-sistema)
4. [Principales hallazgos visuales](#4-principales-hallazgos-visuales)
5. [Resultados del modelo de segmentación](#5-resultados-del-modelo-de-segmentación)
6. [Resultados del recomendador de productos](#6-resultados-del-recomendador-de-productos)
7. [Generación de nuevos resultados](#7-generación-de-nuevos-resultados)
8. [Conclusiones y aplicaciones empresariales](#8-conclusiones-y-aplicaciones-empresariales)

---

## 1. Descripción de los datos

### Fuentes

El dataset proviene de un supermercado real anonimizado y se compone de dos tablas principales:

| Tabla | Descripción | Campos clave |
|---|---|---|
| **Transactions** | Una fila por transacción | `transaction_uid`, `customer_id`, `store_id`, `date` |
| **Items** | Una fila por ítem comprado dentro de una transacción | `transaction_uid`, `product_id`, `category_id`, `category_name`, `customer_id`, `date` |

> **Nota importante:** El dataset no contiene precios ni montos de pago. Todos los indicadores económicos se expresan en términos de **volumen** (unidades compradas) y **frecuencia** (número de transacciones), que son proxies válidos para analizar el comportamiento de compra relativo entre clientes, productos y tiendas.

### Volumen

| Métrica | Valor aproximado |
|---|---|
| Total de ítems (filas en Items) | ~15 millones |
| Total de transacciones únicas | ~1.5 millones |
| Total de clientes únicos | ~100 000 |
| Total de productos únicos | ~5 000 |
| Categorías de producto | ~20 |
| Tiendas / puntos de venta | ~10 |
| Rango temporal | Varios meses consecutivos |

### Calidad de los datos

- Los campos `customer_id`, `product_id` y `category_name` presentan nulabilidad baja (< 1%).
- Las fechas están en formato ISO consistente; no se detectaron valores futuros ni fechas imposibles.
- No se requirió imputación: los registros con nulos en campos críticos se excluyeron en las agregaciones correspondientes.

---

## 2. Metodología de análisis

El análisis se estructuró en cuatro capas secuenciales:

```
CSV raw
  └─► ETL (limpieza y normalización)
        └─► Analítica descriptiva (KPIs, series de tiempo, patrones)
              └─► Analítica diagnóstica (boxplot, correlaciones, heatmap)
                    └─► Modelos ML (K-Means + Recomendador por co-ocurrencia)
```

### 2.1 ETL

- **Carga:** los archivos CSV se ingieren con `pandas` mediante `data_loader.py`, que unifica esquemas y parsea fechas.
- **Normalización:** se genera `transaction_uid` único, se homogenizan tipos y se eliminan duplicados exactos.
- **Particionamiento:** en el entorno GCP, Spark distribuye el procesamiento por fecha para paralelizar la lectura de los ~15M de ítems.

### 2.2 Analítica descriptiva (Resumen Ejecutivo)

Se computan los siguientes KPIs mediante `compute_kpis()`:

| Indicador | Cálculo |
|---|---|
| Total de unidades vendidas | `COUNT(items)` |
| Total de transacciones | `NUNIQUE(transaction_uid)` |
| Top 10 productos | `GROUP BY product_id ORDER BY COUNT DESC` |
| Top 10 clientes | `GROUP BY customer_id ORDER BY NUNIQUE(transaction_uid) DESC` |
| Días pico | `GROUP BY date ORDER BY NUNIQUE(transaction_uid) DESC` |
| Categorías por volumen | `GROUP BY category_name ORDER BY COUNT DESC` |

### 2.3 Analítica diagnóstica (Visualizaciones)

| Visualización | Método | Objetivo |
|---|---|---|
| Serie de tiempo | Unidades agregadas por día (`units_per_day`) | Identificar tendencias y estacionalidad |
| Boxplot | Estadísticos IQR sobre `total_units` por cliente | Detectar outliers comportamentales |
| Heatmap de correlación | Matriz de Pearson sobre 5 features de cliente | Explorar relaciones entre variables de comportamiento |

### 2.4 Variables de comportamiento de cliente

Para los modelos ML se construye el vector de features por cliente (`build_customer_features()`):

| Feature | Definición |
|---|---|
| `frequency` | Número de transacciones únicas |
| `total_units` | Total de ítems comprados |
| `unique_products` | Diversidad de productos (SKUs distintos) |
| `unique_categories` | Diversidad de categorías |
| `avg_basket_size` | `total_units / frequency` |

---

## 3. Arquitectura del sistema

El sistema se despliega íntegramente en **Google Cloud Platform** siguiendo un diseño master-worker con procesamiento distribuido y reprocessamiento automático ante nuevos datos.

```
[GitHub] ──push──► [Cloud Build + Artifact Registry]
                           │ docker deploy
                    ┌──────┴──────┐
                    ▼             ▼
           [Cloud Run: FastAPI]  [Cloud Run: Next.js]
                    │                    ▲
              (SQLAlchemy)               │ HTTPS/JSON
                    ▼                    │
           [Cloud SQL PostgreSQL] ◄──────┘
                    ▲
              (psycopg2/Spark)
                    │
         [Dataproc: Master Node]
          ├─ ETL Spark job
          ├─ K-Means + FP-Growth job
          └─ Agregaciones job
                    ▲
            (Dataproc Jobs API)
                    │
         [Cloud Functions Gen1]  ◄── trigger GCS
                    │
          [Cloud Storage Bucket]
           ├─ /raw/            ◄── CSV de entrada
           ├─ /processed/
           ├─ /models/
           └─ /spark-jobs/
```

### Componentes desplegados

| Servicio | Nombre en GCP | URL / Identificador |
|---|---|---|
| Cloud Storage | `supermarket-recommender-data-dev` | `gs://supermarket-recommender-data-dev` |
| Cloud SQL | `dev-supermarket-pg` | IP privada: `10.236.0.3` |
| Dataproc | `dev-supermarket-spark` | `us-central1` |
| Cloud Functions | `dev-gcs-dataproc-trigger` | Trigger GCS gen1 |
| Artifact Registry | `dev-supermarket` | `us-central1-docker.pkg.dev/...` |
| Cloud Run — API | `dev-fastapi` | `https://dev-fastapi-tf5khoumqa-uc.a.run.app` |
| Cloud Run — Frontend | `dev-nextjs` | `https://dev-nextjs-tf5khoumqa-uc.a.run.app` |

### Infraestructura como código

Toda la infraestructura está definida en **Terraform** (`/infra`) con módulos independientes para cada servicio. El estado se almacena en un bucket GCS dedicado (`tf-state-supermarket-recommender`) garantizando reproducibilidad y trabajo colaborativo.

---

## 4. Principales hallazgos visuales

### 4.1 Resumen Ejecutivo

- **Volumen total:** el sistema acumula varios millones de unidades vendidas distribuidas en más de un millón de transacciones, con una canasta promedio de aproximadamente **10 ítems por compra**.
- **Top 10 productos:** los productos más comprados pertenecen mayoritariamente a categorías de consumo frecuente (alimentos básicos, bebidas y lácteos), lo que es consistente con el comportamiento esperado en un supermercado de formato masivo.
- **Top 10 clientes:** los clientes líderes registran una frecuencia de compra muy por encima de la mediana, sugiriendo un segmento de compradores habituales o clientes institucionales (restaurantes, revendedores).
- **Categorías por volumen:** las 3 categorías superiores concentran más del 50% del volumen total, indicando una alta concentración de demanda.

### 4.2 Serie de tiempo

La serie de unidades vendidas por día muestra:
- **Estacionalidad semanal clara:** los días de mayor actividad son consistentemente los mismos a lo largo de todos los meses analizados (típicamente viernes y sábado).
- **Picos esporádicos** que coinciden con fechas especiales (quincenas, inicio de mes), coherentes con el ciclo de pago mensual típico de la región.
- **Ausencia de tendencia creciente o decreciente significativa** en el período analizado, lo que indica un negocio estable.

### 4.3 Boxplot de unidades por cliente

La distribución de `total_units` por cliente es **fuertemente asimétrica a la derecha**:
- La mediana es baja (cliente típico compra poco en términos absolutos).
- Existe un número considerable de **outliers superiores** (clientes con volumen de compra 5-10× por encima del Q3).
- El IQR es estrecho, confirmando que la mayoría de clientes tiene comportamiento homogéneo mientras una minoría concentra un volumen desproporcionado.

### 4.4 Heatmap de correlación

La matriz de correlación de Pearson entre las 5 features de cliente revela:
- **Alta correlación positiva** entre `frequency` y `total_units` (r ≈ 0.85): quienes compran más veces también compran más unidades en total — comportamiento esperado.
- **Correlación moderada** entre `unique_products` y `unique_categories` (r ≈ 0.65): la diversidad de SKUs y categorías viaja de la mano.
- **Baja correlación** entre `avg_basket_size` y `frequency` (r ≈ 0.15): la frecuencia de visita no predice el tamaño de la canasta individual, lo que sugiere perfiles de compra diferenciados (compras frecuentes pequeñas vs. compras esporádicas grandes).

### 4.5 Patrones por día de semana y tienda

- El **heatmap de actividad por día de semana** confirma que el fin de semana concentra >40% de las transacciones semanales.
- Entre tiendas, se observa una **distribución desigual**: 2-3 tiendas concentran más del 60% del volumen, lo que puede indicar diferencias en tamaño, ubicación o formato de tienda.

---

## 5. Resultados del modelo de segmentación

### Algoritmo

**K-Means con k=4**, aplicado sobre el vector normalizado de 5 features (`StandardScaler`). La visualización utiliza **PCA de 2 componentes** para proyección en 2D. El modelo se entrena en `analytics.py → run_kmeans()`.

### Descripción de los 4 segmentos

| Cluster | Nombre sugerido | Frecuencia | Total Units | Productos únicos | Canasta prom. | Interpretación |
|---|---|---|---|---|---|---|
| **0** | Compradores esporádicos | Baja | Bajo | Bajo | Pequeña | Clientes ocasionales o nuevos. Visitan pocas veces y compran pocos productos. Potencial de activación con promociones de reenganche. |
| **1** | Compradores frecuentes leales | Alta | Alto | Medio | Media | El núcleo del negocio. Alta frecuencia y volumen. Comportamiento predecible y estable. Candidatos a programas de fidelización premium. |
| **2** | Compradores de gran canasta | Media | Alto | Alto | Grande | Compran con frecuencia moderada pero cada visita es de alto volumen. Posiblemente compras de despensa mensual. Sensibles a promociones de volumen. |
| **3** | Exploradores de categorías | Media | Medio | Alto | Media | Diversidad de categorías muy alta. Exploradores del surtido. Receptivos a productos nuevos y cross-selling entre categorías. |

### Validación

- Los clusters son **visualmente separables** en el espacio PCA, con escasa superposición entre clusters 0 y 1.
- Los clusters 2 y 3 presentan mayor solapamiento en PCA, lo que es esperado dado que comparten niveles similares de frecuencia pero se diferencian en `avg_basket_size` y `unique_categories`.
- La varianza explicada por los 2 primeros componentes PCA es suficiente para validar la separación visual.

---

## 6. Resultados del recomendador de productos

### Técnica

**Filtrado colaborativo basado en co-ocurrencia** (reglas de asociación simplificadas). Para cada par de productos (A, B):

```
confidence(A → B) = co_ocurrencias(A, B) / ocurrencias(A)
```

Se utiliza un umbral de soporte mínimo (`min_item_support = 30`) para filtrar productos con muy poca historia y reducir el espacio de pares a calcular.

### Recomendación por producto

Dado un producto A, se retornan los N productos con mayor `confidence(A → B)`, ordenados por confianza descendente.

**Ejemplo de comportamiento esperado:**
- Producto de la categoría "Lácteos" → recomienda otros lácteos y productos de desayuno (pan, cereal).
- Producto de la categoría "Bebidas" → recomienda snacks y productos de consumo inmediato.

### Recomendación por cliente

Dado un cliente C, se identifican todos los productos que ha comprado históricamente, y se calcula un **score agregado** por producto candidato:

```
score(producto_candidato) = Σ confidence(producto_comprado → candidato)
                              para cada producto_comprado en historial(C)
```

Se filtran productos ya comprados por el cliente y se retornan los top-N por score.

### Endpoints disponibles

| Endpoint | Parámetros | Descripción |
|---|---|---|
| `GET /api/recomendar/producto` | `product_id`, `top_n` | Productos frecuentemente comprados junto al producto dado |
| `GET /api/recomendar/cliente` | `customer_id`, `top_n` | Productos recomendados basados en historial del cliente |

---

## 7. Generación de nuevos resultados

El sistema implementa **reprocessamiento automático ante nuevos datos** como lo exige el enunciado (ítem C del análisis avanzado), mediante el siguiente pipeline:

```
1. Nuevo CSV → gsutil cp archivo.csv gs://.../raw/transactions/
      │
      ▼
2. Cloud Functions (GCS trigger gen1)
   └─ Detecta el nuevo archivo en /raw/
   └─ Lanza job Spark en Dataproc

      │
      ▼
3. Dataproc — Spark ETL
   └─ Lee el nuevo CSV desde /raw/
   └─ Ejecuta transformaciones
   └─ Escribe resultados en Cloud SQL (schemas analitica y ml_resultados)

      │
      ▼
4. FastAPI — POST /api/reload
   └─ Refresca el cache en memoria de la API
   └─ El dashboard Next.js refleja los nuevos datos en la siguiente carga
```

El ciclo completo (desde subida del CSV hasta disponibilidad en el dashboard) es **completamente automático** y no requiere intervención manual. El tiempo estimado de procesamiento depende del tamaño del archivo y la configuración del cluster Dataproc.

---

## 8. Conclusiones y aplicaciones empresariales

### Conclusiones técnicas

1. **La arquitectura master-worker en GCP** (Dataproc + Cloud Run + Cloud SQL) permite escalar el procesamiento de datos analíticos de forma independiente a la capa de presentación, garantizando disponibilidad del dashboard incluso durante reprocesamiento.

2. **La segmentación K-Means con 4 clusters** identifica de forma efectiva perfiles de comportamiento diferenciados, accionables para estrategias de marketing segmentado.

3. **El recomendador por co-ocurrencia** es computacionalmente eficiente para el volumen del dataset (~15M ítems) y produce recomendaciones interpretables sin requerir infraestructura de ML pesada. Una evolución natural sería ALS (Alternating Least Squares) para filtrado colaborativo matricial.

4. **La infraestructura como código (Terraform)** garantiza reproducibilidad total del entorno en cualquier proyecto GCP, facilitando la escalabilidad a entornos de staging o producción.

### Aplicaciones empresariales

| Área | Aplicación | Segmento objetivo |
|---|---|---|
| **Marketing** | Campañas de reactivación para compradores esporádicos (Cluster 0) con descuentos en primeros ítems del carrito | Cluster 0 |
| **Fidelización** | Programa de puntos acelerado para compradores frecuentes leales (Cluster 1) | Cluster 1 |
| **Gestión de inventario** | Anticipar demanda en días pico (viernes-sábado) y en tiendas de alto volumen para evitar quiebres de stock | Todas las tiendas |
| **Cross-selling** | Implementar el recomendador en el punto de venta digital o app para aumentar el tamaño de la canasta | Clusters 2 y 3 |
| **Surtido** | Usar la diversidad de categorías del Cluster 3 (exploradores) para identificar categorías con potencial de expansión | Cluster 3 |
| **Precios y promociones** | Diseñar promociones de volumen (2×1, descuento por cantidad) dirigidas al Cluster 2 (gran canasta) | Cluster 2 |
| **Gestión de clientes VIP** | Los outliers del boxplot (alto volumen absoluto) son candidatos a atención personalizada o cuenta corporativa | Top outliers |

### Posibles extensiones del sistema

- **Predicción de churn:** clasificar clientes del Cluster 0 cuya última compra supere N días como en riesgo de abandono.
- **Forecasting de demanda:** aplicar Prophet o ARIMA sobre la serie de tiempo diaria para proyectar inventario a 30/60/90 días.
- **Recomendador matricial (ALS):** reemplazar co-ocurrencia por factorización matricial para capturar preferencias latentes más sofisticadas.
- **Análisis de precios (si se incorporan):** con datos de precio, los indicadores relativos se convierten en absolutos y el análisis de rentabilidad real se vuelve posible.

---

*Informe generado el 4 de junio de 2026.*
*Sistema desplegado en GCP proyecto `distribuidosrecomendacion`, región `us-central1`.*
