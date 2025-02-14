# Register your models here.

from django.contrib import admin

from .models import Jersey
from .models import OtherItem
from .models import Outerwear
from .models import Pants
from .models import Photo
from .models import Shorts
from .models import Size
from .models import Tracksuit

admin.site.register(Size)
admin.site.register(Jersey)
admin.site.register(Outerwear)
admin.site.register(Shorts)
admin.site.register(Tracksuit)
admin.site.register(Pants)
admin.site.register(OtherItem)
admin.site.register(Photo)
