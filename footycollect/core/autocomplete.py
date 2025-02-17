import logging

from dal import autocomplete
from django.utils.html import escape
from django.utils.html import format_html
from django_countries import countries

from .models import Brand

logger = logging.getLogger(__name__)


class BrandAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = Brand.objects.all()
        if self.q:
            qs = qs.filter(name__icontains=self.q)
        return qs.order_by("name")


class CountryAutocomplete(autocomplete.Select2ListView):
    def get_list(self):
        countries_list = list(countries)

        if self.q:
            countries_list = [
                (code, name)
                for code, name in countries_list
                if self.q.lower() in str(name).lower()
            ]

        return self.get_countries_list(countries_list)

    def get_countries_list(self, countries_list):
        return [
            (
                code,
                format_html(
                    '<i class="fi fi-{code}"></i> {name}',
                    code=escape(code.lower()),
                    name=escape(str(name)),
                ),
            )
            for code, name in countries_list
        ]

    def get_results(self, context):
        return super().get_results(context)

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
