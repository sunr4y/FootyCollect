from typing import Any
from urllib.parse import urlencode

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import QuerySet
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, ListView, RedirectView, UpdateView

from footycollect.collection.models import Jersey
from footycollect.collection.services.item_service import ItemService
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
        self.profile_user = profile_user
        self.filter_params: dict[str, str] = {}
        user_service = UserService()
        if not user_service.can_view_profile(profile_user, self.request.user):
            raise Http404
        queryset = (
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

        club_slug = self.request.GET.get("club")
        if club_slug:
            queryset = queryset.filter(base_item__club__slug=club_slug)
            self.filter_params["club"] = club_slug

        competition_slug = self.request.GET.get("competition")
        if competition_slug:
            queryset = queryset.filter(base_item__competitions__slug=competition_slug).distinct()
            self.filter_params["competition"] = competition_slug

        country_code = self.request.GET.get("country")
        if country_code:
            queryset = queryset.filter(base_item__country=country_code)
            self.filter_params["country"] = country_code

        brand_slug = self.request.GET.get("brand")
        if brand_slug:
            queryset = queryset.filter(base_item__brand__slug=brand_slug)
            self.filter_params["brand"] = brand_slug

        design_code = self.request.GET.get("design")
        if design_code:
            queryset = queryset.filter(base_item__design=design_code)
            self.filter_params["design"] = design_code

        color_id = self.request.GET.get("color")
        if color_id:
            try:
                color_id_int = int(color_id)
            except (TypeError, ValueError):
                color_id_int = None
            if color_id_int:
                queryset = queryset.filter(base_item__main_color_id=color_id_int)
                self.filter_params["color"] = str(color_id_int)

        fit_value = self.request.GET.get("fit", "").strip()
        if fit_value and any(fit_value == c[0] for c in Jersey.FIT_CHOICES if c[0]):
            queryset = queryset.filter(fit=fit_value)
            self.filter_params["fit"] = fit_value

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile_user = self._get_profile_user()

        self._add_profile_context(context, profile_user)
        self._add_geo_stats_context(context, profile_user)

        current_filters = self._get_current_filters()
        self._add_current_filters_context(context, current_filters)
        self._add_active_filters_context(context, profile_user, current_filters)
        self._add_pagination_query_string(context)

        return context

    def _get_profile_user(self) -> User:
        return getattr(self, "profile_user", None) or get_object_or_404(
            User,
            username=self.kwargs["username"],
        )

    def _add_profile_context(self, context: dict[str, Any], profile_user: User) -> None:
        context["profile_user"] = profile_user
        context["is_user_collection"] = True
        context["can_edit_items"] = profile_user == self.request.user
        page = context.get("page_obj")
        context["total_items"] = page.paginator.count if page else 0

    def _add_geo_stats_context(self, context: dict[str, Any], profile_user: User) -> None:
        item_service = ItemService()
        geo_stats = item_service.get_user_geo_stats(profile_user)
        context["geo_summary"] = geo_stats["summary_counts"]
        context["top_geo_cards"] = {
            "club": geo_stats["top_club"],
            "country": geo_stats["top_country"],
            "competition": geo_stats["top_competition"],
            "brand": geo_stats["top_brand"],
            "design": geo_stats["top_design"],
            "color": geo_stats["top_color"],
        }
        context["top_clubs"] = geo_stats["top_clubs"]
        context["top_countries"] = geo_stats["top_countries"]
        context["top_competitions"] = geo_stats["top_competitions"]
        context["top_brands"] = geo_stats["top_brands"]
        context["top_designs"] = geo_stats["top_designs"]
        context["top_colors"] = geo_stats["top_colors"]
        context["fit_choices"] = [(c[0], c[1]) for c in Jersey.FIT_CHOICES if c[0]]

    def _get_current_filters(self) -> dict[str, str]:
        return getattr(self, "filter_params", {})

    def _add_current_filters_context(
        self,
        context: dict[str, Any],
        current_filters: dict[str, str],
    ) -> None:
        context["current_filters"] = current_filters
        if current_filters:
            filter_type, filter_value = next(iter(current_filters.items()))
            context["current_filter_type"] = filter_type
            context["current_filter_value"] = filter_value

    def _add_active_filters_context(
        self,
        context: dict[str, Any],
        profile_user: User,
        current_filters: dict[str, str],
    ) -> None:
        type_labels = {
            "club": _("Club"),
            "competition": _("League"),
            "country": _("Country"),
            "brand": _("Brand"),
            "design": _("Design"),
            "color": _("Main colour"),
            "fit": _("How it fits"),
        }
        base_url = reverse("users:user_items", kwargs={"username": profile_user.username})
        active_filters_display = []
        for filter_type, filter_value in (current_filters or {}).items():
            label = self._get_filter_label(filter_type, filter_value, context)
            other_params = {key: value for key, value in (current_filters or {}).items() if key != filter_type}
            clear_url = self._build_clear_filter_url(base_url, other_params)
            active_filters_display.append(
                {
                    "type": filter_type,
                    "value": filter_value,
                    "type_label": type_labels.get(filter_type, filter_type),
                    "label": label or filter_value,
                    "clear_url": clear_url,
                },
            )
        context["active_filters_display"] = active_filters_display
        context["user_items_base_url"] = base_url

    def _get_filter_label(
        self,
        filter_type: str,
        filter_value: str,
        context: dict[str, Any],
    ) -> str | None:
        lookup_config: dict[str, dict[str, Any]] = {
            "club": {"source": "top_clubs"},
            "competition": {"source": "top_competitions"},
            "country": {"source": "top_countries"},
            "brand": {"source": "top_brands"},
            "design": {"source": "top_designs", "use_code_fallback": True},
            "color": {"source": "top_colors", "coerce_to_str": True},
            "fit": {"source": "fit_choices"},
        }
        config = lookup_config.get(filter_type)
        if not config:
            return None
        if filter_type == "fit":
            for choice_value, choice_label in context.get("fit_choices") or []:
                if choice_value == filter_value:
                    return str(choice_label)
            return None

        items = context.get(config["source"], [])
        coerce_to_str = config.get("coerce_to_str", False)
        use_code_fallback = config.get("use_code_fallback", False)

        for item in items:
            candidate = item.get("slug_or_code")
            if use_code_fallback:
                candidate = candidate or item.get("code")
            if coerce_to_str:
                if str(candidate or "") == str(filter_value or ""):
                    return item.get("label")
            elif (candidate or "") == (filter_value or ""):
                return item.get("label")

        return None

    def _build_clear_filter_url(
        self,
        base_url: str,
        other_params: dict[str, str],
    ) -> str:
        if not other_params:
            return base_url

        query_params = dict(other_params)
        query_params["page"] = 1
        encoded = urlencode(query_params, doseq=True)
        return f"{base_url}?{encoded}"

    def _add_pagination_query_string(self, context: dict[str, Any]) -> None:
        query = self.request.GET.copy()
        query.pop("page", None)
        context["query_string"] = query.urlencode()

    def render_to_response(self, context, **response_kwargs):
        """
        Return only the items grid when requested via HTMX.
        """
        if self.request.headers.get("HX-Request"):
            return render(
                self.request,
                "collection/_user_collection_htmx_block.html",
                context,
                **response_kwargs,
            )
        return super().render_to_response(context, **response_kwargs)


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
