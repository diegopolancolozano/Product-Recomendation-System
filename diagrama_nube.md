workspace "Análisis Transacciones Supermercado — GCP" "Solución analítica sobre Google Cloud Platform." {

    model {

        analista = person "Analista" "Visualiza dashboards y resultados de ML."
        archivosCSV = softwareSystem "Archivos CSV" "Dataset de transacciones del supermercado." "External"
        githubExterno = softwareSystem "GitHub" "Repositorio remoto. Dispara el CI/CD." "External"

        sistema = softwareSystem "Sistema Analítico de Supermercado (GCP)" "Arquitectura master-worker en GCP. Reprocesa automáticamente al llegar nuevos datos." {

            gcs = container "Cloud Storage — Bucket" "Prefijos: /raw (CSV), /models (artefactos ML), /tmp (staging Spark)." "Google Cloud Storage" "Storage"

            trigger = container "Cloud Functions" "Detecta nuevo archivo en /raw y lanza los jobs ETL → ML → Agregaciones." "Python / Cloud Functions Gen2" "Trigger"

            master = container "Dataproc — Master Node" "Orquesta los tres pipelines Spark: ETL, K-Means + FP-Growth, Agregaciones." "Google Cloud Dataproc / Spark" "Master"

            workers = container "Dataproc — Worker Nodes" "Ejecutan en paralelo ETL, K-Means, FP-Growth y cálculo de métricas." "Google Cloud Dataproc / PySpark" "Worker"

            postgresql = container "Cloud SQL — PostgreSQL" "Dos schemas: analitica (métricas) y ml_resultados (segmentos y reglas)." "PostgreSQL / Cloud SQL" "Database"

            api = container "Cloud Run — FastAPI" "API REST. Endpoints: /resumen, /segmentacion, /recomendacion. Consulta PostgreSQL." "Python / FastAPI / Cloud Run" "API"

            frontend = container "Cloud Run — Next.js" "Dashboard: Resumen Ejecutivo (KPIs, top 10, días pico) y Análisis Avanzado (clusters, recomendaciones)." "Next.js / React / Cloud Run" "Web"

            cicd = container "Cloud Build + Artifact Registry" "Construye y despliega imágenes Docker de API y frontend en Cloud Run." "Cloud Build / Artifact Registry" "DevOps"

        }

        archivosCSV -> gcs "Deposita CSV en /raw" "gsutil"
        gcs -> trigger "Nuevo archivo en /raw" "GCS Trigger"
        trigger -> master "Lanza jobs en orden" "Dataproc Jobs API"
        master -> workers "Distribuye particiones" "Spark / YARN"
        workers -> gcs "Lee /raw; escribe /models" "GCS SDK"
        workers -> postgresql "Escribe en schemas analitica y ml_resultados" "psycopg2"
        api -> postgresql "Consulta métricas y resultados ML" "SQLAlchemy"
        frontend -> api "Solicita datos" "HTTPS / JSON"
        analista -> frontend "Visualiza el dashboard" "HTTPS / Navegador"
        githubExterno -> cicd "Push a main" "Webhook"
        cicd -> api "Despliega imagen" "Cloud Run Deploy API"
        cicd -> frontend "Despliega imagen" "Cloud Run Deploy API"

    }

    views {

        container sistema "Arquitectura-General" {
            include *
            autolayout lr
            title "Arquitectura General — Sistema Analítico de Supermercado (GCP)"
        }

        styles {
            element "Person" {
                shape Person
                background #F1EFE8
                color #2C2C2A
                stroke #B4B2A9
            }
            element "External" {
                background #D3D1C7
                color #2C2C2A
                stroke #888780
            }
            element "Storage" {
                shape Cylinder
                background #E8F4FD
                color #0D47A1
                stroke #1565C0
            }
            element "Trigger" {
                background #EAF3DE
                color #27500A
                stroke #639922
            }
            element "Master" {
                background #FCE4EC
                color #880E4F
                stroke #C2185B
            }
            element "Worker" {
                background #FFF8E1
                color #E65100
                stroke #FF6F00
            }
            element "Database" {
                shape Cylinder
                background #E1F5EE
                color #04342C
                stroke #1D9E75
            }
            element "API" {
                background #E1F5EE
                color #04342C
                stroke #1D9E75
            }
            element "Web" {
                background #FAECE7
                color #4A1B0C
                stroke #D85A30
            }
            element "DevOps" {
                background #F3E5F5
                color #4A148C
                stroke #7B1FA2
            }
            element "Container" {
                background #EBF3FC
                color #0C447C
                stroke #378ADD
            }
            element "SoftwareSystem" {
                background #EBF3FC
                color #0C447C
                stroke #378ADD
            }
            relationship "Relationship" {
                thickness 1
                color #888780
                style dashed
            }
        }

    }

}