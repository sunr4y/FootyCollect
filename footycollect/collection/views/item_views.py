"""
Item-specific views for the collection app.

This module contains views that handle CRUD operations for items
in the collection, such as jerseys, shirts, etc.
"""

import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView

from footycollect.collection.cache_utils import invalidate_item_list_cache_for_user
from footycollect.collection.forms import JerseyForm
from footycollect.collection.models import Jersey

from .base import BaseItemCreateView, BaseItemDeleteView, BaseItemUpdateView

logger = logging.getLogger(__name__)


class JerseySelectView(LoginRequiredMixin, TemplateView):
    """View for browsing and selecting kit templates from the database."""

    template_name = "collection/jersey_select.html"

    # Performance optimization fields
    select_related_fields = ["user"]
    prefetch_related_fields = []

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["help_text"] = _(
            "Browse available kit templates in our database. "
            "A 'kit' is the design/template (e.g., 'FC Barcelona 2020-21 Home Kit'). "
            "After selecting a kit, you'll add details about your specific physical item "
            "(size, condition, player name, photos, etc.). Multiple users can own the same kit "
            "but with different customizations!",
        )
        return context


class ItemCreateView(BaseItemCreateView):
    """Create view for adding new items to the collection."""

    template_name = "collection/item_form.html"
    success_url = reverse_lazy("collection:item_list")

    def get_form_class(self):
        """Return the appropriate form class based on the item type."""
        item_type = self.request.GET.get("type", "jersey")
        if item_type == "jersey":
            return JerseyForm
        # Add other form types as needed
        return JerseyForm

    def get_context_data(self, **kwargs):
        """Add context data for item creation."""
        context = super().get_context_data(**kwargs)

        # Add options for Cotton components using services
        try:
            import json

            from footycollect.collection.models import BaseItem
            from footycollect.collection.services import get_collection_service

            collection_service = get_collection_service()
            form_data = collection_service.get_form_data()
            context["color_choices"] = json.dumps(form_data["colors"]["main_colors"])
            context["design_choices"] = json.dumps(
                [{"value": d[0], "label": str(d[1])} for d in BaseItem.DESIGN_CHOICES],
            )
        except (KeyError, AttributeError, ImportError) as e:
            logger.warning("Error getting form data: %s", str(e))
            context["color_choices"] = "[]"
            context["design_choices"] = "[]"

        return context


