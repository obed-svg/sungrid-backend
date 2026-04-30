from django.contrib import admin

from apps.maneuvers.models import ManeuverLog


@admin.register(ManeuverLog)
class ManeuverLogAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "user", "project", "action", "pre_status", "post_status", "result")
    list_filter = ("action", "result", "project")
    readonly_fields = [field.name for field in ManeuverLog._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

