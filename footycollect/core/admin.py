# Register your models here.
from django.contrib import admin

from .models import Brand
from .models import Club
from .models import Competition
from .models import Kit
from .models import Season
from .models import TypeK

admin.site.register(Competition)
admin.site.register(Club)
admin.site.register(Brand)
admin.site.register(Kit)
admin.site.register(Season)
admin.site.register(TypeK)
