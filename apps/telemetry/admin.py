from django.contrib import admin

from apps.telemetry.models import AnalogPoint, BinaryPoint, TelemetryRecord


@admin.register(TelemetryRecord)
class TelemetryRecordAdmin(admin.ModelAdmin):
    list_display = ("project", "cycle_timestamp", "derived_status", "ua", "ub", "uc", "ia", "ib", "ic")
    list_filter = ("derived_status", "project")
    readonly_fields = [field.name for field in TelemetryRecord._meta.fields]


@admin.register(AnalogPoint)
class AnalogPointAdmin(admin.ModelAdmin):
    list_display = ("telemetry", "label", "value", "timestamp")
    search_fields = ("label",)


@admin.register(BinaryPoint)
class BinaryPointAdmin(admin.ModelAdmin):
    list_display = ("telemetry", "label", "value", "timestamp")
    search_fields = ("label",)

