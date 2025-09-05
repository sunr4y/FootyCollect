from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import QuerySet
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, RedirectView, UpdateView

from footycollect.users.forms import UserUpdateForm
from footycollect.users.models import User


class UserDetailView(LoginRequiredMixin, DetailView):
    model = User
    slug_field = "username"
    slug_url_kwarg = "username"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.get_object()

        # Only show details if the profile is public or it's the user's own profile
        if not user.is_private or user == self.request.user:
            context["show_details"] = True

            # Calculate collection stats for the user
            from footycollect.collection.models import Jersey

            # Get user's jerseys directly
            user_jerseys = Jersey.objects.filter(user=user)

            # Calculate stats
            context["total_items"] = user_jerseys.count()
            context["total_teams"] = user_jerseys.filter(club__isnull=False).values("club").distinct().count()
            context["total_competitions"] = (
                user_jerseys.filter(competitions__isnull=False).values("competitions").distinct().count()
            )

            # Get recent items for display
            context["recent_items"] = user_jerseys.select_related("club", "brand", "season").order_by("-created_at")[
                :5
            ]

        return context


user_detail_view = UserDetailView.as_view()


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
