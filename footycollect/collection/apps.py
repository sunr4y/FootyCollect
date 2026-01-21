from django.apps import AppConfig


class CollectionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "footycollect.collection"

    def ready(self):
        # Import signals to ensure cache invalidation hooks are registered
        from footycollect.collection import signals  # noqa: F401
