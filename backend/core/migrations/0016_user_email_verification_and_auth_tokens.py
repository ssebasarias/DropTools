from django.db import migrations, models
import django.db.models.deletion
from django.utils import timezone
from django.conf import settings


def mark_existing_users_as_verified(apps, schema_editor):
    User = apps.get_model("core", "User")
    now = timezone.now()
    User.objects.filter(email_verified=False).update(
        email_verified=True,
        email_verified_at=now,
    )


def unmark_existing_users_as_verified(apps, schema_editor):
    User = apps.get_model("core", "User")
    User.objects.all().update(
        email_verified=False,
        email_verified_at=None,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0015_reduce_range_size_to_50"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="email_verified",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="user",
            name="email_verified_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name="AuthToken",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("token_hash", models.CharField(max_length=64)),
                ("purpose", models.CharField(choices=[("verify_email", "Verify email"), ("reset_password", "Reset password")], max_length=32)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField()),
                ("used_at", models.DateTimeField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, null=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="auth_tokens", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "auth_tokens",
            },
        ),
        migrations.AddIndex(
            model_name="authtoken",
            index=models.Index(fields=["token_hash", "purpose"], name="auth_tokens_token_h_0ef2ac_idx"),
        ),
        migrations.AddIndex(
            model_name="authtoken",
            index=models.Index(fields=["user", "purpose"], name="auth_tokens_user_id_3d4dcb_idx"),
        ),
        migrations.AddIndex(
            model_name="authtoken",
            index=models.Index(fields=["expires_at"], name="auth_tokens_expires_53da3b_idx"),
        ),
        migrations.RunPython(mark_existing_users_as_verified, unmark_existing_users_as_verified),
    ]
