"""
Base views and mixins for the collection app.

This module contains base classes and mixins that are shared across
different view types in the collection app.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.utils.translation import gettext as _
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from footycollect.collection.models import BaseItem
from footycollect.collection.services import get_item_service, get_photo_service


class CollectionLoginRequiredMixin(LoginRequiredMixin):
    """Mixin that requires user to be logged in to access collection views."""

    login_url = "/accounts/login/"
    redirect_field_name = "next"


class CollectionSuccessMessageMixin(SuccessMessageMixin):
    """Mixin that provides success messages for collection operations."""

    def get_success_message(self, cleaned_data):
        """Return the success message."""
        return _("Operation completed successfully.")


class BaseItemListView(CollectionLoginRequiredMixin, ListView):
    """Base list view for items in the collection."""

    model = BaseItem
    template_name = "collection/item_list.html"
    context_object_name = "items"
    paginate_by = 20

    def get_queryset(self):
        """Get all items using service layer with MTI structure."""
        item_service = get_item_service()
        return item_service.get_user_items(self.request.user)

    def get_context_data(self, **kwargs):
        """Add additional context data."""
        context = super().get_context_data(**kwargs)
        context["total_items"] = self.get_queryset().count()
        return context


class BaseItemDetailView(CollectionLoginRequiredMixin, DetailView):
    """Base detail view for items in the collection."""

    model = BaseItem
    template_name = "collection/item_detail.html"
    context_object_name = "item"

    def get_queryset(self):
        """Get all items using service layer with MTI structure."""
        item_service = get_item_service()
        return item_service.get_user_items(self.request.user)

    def get_context_data(self, **kwargs):
        """Add additional context data."""
        context = super().get_context_data(**kwargs)
        photo_service = get_photo_service()
        context["photos"] = photo_service.get_item_photos(self.object)
        # Get the specific item instance (Jersey, Shorts, etc.) for MTI
        context["specific_item"] = self.object.get_specific_item()
        return context


class BaseItemCreateView(
    CollectionLoginRequiredMixin,
    CollectionSuccessMessageMixin,
    CreateView,
):
    """Base create view for items in the collection."""

    model = BaseItem
    template_name = "collection/item_form.html"
    success_url = reverse_lazy("collection:item_list")

    def get_form_kwargs(self):
        """Add user to form kwargs."""
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        # Ensure we have an instance for the form
        if "instance" not in kwargs:
            kwargs["instance"] = self.model()
        return kwargs

    def form_valid(self, form):
        """Process the form when it is valid."""
        return super().form_valid(form)


class BaseItemUpdateView(
    CollectionLoginRequiredMixin,
    CollectionSuccessMessageMixin,
    UpdateView,
):
    """Base update view for items in the collection."""

    model = BaseItem
    template_name = "collection/item_form.html"
    success_url = reverse_lazy("collection:item_list")

    def get_queryset(self):
        """Get all items."""
        return BaseItem.objects.all()


class BaseItemDeleteView(
    CollectionLoginRequiredMixin,
    CollectionSuccessMessageMixin,
    DeleteView,
):
    """Base delete view for items in the collection."""

    model = BaseItem
    template_name = "collection/item_confirm_delete.html"
    success_url = reverse_lazy("collection:item_list")

    def get_queryset(self):
        """Get all items."""
        return BaseItem.objects.all()

    def delete(self, request, *args, **kwargs):
        """Override delete to add custom success message."""
        messages.success(request, _("Item deleted successfully."))
        return super().delete(request, *args, **kwargs)
