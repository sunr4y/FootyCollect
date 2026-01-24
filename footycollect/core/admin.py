# Register your models here.
from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin

from .models import Brand, Club, Competition, Kit, Season, TypeK


@admin.register(Competition)
class CompetitionAdmin(ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Club)
class ClubAdmin(ModelAdmin):
    list_display = ("name", "country", "show_logo")
    list_filter = ("country",)
    search_fields = ("name", "country")
    list_per_page = 25

    @admin.display(
        description="Logo",
    )
    def show_logo(self, obj):
        if obj.logo:
            return format_html(
                '<img src="{}" style="max-height: 50px; max-width: 50px;" />',
                obj.logo,
            )
        return "No logo"


@admin.register(Brand)
class BrandAdmin(ModelAdmin):
    list_display = ("name", "show_logo")
    search_fields = ("name",)

    @admin.display(description="Logo")
    def show_logo(self, obj):
        if obj.logo:
            return format_html(
                '<img src="{}" style="max-height: 50px; max-width: 50px;" />',
                obj.logo,
            )
        return "No logo"


@admin.register(Kit)
class KitAdmin(ModelAdmin):
    list_display = ("name", "team", "season")
    list_filter = ("team", "season")
    search_fields = ("name", "team__name", "season__year")


@admin.register(Season)
class SeasonAdmin(ModelAdmin):
    list_display = ("year", "first_year", "second_year")
    search_fields = ("year",)


@admin.register(TypeK)
class TypeKAdmin(ModelAdmin):
    list_display = ("name", "category", "is_goalkeeper")
    list_filter = ("category", "is_goalkeeper")
    search_fields = ("name",)
    ordering = ("category", "is_goalkeeper", "name")
