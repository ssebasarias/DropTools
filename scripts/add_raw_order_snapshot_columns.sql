-- Añade columnas faltantes en raw_order_snapshots cuando la BD fue creada por init.sql
-- y las migraciones Django no se aplican (p. ej. contenttypes ya distinto).
-- Ejecutar desde el host:
--   Linux/macOS: docker exec -i dahell_db psql -U dahell_admin -d dahell_db < scripts/add_raw_order_snapshot_columns.sql
--   PowerShell: Get-Content scripts/add_raw_order_snapshot_columns.sql -Raw | docker exec -i dahell_db psql -U dahell_admin -d dahell_db

ALTER TABLE raw_order_snapshots ADD COLUMN IF NOT EXISTS customer_email VARCHAR(255) NULL;
ALTER TABLE raw_order_snapshots ADD COLUMN IF NOT EXISTS product_id VARCHAR(100) NULL;
ALTER TABLE raw_order_snapshots ADD COLUMN IF NOT EXISTS sku VARCHAR(100) NULL;
ALTER TABLE raw_order_snapshots ADD COLUMN IF NOT EXISTS variation VARCHAR(255) NULL;
ALTER TABLE raw_order_snapshots ADD COLUMN IF NOT EXISTS profit NUMERIC(12,2) NULL;
ALTER TABLE raw_order_snapshots ADD COLUMN IF NOT EXISTS shipping_price NUMERIC(12,2) NULL;
ALTER TABLE raw_order_snapshots ADD COLUMN IF NOT EXISTS supplier_price NUMERIC(12,2) NULL;
ALTER TABLE raw_order_snapshots ADD COLUMN IF NOT EXISTS store_type VARCHAR(50) NULL;
ALTER TABLE raw_order_snapshots ADD COLUMN IF NOT EXISTS store_name VARCHAR(100) NULL;
ALTER TABLE raw_order_snapshots ADD COLUMN IF NOT EXISTS order_time VARCHAR(20) NULL;
ALTER TABLE raw_order_snapshots ADD COLUMN IF NOT EXISTS report_date DATE NULL;
