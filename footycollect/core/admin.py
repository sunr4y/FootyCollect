# Register your models here.
from .models import Competition, Club, Brand, Kit, Season, TypeK
from django.contrib import admin

admin.site.register(Competition)
admin.site.register(Club)
admin.site.register(Brand)
admin.site.register(Kit)
admin.site.register(Season)
admin.site.register(TypeK)