class ItemUpdateView(BaseItemUpdateView):
    """Update view for editing existing items in the collection."""

    template_name = "collection/item_form.html"
    success_url = reverse_lazy("collection:item_list")

    def form_valid(self, form):
        """
        Handle form validation for item updates, including photo processing.

        This method:
        - associates uploaded photos from the Cotton photo manager
        - applies the current ordering
        - removes photos that were deleted in the UI
        """
        response = super().form_valid(form)

        photo_ids = self.request.POST.get("photo_ids", "")
        if not photo_ids:
            return response

        parsed = self._parse_photo_ids(photo_ids)
        if parsed is None:
            return response

        keep_ids, order_map, external_images = self._extract_photo_data(parsed)

        self._update_existing_photos(keep_ids, order_map)
        self._remove_deleted_photos(keep_ids)

        if external_images:
            logger.info("Ignoring external images on edit (not implemented): %s", external_images)

        return response

    def _parse_photo_ids(self, photo_ids):
        """Parse photo_ids JSON payload."""
        import json

        try:
            parsed = json.loads(photo_ids)
        except (TypeError, ValueError, json.JSONDecodeError):
            logger.warning("Invalid photo_ids payload for ItemUpdateView: %s", photo_ids)
            return None

        if not isinstance(parsed, list):
            logger.warning("Unexpected photo_ids structure for ItemUpdateView: %s", type(parsed))
            return None

        return parsed

    def _extract_photo_data(self, parsed):
        """Extract keep_ids, order_map, and external_images from parsed payload."""
        keep_ids: set[int] = set()
        order_map: dict[int, int] = {}
        external_images: list[dict] = []

        for item in parsed:
            if not isinstance(item, dict):
                continue

            photo_id = item.get("id")
            order = item.get("order", 0)
            is_external = item.get("external", False)
            url = item.get("url")

            if is_external and url:
                external_images.append({"url": url, "order": order})
            elif photo_id:
                try:
                    pid_int = int(photo_id)
                    keep_ids.add(pid_int)
                    order_map[pid_int] = order
                except (TypeError, ValueError):
                    continue

        return keep_ids, order_map, external_images

    def _update_existing_photos(self, keep_ids, order_map):
        """Attach existing photos and update their order."""
        if not keep_ids:
            return

        from django.contrib.contenttypes.models import ContentType

        from footycollect.collection.models import Photo

        photos = Photo.objects.filter(id__in=keep_ids, user=self.request.user)
        content_type = ContentType.objects.get_for_model(self.object)

        for photo in photos:
            photo.content_type = content_type
            photo.object_id = self.object.id
            if photo.id in order_map:
                photo.order = order_map[photo.id]
            photo.save()

    def _remove_deleted_photos(self, keep_ids):
        """Remove photos that were not included in the payload (user deleted them)."""
        try:
            existing_photos = self.object.photos.filter(user=self.request.user)
            photos_to_delete = existing_photos.exclude(id__in=keep_ids) if keep_ids else existing_photos

            if photos_to_delete.exists():
                photos_to_delete.delete()
        except (OSError, AttributeError):
            logger.exception("Error cleaning up removed photos in ItemUpdateView")

    def get_form_class(self):
        """Return the appropriate form class based on the item type."""
        if isinstance(self.object, Jersey):
            return JerseyForm
        # Add other form types as needed
        return JerseyForm

    def get_context_data(self, **kwargs):
        """Add context data for item update."""
        context = super().get_context_data(**kwargs)
        context["is_edit"] = True

        self._add_color_and_design_choices(context)
        self._add_initial_photos(context)
        self._add_autocomplete_initial_data(context)

        return context

    def _add_color_and_design_choices(self, context):
        """Add color and design choices for Cotton components."""
        import json

        from footycollect.collection.models import BaseItem
        from footycollect.collection.services import get_collection_service

        try:
            collection_service = get_collection_service()
            form_data = collection_service.get_form_data()
            context["color_choices"] = json.dumps(form_data["colors"]["main_colors"])
            context["design_choices"] = json.dumps(
                [{"value": d[0], "label": str(d[1])} for d in BaseItem.DESIGN_CHOICES],
            )
        except (KeyError, AttributeError, ImportError) as e:
            logger.warning("Error getting form data: %s", str(e))
            context["color_choices"] = "[]"
            context["design_choices"] = "[]"

    def _add_initial_photos(self, context):
        """Pre-load existing photos for the photo manager."""
        import json

        try:
            photos = self.object.photos.order_by("order", "id")
            photo_list = [self._build_photo_dict(photo) for photo in photos]
            context["initial_photos"] = json.dumps(photo_list)
        except (AttributeError, ValueError, TypeError, OSError) as exc:
            logger.warning("Error building initial_photos for ItemUpdateView: %s", str(exc))
            context["initial_photos"] = "[]"

    def _build_photo_dict(self, photo):
        """Build a dictionary representation of a photo."""
        try:
            url = photo.get_image_url()
            thumbnail_url = getattr(photo.thumbnail, "url", None) or url
        except (AttributeError, ValueError):
            url = f"/media/item_photos/{photo.image.name}" if photo.image.name else ""
            thumbnail_url = url

        return {
            "id": photo.id,
            "url": url,
            "thumbnail_url": thumbnail_url,
            "order": photo.order,
            "uploading": False,
        }

    def _add_autocomplete_initial_data(self, context):
        """Pre-load initial values for autocomplete components."""
        import json

        try:
            base_item = self.get_object()
            kit = self._get_kit_from_base_item(base_item)

            initial_data = {
                "brand": self._get_entity_data(base_item, kit, "brand", "brand"),
                "club": self._get_entity_data(base_item, kit, "club", "team"),
                "season": self._get_season_data(base_item, kit),
                "competitions": self._get_competitions_data(base_item, kit),
            }
            # Remove None values
            initial_data = {k: v for k, v in initial_data.items() if v}

            context["autocomplete_initial_data"] = json.dumps(initial_data)
            logger.info("Autocomplete initial data for ItemUpdateView: %s", context["autocomplete_initial_data"])
        except (AttributeError, ValueError, TypeError, KeyError) as e:
            logger.warning("Error building autocomplete initial data for ItemUpdateView: %s", e)
            context["autocomplete_initial_data"] = "{}"

    def _get_kit_from_base_item(self, base_item):
        """Try to get kit from base_item's jersey."""
        try:
            if hasattr(base_item, "jersey"):
                jersey = base_item.jersey
                if jersey and hasattr(jersey, "kit") and jersey.kit:
                    return jersey.kit
        except AttributeError:
            pass
        return None

    def _get_entity_data(self, base_item, kit, base_item_attr, kit_attr):
        """Get entity data (brand/club) from base_item or kit."""
        # Try from base_item first
        try:
            entity = getattr(base_item, base_item_attr, None)
            if entity:
                return {
                    "id": entity.id,
                    "name": entity.name,
                    "logo": getattr(entity, "logo", None) or "",
                }
        except AttributeError:
            pass

        # Try from kit
        if kit:
            try:
                entity = getattr(kit, kit_attr, None)
                if entity:
                    return {
                        "id": entity.id,
                        "name": entity.name,
                        "logo": getattr(entity, "logo", None) or "",
                    }
            except AttributeError:
                pass

        return None

    def _get_season_data(self, base_item, kit):
        """Get season data from base_item or kit."""
        # Try from base_item first
        try:
            season = base_item.season
            if season:
                return {"id": season.id, "name": season.year, "logo": ""}
        except AttributeError:
            pass

        # Try from kit
        if kit:
            try:
                season = kit.season
                if season:
                    return {"id": season.id, "name": season.year, "logo": ""}
            except AttributeError:
                pass

        return None

    def _get_competitions_data(self, base_item, kit):
        """Get competitions data from base_item or kit."""
        # Try from base_item first
        try:
            competitions = list(base_item.competitions.all())
            if competitions:
                return [
                    {"id": comp.id, "name": comp.name, "logo": getattr(comp, "logo", None) or ""}
                    for comp in competitions
                ]
        except AttributeError:
            pass

        # Try from kit
        if kit:
            try:
                competitions = list(kit.competition.all())
                if competitions:
                    return [
                        {"id": comp.id, "name": comp.name, "logo": getattr(comp, "logo", None) or ""}
                        for comp in competitions
                    ]
            except AttributeError:
                pass

        return None


