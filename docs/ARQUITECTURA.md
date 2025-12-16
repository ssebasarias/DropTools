# Dahell Intelligence - Documentación Técnica (V1.2)

## 1. Visión General
Dahell es una plataforma de inteligencia de mercado para Dropshipping diseñada para identificar productos ganadores ("Minas de Oro") mediante el análisis masivo de catálogos de proveedores.

El núcleo del sistema es un motor de **Clustering Híbrido** que agrupa productos idénticos vendidos por diferentes proveedores para calcular la saturación real del mercado.

---

## 2. Arquitectura del Sistema

### 2.1 Backend (Django + Python)
El backend actúa como el cerebro orquestador, gestionando una serie de demonios (scripts en segundo plano) que procesan los datos de forma continua.

#### Servicios Core (Daemons):
1.  **Scraper (`scraper.py`):**
    *   Extrae productos de catálogos web (Droi, etc.).
    *   Guarda datos crudos en PostgreSQL.
2.  **Loader (`loader.py`):**
    *   Normaliza los datos crudos y descarga imágenes a un bucket S3.
3.  **Vectorizer (`vectorizer.py`) [ACTUALIZADO V3]:**
    *   Utiliza el modelo de IA **CLIP (OpenAI)** para generar embeddings semánticos de las imágenes.
    *   Genera vectores que "entienden" el contenido visual, ignorando ruido como marcos o textos promocionales.
4.  **Clusterizer (`clusterizer.py`) [ACTUALIZADO V3 Híbrido]:**
    *   **Lógica:** Híbrida (Imagen + Texto).
    *   **Proceso:**
        *   Busca candidatos visuales usando `pgvector`.
        *   Compara similitud de títulos (Texto).
        *   **Fórmula:** `Score = (0.6 * Visual) + (0.4 * Texto)`.
        *   **Rescue Logic:** Si la imagen difiere pero el texto es 95% idéntico, fuerza la unión ("Text Rescue").

### 2.2 Base de Datos (PostgreSQL + pgvector)
*   **Tablas Clave:** `products`, `product_embeddings` (vectores CLIP), `unique_product_clusters` (agrupaciones), `product_cluster_membership`.
*   **Extensiones:** `vector` (para búsqueda semántica), `pg_trgm` (para búsqueda de texto difuso).

### 2.3 Frontend (React + Vite)
*   **Gold Mine:** Panel principal de descubrimiento de productos. Clasifica por nivel de competencia (Baja, Media, Alta).
*   **Cluster Lab:** Centro de auditoría en tiempo real. Permite ver los logs de decisión de la IA (`/api/cluster-lab/audit-logs`) y auditar productos huérfanos.

---

## 3. Flujo de Datos

1.  **Ingesta:** Scraper -> DB Raw.
2.  **Procesamiento:** Loader -> DB Clean -> S3.
3.  **Enriquecimiento:** Vectorizer -> Crea Embedding CLIP (Imagen).
4.  **Análisis:** Clusterizer ->
    *   Busca similares.
    *   Evalúa Score Híbrido.
    *   Decide: Unir a Cluster existente o Crear "Singleton".
5.  **Visualización:** Frontend consume APIs (`/api/gold-mine/`, `/api/cluster-lab/`).

---

## 4. Guía de Uso Rápido

### Comandos de Gestión
*   **Iniciar todo:** `docker-compose up -d`
*   **Reiniciar Clusterizer (tras cambios):** `docker restart dahell-clusterizer-1`
*   **Ver Logs en Vivo:** `docker logs -f dahell-clusterizer-1`

### Mantenimiento
*   Los logs de auditoría se guardan en `logs/cluster_audit.jsonl`.
*   La base de datos se respalda en el volumen `dahell_postgres_data`.

---

## 5. Glosario de Métricas
*   **Competidores:** Número de proveedores únicos vendiendo el mismo producto (mismo Cluster).
*   **Saturation Score:**
    *   🟢 **BAJA:** 1-2 Competidores (Oportunidad).
    *   🟡 **MEDIA:** 3-5 Competidores (Validado).
    *   🔴 **ALTA:** 6+ Competidores (Saturado).
