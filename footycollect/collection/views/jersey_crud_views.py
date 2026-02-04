"""
Jersey-specific CRUD views.

Contains JerseyCreateView and JerseyUpdateView.
"""

import json
import logging

from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _

from footycollect.collection.forms import JerseyForm
from footycollect.collection.models import BaseItem, Jersey
from footycollect.collection.services import get_collection_service

from .base import URL_NAME_ITEM_LIST, BaseItemCreateView, BaseItemUpdateView

logger = logging.getLogger(__name__)


class JerseyCreateView(BaseItemCreateView):
    """Create view specifically for jerseys."""

    model = Jersey
    form_class = JerseyForm
    template_name = "collection/item_form.html"
    success_url = reverse_lazy(URL_NAME_ITEM_LIST)

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

        try:
            collection_service = get_collection_service()
            form_data = collection_service.get_form_data()
            context["color_choices"] = json.dumps(form_data["colors"]["main_colors"])
            context["design_choices"] = json.dumps(
                [{"value": d[0], "label": str(d[1])} for d in BaseItem.DESIGN_CHOICES],
            )
        except (KeyError, AttributeError, ImportError) as exc:
            logger.warning("Error getting form data: %s", str(exc))
            context["color_choices"] = "[]"
            context["design_choices"] = "[]"

        context["proxy_image_url"] = reverse("collection:proxy_image")
        context["proxy_image_hosts"] = json.dumps(getattr(settings, "ALLOWED_EXTERNAL_IMAGE_HOSTS", []))
        return context

    def form_valid(self, form):
        """Handle form validation for jersey creation."""
        try:
            with transaction.atomic():
                form.user = self.request.user
                base_item = form.save()
                self.object = base_item

                self._process_post_creation()

                try:
                    from footycollect.collection.services.logo_download import (
                        ensure_item_entity_logos_downloaded,
                    )

                    ensure_item_entity_logos_downloaded(base_item)
                except Exception:
                    logger.exception("Error downloading club/brand logos for item")

                messages.success(self.request, _("Jersey created successfully!"))

                import time

                from django.http import HttpResponseRedirect

                url = str(self.get_success_url())
                sep = "&" if "?" in url else "?"
                url = f"{url}{sep}_={int(time.time() * 1000)}"
                return HttpResponseRedirect(url)

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

    def _process_post_creation(self):
        """Process any additional data after jersey creation."""
        self._ensure_brand_from_post()
        self._ensure_competition_from_post()

    def _ensure_brand_from_post(self):
        """Create or assign brand from POST brand_name if missing."""
        from django.utils.text import slugify

        from footycollect.core.models import Brand

        brand_name = self.request.POST.get("brand_name")
        if not brand_name or self.object.brand:
            return
        try:
            brand, created = Brand.objects.get_or_create(
                name=brand_name,
                defaults={"slug": slugify(brand_name)},
            )
            self.object.brand = brand
            self.object.save()
            logger.info("%s brand %s for jersey", "Created new" if created else "Found existing", brand.name)
        except (ValueError, TypeError):
            logger.exception("Error creating brand %s", brand_name)

    def _ensure_competition_from_post(self):
        """Add competition from POST competition_name if present."""
        from django.utils.text import slugify

        from footycollect.core.models import Competition

        competition_name = self.request.POST.get("competition_name")
        if not competition_name:
            return
        try:
            competition, created = Competition.objects.get_or_create(
                name=competition_name,
                defaults={"slug": slugify(competition_name)},
            )
            if competition not in self.object.competitions.all():
                self.object.competitions.add(competition)
                logger.info(
                    "%s competition %s to jersey",
                    "Created and added new" if created else "Added existing",
                    competition.name,
                )
        except (ValueError, TypeError):
            logger.exception("Error adding competition %s", competition_name)


class JerseyUpdateView(BaseItemUpdateView):
    """Update view specifically for jerseys."""

    model = Jersey
    form_class = JerseyForm
    template_name = "collection/item_form.html"
    success_url = reverse_lazy(URL_NAME_ITEM_LIST)
    success_message = _("Jersey updated successfully!")

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
                return super().form_valid(form)
        except (ValueError, TypeError, AttributeError):
            logger.exception("Error updating jersey")
            messages.error(self.request, _("Error updating jersey. Please try again."))
            return self.form_invalid(form)


__all__ = [
    "JerseyCreateView",
    "JerseyUpdateView",
]
