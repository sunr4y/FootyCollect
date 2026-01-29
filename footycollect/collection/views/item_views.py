"""
Item-specific views for the collection app.

Contains JerseySelectView.
JerseyCreateView and JerseyUpdateView live in jersey_crud_views.py.
ItemCreateView, ItemUpdateView, ItemDeleteView live in crud_views.py.
"""

import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView

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
