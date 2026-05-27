# Product-Recomendation-System
Proyecto creado para entrega final del curso de procesamiento distribuido en datos

Diego Armando Polanco Lozano

Ricardo Andrés Chamorro Martínez

## Objetivo
Solucion funcional para analisis descriptivo y diagnostico de transacciones de supermercado, con segmentacion y recomendacion de productos.

## Estructura
- app.py: dashboard en Streamlit
- src/data_loader.py: carga y normalizacion de datos
- src/analytics.py: metricas, segmentacion y recomendador
- DataSet/DataSet: carpeta de datos de entrada

## Ejecutar
1. Crear entorno y activar
2. Instalar dependencias
3. Ejecutar la aplicacion

Ejemplo:
```
python -m venv .venv
pip install -r requirements.txt
streamlit run app.py
```

## Datos
- Transactions/*_Tran.csv: date|store_id|customer_id|product_list
- ProductCategory.csv: product_id|category_id
- Categories.csv: category_id|category_name

## Nota
Las metricas se basan en volumen y frecuencia (no hay precios ni montos).