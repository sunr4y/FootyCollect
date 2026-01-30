from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import QuerySet
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, ListView, RedirectView, UpdateView

from footycollect.collection.models import Jersey
from footycollect.users.forms import UserUpdateForm
from footycollect.users.models import User
from footycollect.users.services import UserService


class UserDetailView(LoginRequiredMixin, DetailView):
    model = User
    slug_field = "username"
    slug_url_kwarg = "username"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.get_object()

        # Use service to get profile data with MTI structure
        user_service = UserService()
        profile_data = user_service.get_user_profile_data(user, self.request.user)

        # Add profile data to context
        context.update(profile_data)

        return context


user_detail_view = UserDetailView.as_view()


class UserItemListView(LoginRequiredMixin, ListView):
    template_name = "collection/item_list.html"
    context_object_name = "items"
    paginate_by = 20

    def get_queryset(self):
        profile_user = get_object_or_404(User, username=self.kwargs["username"])
        user_service = UserService()
        if not user_service.can_view_profile(profile_user, self.request.user):
            raise Http404
        return (
            Jersey.objects.filter(base_item__user=profile_user)
            .select_related(
                "base_item",
                "base_item__user",
                "base_item__club",
                "base_item__season",
                "base_item__brand",
                "base_item__main_color",
                "size",
                "kit",
                "kit__type",
            )
            .prefetch_related(
                "base_item__competitions",
                "base_item__photos",
                "base_item__secondary_colors",
                "base_item__tags",
            )
            .order_by("-base_item__created_at")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile_user = get_object_or_404(User, username=self.kwargs["username"])
        context["profile_user"] = profile_user
        context["is_user_collection"] = True
        context["can_edit_items"] = profile_user == self.request.user
        if context.get("page_obj"):
            context["total_items"] = context["page_obj"].paginator.count
        else:
            context["total_items"] = 0
        return context


user_item_list_view = UserItemListView.as_view()


class UserUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = User
    form_class = UserUpdateForm
    success_message = _("Profile updated successfully")

    def get_object(self, queryset: QuerySet | None = None) -> User:
        assert self.request.user.is_authenticated  # type guard
        return self.request.user

    def get_success_url(self):
        return reverse("users:detail", kwargs={"username": self.request.user.username})


user_update_view = UserUpdateView.as_view()


class UserRedirectView(LoginRequiredMixin, RedirectView):
    permanent = False

    def get_redirect_url(self) -> str:
        return reverse("users:detail", kwargs={"username": self.request.user.username})


user_redirect_view = UserRedirectView.as_view()
