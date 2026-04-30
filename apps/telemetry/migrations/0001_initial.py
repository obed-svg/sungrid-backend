import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="TelemetryRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("cycle_timestamp", models.DateTimeField(default=django.utils.timezone.now)),
                ("derived_status", models.CharField(max_length=10)),
                ("ia", models.FloatField(blank=True, null=True)),
                ("ib", models.FloatField(blank=True, null=True)),
                ("ic", models.FloatField(blank=True, null=True)),
                ("i_neutral", models.FloatField(blank=True, null=True)),
                ("ua", models.FloatField(blank=True, null=True)),
                ("ub", models.FloatField(blank=True, null=True)),
                ("uc", models.FloatField(blank=True, null=True)),
                ("ur", models.FloatField(blank=True, null=True)),
                ("us", models.FloatField(blank=True, null=True)),
                ("ut", models.FloatField(blank=True, null=True)),
                ("freq", models.FloatField(blank=True, null=True)),
                ("pf", models.FloatField(blank=True, null=True)),
                ("breaker_close", models.BooleanField(blank=True, null=True)),
                ("breaker_open", models.BooleanField(blank=True, null=True)),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="telemetry",
                        to="core.project",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="BinaryPoint",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("label", models.CharField(max_length=50)),
                ("value", models.BooleanField()),
                ("count_update", models.PositiveIntegerField()),
                ("timestamp", models.DateTimeField()),
                (
                    "telemetry",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="binaries",
                        to="telemetry.telemetryrecord",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="AnalogPoint",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("label", models.CharField(max_length=20)),
                ("value", models.FloatField()),
                ("count_update", models.PositiveIntegerField()),
                ("timestamp", models.DateTimeField()),
                (
                    "telemetry",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="analogs",
                        to="telemetry.telemetryrecord",
                    ),
                ),
            ],
        ),
        migrations.AddIndex(
            model_name="telemetryrecord",
            index=models.Index(fields=["project", "-cycle_timestamp"], name="telemetry_t_project_c15d1f_idx"),
        ),
        migrations.AddIndex(
            model_name="binarypoint",
            index=models.Index(fields=["telemetry", "label"], name="telemetry_b_telemet_5f6cb4_idx"),
        ),
        migrations.AddIndex(
            model_name="analogpoint",
            index=models.Index(fields=["telemetry", "label"], name="telemetry_a_telemet_657053_idx"),
        ),
    ]

