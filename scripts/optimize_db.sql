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
