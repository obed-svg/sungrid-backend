import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("core", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ManeuverLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action", models.CharField(choices=[("TRIP", "TRIP"), ("CLOSE", "CLOSE")], max_length=10)),
                ("pre_status", models.CharField(max_length=10)),
                ("pre_snapshot", models.JSONField()),
                ("post_status", models.CharField(blank=True, default="", max_length=10)),
                ("post_snapshot", models.JSONField(blank=True, null=True)),
                (
                    "result",
                    models.CharField(
                        choices=[
                            ("success", "Success"),
                            ("fail_guard", "Fail (guard)"),
                            ("fail_tcp", "Fail (TCP)"),
                            ("fail_verify", "Fail (verify)"),
                            ("fail_locked", "Fail (mutex)"),
                            ("fail_cooldown", "Fail (cooldown)"),
                            ("fail_tunnel", "Fail (tunnel)"),
                        ],
                        max_length=20,
                    ),
                ),
                ("error_message", models.TextField(blank=True)),
                ("tx_frame", models.CharField(blank=True, max_length=200)),
                ("rx_frame", models.CharField(blank=True, max_length=200)),
                ("timestamp", models.DateTimeField(auto_now_add=True)),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="maneuvers",
                        to="core.project",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="maneuvers",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.AddIndex(
            model_name="maneuverlog",
            index=models.Index(fields=["-timestamp"], name="maneuvers_m_timesta_868f7a_idx"),
        ),
        migrations.AddIndex(
            model_name="maneuverlog",
            index=models.Index(fields=["project", "-timestamp"], name="maneuvers_m_project_7c752e_idx"),
        ),
    ]

