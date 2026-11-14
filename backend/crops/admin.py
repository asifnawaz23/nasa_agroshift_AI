from django.contrib import admin

from .models import Crop, CropCalendar, RotationTemplate


@admin.register(Crop)
class CropAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "family",
        "role",
        "water_need_mm",
        "drought_tolerance",
        'n_fixing',
    )
    list_filter = ("role", "family", "n_fixing", "root_depth")
    search_fields = ("name", "name_ur", "slug", "family")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(CropCalendar)
class CropCalendarAdmin(admin.ModelAdmin):
    list_display = ("crop", "zone", "season_label")
    list_filter = ("zone", "season_label")
    search_fields = ("crop__name", "season_label")
    list_select_related = ("crop",)


@admin.register(RotationTemplate)
class RotationTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "zone", "key")
    list_filter = ("zone", "key")
    search_fields = ("name", "description")