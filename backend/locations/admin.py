from django.contrib import admin

from .models import Location, LocationCache


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "country",
        "zone",
        "tier",
        "featured",
        "lat",
        "lon",
    )
    list_filter = ("country", "zone", "tier", "featured")
    search_fields = ("name", "slug", "country")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(LocationCache)
class LocationCacheAdmin(admin.ModelAdmin):
    list_display = (
        "kind",
        "grid_key",
        "fetched_at",
    )
    list_filter = ("kind",)
    search_fields = ("grid_key", "source_url")
    readonly_fields = ("fetched_at",)