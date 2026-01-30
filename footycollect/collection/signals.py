from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from footycollect.collection.cache_utils import invalidate_item_list_cache_for_user
from footycollect.collection.models import BaseItem, Jersey, Photo


@receiver(post_save, sender=BaseItem)
@receiver(post_delete, sender=BaseItem)
def invalidate_item_list_cache_for_base_item(sender, instance, **kwargs):
    if instance.user_id:
        invalidate_item_list_cache_for_user(instance.user_id)


@receiver(post_save, sender=Jersey)
@receiver(post_delete, sender=Jersey)
def invalidate_item_list_cache_for_jersey(sender, instance, **kwargs):
    user_id = instance.base_item.user_id if instance.base_item_id else None
    if user_id:
        invalidate_item_list_cache_for_user(user_id)


@receiver(post_save, sender=Photo)
@receiver(post_delete, sender=Photo)
def invalidate_item_list_cache_for_photo(sender, instance, **kwargs):
    user_id = None

    if hasattr(instance, "user_id") and instance.user_id:
        user_id = instance.user_id
    elif instance.content_object is not None and hasattr(instance.content_object, "user_id"):
        user_id = instance.content_object.user_id

    if user_id:
        invalidate_item_list_cache_for_user(user_id)
