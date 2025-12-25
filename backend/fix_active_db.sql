
-- Activar extension por si acaso (idempotente)
CREATE EXTENSION IF NOT EXISTS vector;

-- Corregir tabla product_embeddings
-- 1. Eliminar columnas viejas/erroneas
ALTER TABLE product_embeddings DROP COLUMN IF EXISTS embedding_visual;
ALTER TABLE product_embeddings DROP COLUMN IF EXISTS embedding_text;

-- 2. Crear columna correcta con 1152 dimensiones (SigLIP)
ALTER TABLE product_embeddings ADD COLUMN embedding_visual vector(1152);

-- 3. Limpiar tabla para evitar conflictos con datos viejos
TRUNCATE TABLE product_embeddings;

-- 4. Verificar estado
SELECT column_name, data_type, udt_name 
FROM information_schema.columns 
WHERE table_name = 'product_embeddings';
