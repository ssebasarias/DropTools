# Añade customer_email (y columnas de 0004 que puedan faltar) si la tabla
# fue creada por init.sql u otro esquema sin ellas. Seguro si la columna ya existe.

from django.db import migrations


def add_columns_if_missing(apps, schema_editor):
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'raw_order_snapshots';
        """)
        existing = {row[0] for row in cursor.fetchall()}
    if not existing:
        return  # tabla aún no existe (migraciones anteriores no aplicadas)

    # Columnas que 0004 añade y que el modelo actual espera
    to_add = [
        ("customer_email", "VARCHAR(255) NULL"),
        ("product_id", "VARCHAR(100) NULL"),
        ("sku", "VARCHAR(100) NULL"),
        ("variation", "VARCHAR(255) NULL"),
        ("profit", "NUMERIC(12,2) NULL"),
        ("shipping_price", "NUMERIC(12,2) NULL"),
        ("supplier_price", "NUMERIC(12,2) NULL"),
        ("store_type", "VARCHAR(50) NULL"),
        ("store_name", "VARCHAR(100) NULL"),
        ("order_time", "VARCHAR(20) NULL"),
        ("report_date", "DATE NULL"),
    ]
    with connection.cursor() as cursor:
        for col, col_type in to_add:
            if col not in existing:
                cursor.execute(
                    f"ALTER TABLE raw_order_snapshots ADD COLUMN {col} {col_type};"
                )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_remove_rawordersnapshot_analysis_empty_fields'),
    ]

    operations = [
        migrations.RunPython(add_columns_if_missing, noop),
    ]
