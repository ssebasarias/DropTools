from django.db import migrations


def normalize_not_found_to_no_encontrado(apps, schema_editor):
    OrderReport = apps.get_model("core", "OrderReport")
    OrderReport.objects.filter(status="not_found").update(status="no_encontrado")


def revert_no_encontrado_to_not_found(apps, schema_editor):
    OrderReport = apps.get_model("core", "OrderReport")
    OrderReport.objects.filter(status="no_encontrado").update(status="not_found")


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0018_encrypt_dropi_passwords"),
    ]

    operations = [
        migrations.RunPython(
            normalize_not_found_to_no_encontrado,
            revert_no_encontrado_to_not_found,
        ),
    ]
