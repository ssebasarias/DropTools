-- =======================================================================================
-- 🏗️ ARQUITECTURA DE BASE DE DATOS: DAHELL INTELLIGENCE
-- =======================================================================================
-- Esta base de datos está optimizada para:
-- 1. Almacenar grandes volúmenes de productos dropshipping.
-- 2. Detectar productos idénticos vendidos por diferentes proveedores mediante IA (Vectores) y Lógica de Bodegas.
-- 3. Calcular métricas de saturación de mercado y oportunidades de arbitraje.
-- =======================================================================================

-- 1️⃣ ACTIVAR EXTENSIONES
-- pgvector: Permite almacenar y comparar embeddings (arrays de números que representan imágenes/texto).
-- unaccent: Para búsquedas de texto insensibles a tildes.
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS unaccent;

-- =======================================================================================
-- 2️⃣ NIVEL DE INFRAESTRUCTURA & TERCEROS
-- =======================================================================================

-- TABLA: warehouses (Bodegas)
-- -----------------------------------------------------------
-- Un "Warehouse" es el lugar físico donde está el stock. 
-- Si dos productos apuntan al mismo warehouse_id, FÍSICAMENTE son el mismo item,
-- sin importar que el vendedor le cambie el nombre o la foto.
CREATE TABLE warehouses (
    warehouse_id BIGINT PRIMARY KEY, -- ID original de Dropi (ej: 4353)
    city VARCHAR(100),               -- Ciudad de la bodega (Bogotá, Medellín...)
    first_seen_at TIMESTAMP DEFAULT NOW(),
    last_seen_at TIMESTAMP DEFAULT NOW()
);

-- TABLA: suppliers (Proveedores)
-- -----------------------------------------------------------
-- Quién vende el producto. Importante para perfilar "Tiburones" vs "Novatos".
CREATE TABLE suppliers (
    supplier_id BIGINT PRIMARY KEY,  -- ID de usuario Dropi (user.id)
    name VARCHAR(255),               -- Nombre del contacto (ej: "Jhon")
    store_name VARCHAR(255),         -- Nombre de la tienda (ej: "Advanced Technology J.A")
    plan_name VARCHAR(100),          -- Nivel: "SUPPLIER PREMIUM", "EXCLUSIVO"
    is_verified BOOLEAN DEFAULT FALSE,
    reputation_score DECIMAL(3,2),   -- A futuro: calcular calidad basada en envíos.
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- =======================================================================================
-- 3️⃣ NIVEL DE PRODUCTO (CORE)
-- =======================================================================================

-- TABLA: categories (Categorías)
-- -----------------------------------------------------------
-- Categorías normalizadas para "silo-ing" (filtrar antes de buscar vectores).
-- Ej: "Salud", "Hogar", "Juguetería".
CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL
);

