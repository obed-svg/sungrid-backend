from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.core.models import Project, User


@admin.register(User)
class SungridUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("SUN-GRID", {"fields": ("role",)}),)
    list_display = ("username", "email", "role", "is_active", "is_staff")
    list_filter = ("role", "is_active", "is_staff")


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "ip", "port", "master_id", "outstation_id", "enabled")
    list_filter = ("enabled",)
    search_fields = ("name", "ip")

