# Register your models here.
from django.contrib import admin
from django.utils.html import format_html

from .models import Brand, Club, Competition, Kit, Season, TypeK

admin.site.register(Competition)


@admin.register(Club)
class ClubAdmin(admin.ModelAdmin):
    list_display = ("name", "show_logo")

    @admin.display(
        description="Logo",
    )
    def show_logo(self, obj):
        return format_html(
            '<img src="{}" style="max-height: 50px; max-width: 50px;" />',
            obj.logo,
        )


admin.site.register(Brand)
admin.site.register(Kit)
admin.site.register(Season)
admin.site.register(TypeK)
