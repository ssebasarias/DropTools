-- ============================================================================
-- LIMPIEZA AUTOMÁTICA DE BASE DE DATOS - Dahell Intelligence
-- ============================================================================
-- Uso: docker exec dahell_db psql -U dahell_admin -d dahell_db -f /app/scripts/cleanup_db.sql
-- Cron: 0 4 1 * * docker exec dahell_db psql -U dahell_admin -d dahell_db -f /app/scripts/cleanup_db.sql

-- ========================================
-- 1. Eliminar productos inactivos antiguos
-- ========================================
-- Productos que no se han visto en más de 6 meses
DELETE FROM products
WHERE is_active = false
AND last_seen_at < NOW() - INTERVAL '6 months';

-- ========================================
-- 2. Eliminar logs de decisiones antiguos
-- ========================================
-- Logs de clusterización de más de 3 meses
DELETE FROM cluster_decision_logs
WHERE timestamp < NOW() - INTERVAL '3 months';

-- Logs de feedback de IA de más de 3 meses
DELETE FROM ai_feedback
WHERE created_at < NOW() - INTERVAL '3 months';

-- ========================================
-- 3. Eliminar logs de stock antiguos
-- ========================================
-- Snapshots de stock de más de 2 meses
DELETE FROM product_stock_log
WHERE snapshot_at < NOW() - INTERVAL '2 months';

-- ========================================
-- 4. Eliminar logs de inteligencia de mercado antiguos
-- ========================================
-- Logs de más de 4 meses
DELETE FROM market_intelligence_logs
WHERE snapshot_at < NOW() - INTERVAL '4 months';

-- ========================================
-- 5. Limpiar clusters descartados antiguos
-- ========================================
-- Clusters descartados de más de 6 meses
DELETE FROM unique_product_clusters
WHERE is_discarded = true
AND updated_at < NOW() - INTERVAL '6 months';

-- ========================================
-- 6. Actualizar estadísticas de tablas
-- ========================================
ANALYZE products;
ANALYZE product_embeddings;
ANALYZE unique_product_clusters;
ANALYZE product_cluster_membership;

-- ========================================
-- 7. Vacuum para recuperar espacio
-- ========================================
-- NOTA: VACUUM FULL bloquea la tabla, usar solo en mantenimiento programado
-- Descomentar si es necesario:
-- VACUUM FULL products;
-- VACUUM FULL cluster_decision_logs;
-- VACUUM FULL ai_feedback;

-- Vacuum ligero (no bloquea)
VACUUM products;
VACUUM cluster_decision_logs;
VACUUM ai_feedback;
VACUUM product_stock_log;
VACUUM market_intelligence_logs;

-- ========================================
-- 8. Reindexar tablas críticas
-- ========================================
REINDEX TABLE products;
REINDEX TABLE product_embeddings;
REINDEX TABLE unique_product_clusters;

-- ========================================
-- 9. Mostrar estadísticas finales
-- ========================================
SELECT 
    'products' AS tabla,
    COUNT(*) AS total_registros,
    COUNT(*) FILTER (WHERE is_active = true) AS activos,
    COUNT(*) FILTER (WHERE is_active = false) AS inactivos
FROM products
UNION ALL
SELECT 
    'unique_product_clusters',
    COUNT(*),
    COUNT(*) FILTER (WHERE is_candidate = true),
    COUNT(*) FILTER (WHERE is_discarded = true)
FROM unique_product_clusters
UNION ALL
SELECT 
    'product_embeddings',
    COUNT(*),
    NULL,
    NULL
FROM product_embeddings;

-- Mostrar tamaño de tablas
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 10;