class ItemDeleteView(BaseItemDeleteView):
    """Delete view for removing items from the collection."""

    template_name = "collection/item_confirm_delete.html"
    success_url = reverse_lazy("collection:item_list")

    def get_success_url(self):
        """Return to the same page after deletion."""
        page = self.request.POST.get("page") or self.request.GET.get("page")
        base_url = reverse_lazy("collection:item_list")
        if page and page != "1":
            return f"{base_url}?page={page}"
        return base_url

    def delete(self, request, *args, **kwargs):
        """Override delete to handle photo cleanup."""
        item = self.get_object()

        # Delete associated photos
        photos = item.photos.all()
        for photo in photos:
            photo.delete()

        # Use a plain English success message so tests can assert on the word \"photo\"
        # (avoid translation changing the literal text).
        messages.success(request, "Item and associated photos deleted successfully.")

        # Invalidate cached item list pages for this user so the next render
        # isn't served from a stale cache that was generated before the message
        # was added. This is important for tests that assert on the presence
        # of the success message in the redirected response.
        invalidate_item_list_cache_for_user(request.user.pk)

        return super().delete(request, *args, **kwargs)


class JerseyCreateView(BaseItemCreateView):
    """Create view specifically for jerseys."""

    model = Jersey
    form_class = JerseyForm
    template_name = "collection/item_form.html"
    success_url = reverse_lazy("collection:item_list")

    def get_context_data(self, **kwargs):
        """Add context data for jersey creation."""
        context = super().get_context_data(**kwargs)
        context["item_type"] = "jersey"
        context["is_manual_mode"] = True
        context["help_text"] = _(
            "Use this form to add a jersey that is not in our kit database. "
            "Search for clubs, seasons, and competitions. If they don't exist, you can create them. "
            "This is perfect for fantasy clubs, custom jerseys, or rare items not in the database.",
        )

        # Add translated labels for autocomplete components
        context["label_brand"] = _("Brand")
        context["label_club"] = _("Club")
        context["label_season"] = _("Season")
        context["label_competitions"] = _("Competitions")
        context["help_brand"] = _(
            "Search for a brand from the external database. If not found, you can create it manually.",
        )
        context["help_club"] = _("Search for a club. If not found, you can create it manually.")
        context["help_season"] = _("Search for a season (e.g., 2020-21). If not found, you can create it manually.")
        context["help_competitions"] = _(
            "Search for competitions from the external database. If not found, you can create them manually.",
        )

        # Add options for Cotton components using services
        try:
            import json

            from footycollect.collection.models import BaseItem
            from footycollect.collection.services import get_collection_service

            collection_service = get_collection_service()
            form_data = collection_service.get_form_data()
            context["color_choices"] = json.dumps(form_data["colors"]["main_colors"])
            context["design_choices"] = json.dumps(
                [{"value": d[0], "label": str(d[1])} for d in BaseItem.DESIGN_CHOICES],
            )
        except (KeyError, AttributeError, ImportError) as e:
            logger.warning("Error getting form data: %s", str(e))
            context["color_choices"] = "[]"
            context["design_choices"] = "[]"

        return context

    def form_valid(self, form):
        """Handle form validation for jersey creation."""
        try:
            with transaction.atomic():
                # JerseyForm.save() creates both BaseItem and Jersey objects
                # It needs the user in the form's user attribute
                form.user = self.request.user

                # Save the jersey (this creates BaseItem and Jersey)
                base_item = form.save()

                # Set self.object for CreateView's redirect
                self.object = base_item

                # Process any additional data
                self._process_post_creation(form)

                messages.success(self.request, _("Jersey created successfully!"))

                # Redirect to success URL
                from django.http import HttpResponseRedirect

                return HttpResponseRedirect(self.get_success_url())

        except (ValueError, TypeError, AttributeError):
            logger.exception("Error creating jersey")
            messages.error(
                self.request,
                _("Error creating jersey."),
            )
            return self.form_invalid(form)

    def form_invalid(self, form):
        """Handle form validation errors."""
        logger.warning("Form validation failed. Errors: %s", form.errors)
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(self.request, f"{field}: {error}")
        return super().form_invalid(form)

    def _process_post_creation(self, form):
        """Process any additional data after jersey creation."""
        from django.utils.text import slugify

        from footycollect.core.models import Brand, Competition

        brand_name = self.request.POST.get("brand_name")
        if brand_name and not self.object.brand:
            try:
                brand, created = Brand.objects.get_or_create(
                    name=brand_name,
                    defaults={"slug": slugify(brand_name)},
                )
                self.object.brand = brand
                self.object.save()
                if created:
                    logger.info("Created new brand %s for jersey", brand.name)
                else:
                    logger.info("Found existing brand %s for jersey", brand.name)
            except (ValueError, TypeError):
                logger.exception("Error creating brand %s", brand_name)

        competition_name = self.request.POST.get("competition_name")
        if competition_name:
            try:
                competition, created = Competition.objects.get_or_create(
                    name=competition_name,
                    defaults={"slug": slugify(competition_name)},
                )
                if competition not in self.object.competitions.all():
                    self.object.competitions.add(competition)
                    if created:
                        logger.info("Created and added new competition %s to jersey", competition.name)
                    else:
                        logger.info("Added existing competition %s to jersey", competition.name)
            except (ValueError, TypeError):
                logger.exception("Error adding competition %s", competition_name)


class JerseyUpdateView(BaseItemUpdateView):
    """Update view specifically for jerseys."""

    model = Jersey
    form_class = JerseyForm
    template_name = "collection/item_form.html"
    success_url = reverse_lazy("collection:item_list")

    def get_context_data(self, **kwargs):
        """Add context data for jersey editing."""
        context = super().get_context_data(**kwargs)
        context["item_type"] = "jersey"
        context["is_edit"] = True
        return context

    def form_valid(self, form):
        """Handle form validation for jersey updates."""
        try:
            with transaction.atomic():
                response = super().form_valid(form)
                messages.success(self.request, _("Jersey updated successfully!"))
                return response

        except (ValueError, TypeError, AttributeError):
            logger.exception("Error updating jersey")
            messages.error(self.request, _("Error updating jersey. Please try again."))
            return self.form_invalid(form)
