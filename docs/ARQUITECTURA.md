# 🏗️ ARQUITECTURA DEL SISTEMA - DAHELL INTELLIGENCE

**Versión:** 2.0  
**Última actualización:** 2025-12-14

---

## 📋 ÍNDICE

1. [Visión General](#visión-general)
2. [Arquitectura de Alto Nivel](#arquitectura-de-alto-nivel)
3. [Componentes del Sistema](#componentes-del-sistema)
4. [Flujo de Datos](#flujo-de-datos)
5. [Base de Datos](#base-de-datos)
6. [Tecnologías](#tecnologías)
7. [Decisiones de Diseño](#decisiones-de-diseño)

---

## 🎯 VISIÓN GENERAL

Dahell Intelligence es un sistema de análisis de mercado que utiliza inteligencia artificial para detectar productos idénticos vendidos por diferentes proveedores en plataformas de dropshipping. El sistema identifica oportunidades de negocio con baja competencia mediante clustering vectorial.

### Problema que Resuelve

**Desafío:** Un mismo producto físico es vendido por múltiples proveedores usando diferentes nombres y fotos, haciendo difícil evaluar la competencia real.

**Solución:** Usar IA (embeddings vectoriales) para "ver" y "leer" productos. Si dos productos tienen vectores similares, son el mismo producto.

**Valor:** Identificar productos con alta demanda pero baja competencia (oportunidades de oro).

---

## 🏛️ ARQUITECTURA DE ALTO NIVEL

```
┌─────────────────────────────────────────────────────────────────┐
│                        CAPA DE PRESENTACIÓN                     │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Streamlit  │  │ Django Admin │  │ React (Futuro)│         │
│  │  Dashboard   │  │              │  │   Frontend    │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      CAPA DE APLICACIÓN                         │
├─────────────────────────────────────────────────────────────────┤
│                      Django Backend                             │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Management Commands (ETL)                   │  │
│  ├──────────────┬──────────────┬──────────────┬────────────┤  │
│  │   Scraper    │    Loader    │  Vectorizer  │ Clusterizer│  │
│  └──────────────┴──────────────┴──────────────┴────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  Django ORM (Models)                     │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      CAPA DE DATOS                              │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────┐  │
│  │         PostgreSQL 17 + pgvector Extension              │  │
│  ├──────────────┬──────────────┬──────────────┬────────────┤  │
│  │   Products   │  Embeddings  │   Clusters   │ Suppliers  │  │
│  └──────────────┴──────────────┴──────────────┴────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   CAPA DE INFRAESTRUCTURA                       │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │    Docker    │  │   pgAdmin    │  │  Hugging Face│         │
│  │   Compose    │  │              │  │     Cache    │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🧩 COMPONENTES DEL SISTEMA

### 1. Scraper (Extracción)

**Responsabilidad:** Extraer datos de productos desde Dropi.

**Tecnología:** Selenium + Chrome WebDriver

**Funcionamiento:**
1. Inicia sesión en Dropi con credenciales
2. Navega al catálogo de productos
3. Captura respuestas XHR de la API interna
4. Extrae datos de productos (ID, nombre, precio, imágenes, etc.)
5. Guarda en formato JSONL (UTF-8)

**Salida:** `raw_data/raw_products_YYYYMMDD.jsonl`

**Características:**
- Auto-relogin en caso de sesión expirada
- Modo headless/visible configurable
- Scroll infinito automático
- Manejo robusto de errores

---

### 2. Loader (Carga ETL)

**Responsabilidad:** Cargar datos crudos a la base de datos.

**Tecnología:** SQLAlchemy + psycopg2

**Funcionamiento:**
1. Lee archivos JSONL de `raw_data/`
2. Normaliza datos (proveedores, bodegas, productos)
3. Inserta/actualiza en PostgreSQL con UPSERT
4. Registra histórico de stock
5. Corre en loop infinito (revisa cada 60s)

**Transformaciones:**
- Extracción de datos de proveedor
- Normalización de categorías
- Construcción de URLs de imágenes
- Cálculo de márgenes de ganancia

---

### 3. Vectorizer (IA - Embeddings)

**Responsabilidad:** Generar representaciones vectoriales de productos.

**Tecnología:** PyTorch + CLIP (OpenAI)

**Funcionamiento:**
1. Busca productos con imágenes pero sin vectores
2. Descarga imágenes desde S3
3. Procesa imágenes con modelo CLIP
4. Genera embeddings de 512 dimensiones
5. Normaliza vectores (importante para distancia coseno)
6. Almacena en tabla `product_embeddings`

**Modelo:** `openai/clip-vit-base-patch32`
- Multimodal (imagen + texto)
- Pre-entrenado en 400M de pares imagen-texto
- Embeddings de 512 dimensiones

**Optimizaciones:**
- Detección automática de GPU (CUDA)
- Procesamiento por lotes
- Manejo de errores de descarga

---

### 4. Clusterizer (Agrupación)

**Responsabilidad:** Agrupar productos idénticos.

**Tecnología:** pgvector + Algoritmos personalizados

**Funcionamiento:**

#### Fase 1: Hard Clustering
1. **Por Bodega:** Productos con mismo `warehouse_id` → Mismo producto físico
2. **Por SKU:** Productos con mismo SKU normalizado → Mismo producto

**Confianza:** 100% (match exacto)

#### Fase 2: Soft Clustering (IA)
1. **Búsqueda Vectorial:** Encuentra candidatos con distancia coseno < 0.20
2. **Validación de Texto:** Calcula similitud de títulos (Levenshtein)
3. **Score Combinado:**
   - Si distancia visual < 0.05: 80% visual + 20% texto
   - Si distancia visual > 0.05: 50% visual + 50% texto
4. **Umbral:** Score final > 0.80 → Match

**Penalizaciones:**
- Tipo de producto diferente (SIMPLE vs VARIABLE): -10%
- Categorías incompatibles: Descarte automático

#### Fase 3: Cálculo de Métricas
- Total de competidores (proveedores únicos)
- Precio promedio
- Score de saturación (BAJA/MEDIA/ALTA)

---

## 🔄 FLUJO DE DATOS

### Pipeline Completo

```
1. EXTRACCIÓN
   Dropi → Selenium → JSONL
   
2. TRANSFORMACIÓN
   JSONL → Loader → Normalización
   
3. CARGA
   Datos normalizados → PostgreSQL
   
4. VECTORIZACIÓN
   Imágenes → CLIP → Embeddings (512-dim)
   
5. CLUSTERING
   Embeddings → Similitud → Clusters
   
6. ANÁLISIS
   Clusters → Métricas → Insights
   
7. VISUALIZACIÓN
   Insights → Dashboard → Usuario
```

### Flujo Detallado

```
┌─────────────┐
│   Dropi     │
│  (Fuente)   │
└──────┬──────┘
       │
       ▼ (XHR)
┌─────────────┐
│  Scraper    │
│  (Selenium) │
└──────┬──────┘
       │
       ▼ (JSONL)
┌─────────────┐
│  raw_data/  │
│  *.jsonl    │
└──────┬──────┘
       │
       ▼ (Read)
┌─────────────┐
│   Loader    │
│  (ETL)      │
└──────┬──────┘
       │
       ▼ (SQL INSERT)
┌─────────────────────────────────────┐
│         PostgreSQL                  │
├─────────────┬───────────────────────┤
│  products   │  suppliers            │
│  warehouses │  categories           │
└──────┬──────┴───────────────────────┘
       │
       ▼ (SELECT products without embeddings)
┌─────────────┐
│ Vectorizer  │
│  (CLIP AI)  │
└──────┬──────┘
       │
       ▼ (INSERT embeddings)
┌─────────────────────────────────────┐
│    product_embeddings               │
│    (512-dim vectors)                │
└──────┬──────────────────────────────┘
       │
       ▼ (Vector similarity search)
┌─────────────┐
│ Clusterizer │
│ (Matching)  │
└──────┬──────┘
       │
       ▼ (INSERT clusters)
┌─────────────────────────────────────┐
│  unique_product_clusters            │
│  product_cluster_membership         │
└──────┬──────────────────────────────┘
       │
       ▼ (SELECT insights)
┌─────────────┐
│  Dashboard  │
│ (Streamlit) │
└─────────────┘
```

---

## 🗄️ BASE DE DATOS

### Esquema Relacional

```sql
-- NIVEL 1: Infraestructura
warehouses (warehouse_id PK, city, ...)
suppliers (supplier_id PK, name, store_name, ...)
categories (id PK, name)

-- NIVEL 2: Productos
products (product_id PK, supplier_id FK, sku, title, ...)
product_categories (product_id FK, category_id FK)
product_stock_log (id PK, product_id FK, warehouse_id FK, stock_qty, ...)

-- NIVEL 3: IA
product_embeddings (product_id PK FK, embedding_visual vector(512), embedding_text vector(512))

-- NIVEL 4: Clustering
unique_product_clusters (cluster_id PK, representative_product_id FK, total_competitors, ...)
product_cluster_membership (product_id PK FK, cluster_id FK, match_confidence, match_method)

-- NIVEL 5: Vistas
view_golden_opportunities (cluster_id, sample_name, total_competitors, potential_profit, ...)
```

### Índices Críticos

```sql
-- Índice HNSW para búsqueda vectorial rápida
CREATE INDEX idx_emb_visual ON product_embeddings 
USING hnsw (embedding_visual vector_cosine_ops) 
WITH (m = 16, ef_construction = 64);

-- Índice para histórico de stock
CREATE INDEX idx_stock_log_product ON product_stock_log(product_id, snapshot_at DESC);
```

**Rendimiento:**
- Búsqueda vectorial: ~10ms para 100K productos
- HNSW permite búsqueda aproximada con 95%+ de precisión

---

## 🛠️ TECNOLOGÍAS

### Stack Completo

| Capa | Tecnología | Versión | Propósito |
|------|-----------|---------|-----------|
| **Backend** | Django | 6.0 | Framework web |
| **Base de Datos** | PostgreSQL | 17 | RDBMS |
| **Vectores** | pgvector | Latest | Extensión para embeddings |
| **IA** | PyTorch | 2.9.1 | Deep learning |
| **IA** | Transformers | 4.48.0 | Modelos pre-entrenados |
| **IA** | CLIP | vit-base-patch32 | Embeddings multimodales |
| **Scraping** | Selenium | 4.27.1 | Automatización web |
| **Dashboard** | Streamlit | 1.52.1 | Visualización |
| **Contenedores** | Docker | Latest | Orquestación |
| **ORM** | SQLAlchemy | 2.0.45 | Acceso a datos |

---

## 🎨 DECISIONES DE DISEÑO

### 1. ¿Por qué Django con `managed=False`?

**Decisión:** Usar Django ORM pero con esquema definido en SQL.

**Razón:**
- El esquema requiere extensiones PostgreSQL (pgvector)
- Necesitamos control fino sobre índices HNSW
- Django ORM para queries, SQL para DDL

**Trade-off:**
- ✅ Control total del esquema
- ❌ Migraciones manuales

---

### 2. ¿Por qué CLIP y no otro modelo?

**Decisión:** Usar `openai/clip-vit-base-patch32`

**Razones:**
- Multimodal (imagen + texto en mismo espacio)
- Pre-entrenado en e-commerce
- Embeddings de 512-dim (balance tamaño/precisión)
- Ampliamente usado y probado

**Alternativas consideradas:**
- ResNet: Solo imágenes
- BERT: Solo texto
- ViT: Solo imágenes

---

### 3. ¿Por qué Clustering Híbrido (Hard + Soft)?

**Decisión:** Combinar match exacto con IA.

**Razones:**
- **Hard (Bodega/SKU):** 100% de confianza, no requiere IA
- **Soft (Vectores):** Captura productos sin bodega/SKU

**Ventaja:** Precisión + Cobertura

---

### 4. ¿Por qué UTF-8 Forzado?

**Decisión:** Normalizar todo el sistema a UTF-8.

**Razón:**
- Productos con tildes, ñ, caracteres especiales
- Evitar corrupción de datos
- Compatibilidad internacional

**Implementación:**
- Variables de entorno (`PYTHONIOENCODING=utf-8`)
- Conexiones DB (`client_encoding=UTF8`)
- Archivos JSONL (`encoding='utf-8'`)

---

### 5. ¿Por qué Management Commands en lugar de Scripts?

**Decisión:** Consolidar lógica en Django management commands.

**Razones:**
- ✅ Acceso al ORM de Django
- ✅ Configuración centralizada (settings.py)
- ✅ Estructura profesional
- ✅ Fácil de testear

**Migración:**
- Scripts standalone → `backend/core/management/commands/`

---

## 🔒 SEGURIDAD

### Credenciales
- ✅ Almacenadas en `.env` (no en código)
- ✅ `.env` en `.gitignore`
- ✅ Contraseñas de DB robustas

### Base de Datos
- ✅ Usuario dedicado (`dahell_admin`)
- ✅ Conexión por puerto mapeado (5433)
- ✅ Backups automáticos

### Docker
- ✅ Red interna (`dahell_net`)
- ✅ Volúmenes persistentes
- ✅ Logs centralizados

---

## 📈 ESCALABILIDAD

### Horizontal
- **Scraper:** Múltiples instancias con diferentes cuentas
- **Vectorizer:** Múltiples GPUs en paralelo
- **Clusterizer:** Particionamiento por categoría

### Vertical
- **DB:** Índices HNSW optimizados
- **Vectorizer:** GPU NVIDIA (10x más rápido)
- **Caché:** Redis para queries frecuentes (futuro)

---

## 🔮 EVOLUCIÓN FUTURA

### Fase 1: API REST
- Django REST Framework
- Autenticación JWT
- Rate limiting

### Fase 2: Frontend React
- Dashboard interactivo
- Filtros avanzados
- Exportación de reportes

### Fase 3: ML Avanzado
- Predicción de demanda
- Análisis de tendencias
- Recomendaciones personalizadas

---

**Última actualización:** 2025-12-14  
**Versión:** 2.0