-- TABLA: products (Productos Maestros)
-- -----------------------------------------------------------
-- La representación de una publicación de venta. 
-- Contiene los datos "crudos" y financieros.
CREATE TABLE products (
    product_id BIGINT PRIMARY KEY,       -- ID original de Dropi (id)
    supplier_id BIGINT REFERENCES suppliers(supplier_id),
    
    -- Datos descriptivos básicos
    sku VARCHAR(100),
    title TEXT NOT NULL,
    description TEXT,
    
    -- Datos Financieros (Clave para detectar arbitraje)
    sale_price NUMERIC(12, 2),      -- Precio al drop (Costo para ti)
    suggested_price NUMERIC(12, 2), -- Precio sugerido de venta (Pellizco al cliente)
    profit_margin NUMERIC(12, 2) GENERATED ALWAYS AS (suggested_price - sale_price) STORED, -- Oportunidad bruta
    
    -- Datos Técnicos
    product_type VARCHAR(50),       -- 'SIMPLE' o 'VARIABLE'
    url_image_s3 TEXT,              -- URL de la imagen en alta calidad (AWS S3)
    
    -- Metadata de Rastreo
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

-- RELACIÓN MUCHOS A MUCHOS: Productos <-> Categorías
-- Un producto puede ser de "Salud" Y "Hogar" al mismo tiempo.
CREATE TABLE product_categories (
    product_id BIGINT REFERENCES products(product_id) ON DELETE CASCADE,
    category_id INT REFERENCES categories(id) ON DELETE CASCADE,
    PRIMARY KEY (product_id, category_id)
);

-- TABLA: product_stock_log (Rastreo de Inventario)
-- -----------------------------------------------------------
-- Histórico de stock. Si el stock baja, hubo ventas. 
-- Permite calcular "Velocity" (ventas por día).
CREATE TABLE product_stock_log (
    id SERIAL PRIMARY KEY,
    product_id BIGINT REFERENCES products(product_id),
    warehouse_id BIGINT REFERENCES warehouses(warehouse_id),
    stock_qty INT NOT NULL,
    snapshot_at TIMESTAMP DEFAULT NOW()
);
-- Índice para consultas rápidas de historial de un producto
CREATE INDEX idx_stock_log_product ON product_stock_log(product_id, snapshot_at DESC);


-- =======================================================================================
-- 4️⃣ NIVEL DE INTELIGENCIA ARTIFICIAL (VECTORES & CLUSTERING)
-- =======================================================================================

-- TABLA: product_embeddings (Cerebro Vectorial)
-- -----------------------------------------------------------
-- Aquí vive la IA. Almacenamos representaciones numéricas de las imágenes y textos.
-- Usaremos el modelo CLIP (OpenAI) que es estándar multimodal (imagen y texto en el mismo espacio).
CREATE TABLE product_embeddings (
    product_id BIGINT PRIMARY KEY REFERENCES products(product_id) ON DELETE CASCADE,
    
    -- Vector de IMAGEN (Modelo CLIP: 512 dimensiones)
    -- Permite buscar: "Dame productos que se vean como esta foto"
    embedding_visual vector(512),
    
    -- Vector de TEXTO (Modelo SBERT o CLIP-Text: 384 o 512 dimensiones)
    -- Permite buscar: "Dame productos descritos semánticamente igual"
    embedding_text vector(512), -- Asumiendo CLIP para simetría
    
    -- Check de estado
    processed_at TIMESTAMP DEFAULT NOW()
);

-- ÍNDICES HNSW (Hierarchical Navigable Small World)
-- Son vitales para que la búsqueda vectorial sea rápida (milisegundos) y no lenta (segundos).
-- 'ef_construction': Mayor número = índice más preciso pero más lento de crear.
-- 'm': Número de conexiones por nodo.
CREATE INDEX idx_emb_visual ON product_embeddings 
USING hnsw (embedding_visual vector_cosine_ops) 
WITH (m = 16, ef_construction = 64);

CREATE INDEX idx_emb_text ON product_embeddings 
USING hnsw (embedding_text vector_cosine_ops) 
WITH (m = 16, ef_construction = 64);


-- TABLA: unique_product_clusters (Agrupación de Identidad)
-- -----------------------------------------------------------
-- Tabla CALCULADA. Aquí decimos: "Los productos ID 100, 200 y 500 son en realidad el MISMO (Cluster A)".
-- Esto nos permite decir: "El Cluster A tiene 3 vendedores compitiendo".
CREATE TABLE unique_product_clusters (
    cluster_id BIGSERIAL PRIMARY KEY,
    representative_product_id BIGINT REFERENCES products(product_id), -- El producto "padre" o más antiguo
    total_competitors INT DEFAULT 1,
    average_price NUMERIC(12,2),
    saturation_score VARCHAR(20), -- 'BAJA', 'MEDIA', 'ALTA'
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Relación: Qué producto pertenece a qué cluster
CREATE TABLE product_cluster_membership (
    product_id BIGINT PRIMARY KEY REFERENCES products(product_id),
    cluster_id BIGINT REFERENCES unique_product_clusters(cluster_id),
    match_confidence DECIMAL(3,2), -- % de certeza (ej: 0.98 si es por Warehouse, 0.85 si es por IA)
    match_method VARCHAR(50)       -- 'EXACT_WAREHOUSE', 'VISUAL_AI', 'TEXT_AI'
);

-- =======================================================================================
-- 5️⃣ VISTAS DE ANÁLISIS (DASHBOARD READY)
-- =======================================================================================

-- VISTA: Oportunidades Ganadoras ("Golden Products")
-- Muestra grupos de productos con alta demanda potencial (stock moviéndose)
-- pero con POCOS competidores (baja saturación).
CREATE OR REPLACE VIEW view_golden_opportunities AS
SELECT 
    c.cluster_id,
    p.title AS sample_name,
    p.url_image_s3 AS sample_image,
    c.total_competitors,
    c.average_price,
    p.profit_margin AS potential_profit
FROM unique_product_clusters c
JOIN products p ON c.representative_product_id = p.product_id
WHERE c.total_competitors <= 3  -- Menos de 3 vendedores (Poco saturado)
AND p.profit_margin > 20000;    -- Ganancia de más de 20k (Vale la pena el envío)


-- =======================================================================================
-- 6 NIVEL DE MACHINE LEARNING & FEEDBACK (CEREBRO DIN�MICO)
-- =======================================================================================

-- TABLA: cluster_config (Configuraci�n Din�mica del Clusterizer)
-- -----------------------------------------------------------
-- Guarda los 'pesos' actuales que usa el algoritmo.
-- Esta tabla es le�da por el Clusterizer y escrita por el AI Trainer.
CREATE TABLE IF NOT EXISTS cluster_config (
    id SERIAL PRIMARY KEY,
    weight_visual FLOAT DEFAULT 0.6,      -- Peso Visual Actual
    weight_text FLOAT DEFAULT 0.4,        -- Peso Texto Actual
    threshold_visual_rescue FLOAT DEFAULT 0.15, -- Umbral Rescate Visual
    threshold_text_rescue FLOAT DEFAULT 0.95,   -- Umbral Rescate Texto
    threshold_hybrid FLOAT DEFAULT 0.68,        -- Umbral Aceptaci�n Final
    updated_at TIMESTAMP DEFAULT NOW(),
    version_note VARCHAR(100) DEFAULT 'Initial Config'
);

-- Inicializar con valores por defecto (Si la tabla est� vac�a)
INSERT INTO cluster_config (weight_visual, weight_text, threshold_visual_rescue, threshold_text_rescue, threshold_hybrid, version_note)
SELECT 0.6, 0.4, 0.15, 0.95, 0.68, 'Calibracion Manual V4'
WHERE NOT EXISTS (SELECT 1 FROM cluster_config);


-- TABLA: ai_feedback (Historial de Auditor�a Humana)
-- -----------------------------------------------------------
-- Guarda cada decisi�n que tomas en el 'Cluster Lab'.
-- Sirve de dataset de entrenamiento para calibrar los pesos.
CREATE TABLE IF NOT EXISTS ai_feedback (
    id SERIAL PRIMARY KEY,
    product_id BIGINT,          -- Producto A
    candidate_id BIGINT,        -- Producto B (Candidato)
    
    -- Evidencia (Snapshot del momento)
    visual_score FLOAT,         -- Similitud visual calculada (0-1)
    text_score FLOAT,           -- Similitud texto calculada (0-1)
    final_score FLOAT,          -- Score final que dio el sistema
    match_method VARCHAR(50),   -- Qu� regla se us� ('TEXT_RESCUE', 'HYBRID', etc.)
    active_weights JSONB,       -- Qu� pesos estaban vigentes {v:0.6, t:0.4}
    
    -- Veredicto Humano
    decision VARCHAR(20),       -- 'MATCH' o 'NO_MATCH' (Lo que decidi� la m�quina)
    feedback VARCHAR(20),       -- 'CORRECT' o 'INCORRECT' (Lo que dijiste t�)
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- �ndices para entrenamiento r�pido
CREATE INDEX idx_feedback_created ON ai_feedback(created_at DESC);

-- ============================================================================
-- OPTIMIZACION DE BASE DE DATOS - INDICES FALTANTES
-- Ejecutar este script para mejorar drásticamente el rendimiento de lectura
-- ============================================================================

-- 1. Índices para Dashboard y Filtrado de Productos
-- Acelera: "ORDER BY profit_margin" y busquedas por fecha de creación
CREATE INDEX IF NOT EXISTS idx_products_profit_created 
ON products (profit_margin DESC, created_at DESC);

-- Acelera: Filtros de nulos en imagenes (usado en vectorizer y dashboard)
CREATE INDEX IF NOT EXISTS idx_products_image_not_null 
ON products (product_id) 
WHERE url_image_s3 IS NOT NULL;

-- 2. Índices para Clusters y Competencia
-- Acelera: "competitors <= 10" y ordenamiento por precio
CREATE INDEX IF NOT EXISTS idx_clusters_competitors_price 
ON unique_product_clusters (total_competitors, average_price);

-- Acelera: Búsquedas de texto en títulos de productos (ILOVE operator)
-- Nota: Requiere extensión pg_trgm para mejor rendimiento, pero el índice btree ayuda en prefix scan
CREATE INDEX IF NOT EXISTS idx_products_title_lower 
ON products ((lower(title)));

-- 3. Índices para Membresía
-- Acelera: Joins entre Productos y Clusters (Crucial para eliminar N+1)
CREATE INDEX IF NOT EXISTS idx_cluster_membership_composite 
ON product_cluster_membership (product_id, cluster_id);

-- 4. Optimizaciones de Mantenimiento
VACUUM ANALYZE;
