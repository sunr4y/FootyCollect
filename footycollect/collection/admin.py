# Register your models here.

from .models import Size
from django.contrib import admin
from .models import Jersey, Outerwear, Shorts, Tracksuit, Pants, OtherItem, Photo


admin.site.register(Size)
admin.site.register(Jersey)
admin.site.register(Outerwear)
admin.site.register(Shorts)
admin.site.register(Tracksuit)
admin.site.register(Pants)
admin.site.register(OtherItem)
admin.site.register(Photo)
# @admin.register(Photo)
# class PhotoAdmin(admin.ModelAdmin):
#     list_display = ('__str__', 'thumbnail_preview')  # Use default string representation instead of 'name'
#     readonly_fields = ('thumbnail_preview',)

#     def thumbnail_preview(self, obj):
#         return obj.thumbnail_preview

#     thumbnail_preview.short_description = 'Thumbnail Preview'
#     # Remove allow_tags as it's deprecated in newer Django versions
#     # Use mark_safe() in the model method instead

