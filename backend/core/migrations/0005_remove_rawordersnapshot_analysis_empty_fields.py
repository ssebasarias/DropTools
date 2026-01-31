# Remove columns: mostly empty or not relevant for analysis
# - shipping_type: always "con recaudo", not relevant
# - profit: computed (total - flete - proveedor), not extracted from Excel
# - notes, novelty, novelty_resolved, last_movement, last_movement_date, tags, commission: mostly empty

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_add_raw_order_snapshot_analysis_fields'),
    ]

    operations = [
        migrations.RemoveField(model_name='rawordersnapshot', name='shipping_type'),
        migrations.RemoveField(model_name='rawordersnapshot', name='notes'),
        migrations.RemoveField(model_name='rawordersnapshot', name='novelty'),
        migrations.RemoveField(model_name='rawordersnapshot', name='novelty_resolved'),
        migrations.RemoveField(model_name='rawordersnapshot', name='last_movement'),
        migrations.RemoveField(model_name='rawordersnapshot', name='last_movement_date'),
        migrations.RemoveField(model_name='rawordersnapshot', name='tags'),
        migrations.RemoveField(model_name='rawordersnapshot', name='commission'),
    ]
