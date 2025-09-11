# Register your models here.

from django.contrib import admin

from .models import BaseItem, Color, Jersey, OtherItem, Outerwear, Pants, Photo, Shorts, Size, Tracksuit


@admin.register(BaseItem)
class BaseItemAdmin(admin.ModelAdmin):
    list_display = ["name", "item_type", "user", "brand", "club", "season", "condition", "created_at"]
    list_filter = ["item_type", "brand", "club", "season", "condition", "is_replica", "is_private", "is_draft"]
    search_fields = ["name", "description", "user__username", "brand__name", "club__name"]
    readonly_fields = ["created_at", "updated_at"]
    fieldsets = (
        (
            "Basic Information",
            {
                "fields": ("name", "item_type", "user", "brand", "club", "season"),
            },
        ),
        (
            "Details",
            {
                "fields": (
                    "condition",
                    "detailed_condition",
                    "description",
                    "design",
                    "main_color",
                    "secondary_colors",
                ),
            },
        ),
        (
            "Settings",
            {
                "fields": ("is_replica", "is_private", "is_draft", "country"),
            },
        ),
        (
            "Competitions & Tags",
            {
                "fields": ("competitions", "tags"),
                "classes": ("collapse",),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(Jersey)
class JerseyAdmin(admin.ModelAdmin):
    list_display = ["base_item", "size", "kit", "is_fan_version", "is_signed", "player_name", "number"]
    list_filter = ["is_fan_version", "is_signed", "has_nameset", "is_short_sleeve", "size", "kit"]
    search_fields = ["base_item__name", "player_name", "base_item__user__username"]
    fieldsets = (
        (
            "Jersey Details",
            {
                "fields": ("base_item", "kit", "size", "is_fan_version", "is_short_sleeve"),
            },
        ),
        (
            "Player Information",
            {
                "fields": ("is_signed", "has_nameset", "player_name", "number"),
            },
        ),
    )


@admin.register(Shorts)
class ShortsAdmin(admin.ModelAdmin):
    list_display = ["base_item", "size", "number", "is_fan_version"]
    list_filter = ["is_fan_version", "size"]
    search_fields = ["base_item__name", "base_item__user__username"]


@admin.register(Outerwear)
class OuterwearAdmin(admin.ModelAdmin):
    list_display = ["base_item", "type", "size"]
    list_filter = ["type", "size"]
    search_fields = ["base_item__name", "base_item__user__username"]


@admin.register(Tracksuit)
class TracksuitAdmin(admin.ModelAdmin):
    list_display = ["base_item", "size"]
    list_filter = ["size"]
    search_fields = ["base_item__name", "base_item__user__username"]


@admin.register(Pants)
class PantsAdmin(admin.ModelAdmin):
    list_display = ["base_item", "size"]
    list_filter = ["size"]
    search_fields = ["base_item__name", "base_item__user__username"]


@admin.register(OtherItem)
class OtherItemAdmin(admin.ModelAdmin):
    list_display = ["base_item", "type"]
    list_filter = ["type"]
    search_fields = ["base_item__name", "base_item__user__username"]


@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = ["content_object", "order", "uploaded_at", "user"]
    list_filter = ["uploaded_at", "user"]
    search_fields = ["caption", "user__username"]


@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ["name", "hex_value"]
    search_fields = ["name"]


@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ["name", "category"]
    list_filter = ["category"]
    search_fields = ["name"]
