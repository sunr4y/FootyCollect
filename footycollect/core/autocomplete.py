from dal import autocomplete
from .models import Brand, Club
from django_countries import countries
from django.utils.html import format_html
from django.utils.safestring import mark_safe
import logging

logger = logging.getLogger(__name__)

class BrandAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = Brand.objects.all()
        if self.q:
            qs = qs.filter(name__icontains=self.q)
        return qs.order_by('name')

class CountryAutocomplete(autocomplete.Select2ListView):
    def get_list(self):
        countries_list = list(countries)
        if self.q:
            countries_list = [
                (code, name) 
                for code, name in countries_list 
                if self.q.lower() in str(name).lower()
            ]
        
        return [
            (
                code,
                mark_safe(f'<i class="fi fi-{code.lower()}"></i> {str(name)}')
            )
            for code, name in countries_list
        ]

    def get_results(self, context):
        """Convert results to Select2 format"""
        return [
            {
                'id': code,
                'text': str(name).split('>')[-1].strip(),
                'html': mark_safe(str(name))
            }
            for code, name in context['results']
        ]

    def get(self, request, *args, **kwargs):
        logger.info(f"GET request received: {request.GET}")
        try:
            response = super().get(request, *args, **kwargs)
            logger.info(f"Response content sample: {str(response.content)[:200]}")
            return response
        except Exception as e:
            logger.error(f"Error in get: {str(e)}", exc_info=True)
            raise

# class ClubAutocomplete(autocomplete.Select2QuerySetView):
#     def get_queryset(self):
#         qs = Club.objects.all()
#         if self.q:
#             qs = qs.filter(name__icontains=self.q)
#         return qs