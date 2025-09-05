# Register your models here.

from django.contrib import admin

from .models import Color, Jersey, OtherItem, Outerwear, Pants, Photo, Shorts, Size, Tracksuit

admin.site.register(Size)
admin.site.register(Jersey)
admin.site.register(Outerwear)
admin.site.register(Shorts)
admin.site.register(Tracksuit)
admin.site.register(Pants)
admin.site.register(OtherItem)
admin.site.register(Photo)
admin.site.register(Color)
