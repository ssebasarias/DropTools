-- ============================================
-- MIGRACIÓN: Cambiar PK de products a clave compuesta
-- Fecha: 2025-12-27
-- Objetivo: Permitir que múltiples proveedores vendan el mismo producto
-- ============================================

BEGIN;

-- PASO 1: Verificar que no hay duplicados (product_id, supplier_id)
DO $$
DECLARE
    duplicate_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO duplicate_count
    FROM (
        SELECT product_id, supplier_id, COUNT(*) as cnt
        FROM products
        GROUP BY product_id, supplier_id
        HAVING COUNT(*) > 1
    ) duplicates;
    
    IF duplicate_count > 0 THEN
        RAISE EXCEPTION 'Existen % combinaciones duplicadas de (product_id, supplier_id). Abortando migración.', duplicate_count;
    END IF;
    
    RAISE NOTICE 'Verificación OK: No hay duplicados';
END $$;

-- PASO 2: Eliminar constraints de foreign keys que dependen de la PK actual
-- (Las recrearemos después)

-- Guardar definiciones de FKs para recrearlas después
CREATE TEMP TABLE temp_fk_definitions AS
SELECT 
    conname,
    conrelid::regclass::text as table_name,
    pg_get_constraintdef(oid) as definition
FROM pg_constraint
WHERE confrelid = 'products'::regclass AND contype = 'f';

-- Eliminar las FKs temporalmente
DO $$
DECLARE
    fk_record RECORD;
BEGIN
    FOR fk_record IN 
        SELECT conname, conrelid::regclass::text as table_name
        FROM pg_constraint
        WHERE confrelid = 'products'::regclass AND contype = 'f'
    LOOP
        EXECUTE format('ALTER TABLE %I DROP CONSTRAINT %I', fk_record.table_name, fk_record.conname);
        RAISE NOTICE 'Eliminada FK: %.%', fk_record.table_name, fk_record.conname;
    END LOOP;
END $$;

-- PASO 3: Eliminar la PK actual
ALTER TABLE products DROP CONSTRAINT products_pkey;
RAISE NOTICE 'PK antigua eliminada';

-- PASO 4: Crear la nueva PK compuesta
ALTER TABLE products ADD CONSTRAINT products_pkey 
    PRIMARY KEY (product_id, supplier_id);
RAISE NOTICE 'Nueva PK compuesta creada: (product_id, supplier_id)';

-- PASO 5: Crear índice adicional para búsquedas por product_id solo
CREATE INDEX IF NOT EXISTS idx_products_product_id ON products(product_id);
RAISE NOTICE 'Índice adicional creado para product_id';

-- PASO 6: Recrear las foreign keys
-- IMPORTANTE: Las FKs que apuntaban a products.product_id ahora necesitan
-- apuntar a la clave compuesta, pero esto requiere que las tablas referenciantes
-- también tengan supplier_id. Por ahora, las dejamos sin recrear y las manejaremos
-- manualmente según sea necesario.

RAISE NOTICE '==============================================';
RAISE NOTICE 'ADVERTENCIA: Las siguientes FKs NO fueron recreadas:';
RAISE NOTICE 'Necesitan ser ajustadas manualmente según el modelo de datos:';

DO $$
DECLARE
    fk_record RECORD;
BEGIN
    FOR fk_record IN SELECT * FROM temp_fk_definitions
    LOOP
        RAISE NOTICE '  - %.%: %', fk_record.table_name, fk_record.conname, fk_record.definition;
    END LOOP;
END $$;

RAISE NOTICE '==============================================';

-- PASO 7: Verificar el resultado
DO $$
DECLARE
    pk_columns TEXT;
BEGIN
    SELECT string_agg(a.attname, ', ' ORDER BY array_position(i.indkey, a.attnum))
    INTO pk_columns
    FROM pg_index i
    JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
    WHERE i.indrelid = 'products'::regclass AND i.indisprimary;
    
    RAISE NOTICE 'Nueva PK de products: %', pk_columns;
END $$;

COMMIT;

-- ============================================
-- RESULTADO ESPERADO:
-- - PK de products: (product_id, supplier_id)
-- - Índice adicional en product_id para búsquedas rápidas
-- - FKs eliminadas (requieren ajuste manual del modelo)
-- ============================================
