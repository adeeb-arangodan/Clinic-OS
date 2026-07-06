from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from core.models import Branch, Entitlement, Tenant, User


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ["name", "subdomain", "plan", "status"]
    search_fields = ["name", "subdomain"]


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ["name_en", "name_ar", "tenant", "is_active"]
    list_filter = ["tenant"]


@admin.register(Entitlement)
class EntitlementAdmin(admin.ModelAdmin):
    list_display = ["tenant", "feature_code", "enabled"]
    list_filter = ["tenant", "enabled"]


@admin.register(User)
class CoreUserAdmin(UserAdmin):
    fieldsets = (*UserAdmin.fieldsets, ("Tenant", {"fields": ("tenant",)}))
    list_display = ["username", "email", "tenant", "is_staff"]
