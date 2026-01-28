from django import forms
from django.utils.translation import gettext_lazy as _

from footycollect.collection.forms_jersey_base import JerseyForm
from footycollect.collection.models import Color


class JerseyFKAPIForm(JerseyForm):
    """Enhanced form for creating jerseys with FKAPI integration."""

    class Meta(JerseyForm.Meta):
        """Meta class for JerseyFKAPIForm - inherits from JerseyForm.Meta"""

    kit_search = forms.CharField(
        required=False,
        label=_("Search Kit"),
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": _("Start typing to search for kits..."),
                "x-model": "kitSearch",
                "x-on:input.debounce.500ms": "searchKits()",
            },
        ),
    )
    name = forms.CharField(
        max_length=255,
        required=False,
        help_text="Auto-generated from kit if not provided",
    )

    kit_id = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput(),
    )

    club_search = forms.CharField(
        required=False,
        label=_("Search Club"),
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": _("Or search for a club..."),
                "x-model": "clubSearch",
                "x-on:input.debounce.500ms": "searchClubs()",
                "x-show": "showClubSearch",
            },
        ),
    )

    brand_name = forms.CharField(required=False, widget=forms.HiddenInput())
    club_name = forms.CharField(required=False, widget=forms.HiddenInput())
    season_name = forms.CharField(required=False, widget=forms.HiddenInput())
    competition_name = forms.CharField(required=False, widget=forms.HiddenInput())

    main_img_url = forms.URLField(required=False, widget=forms.HiddenInput(), assume_scheme="https")

    external_image_urls = forms.CharField(required=False, widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        if "instance" not in kwargs or kwargs["instance"] is None:
            from footycollect.collection.models import BaseItem

            kwargs["instance"] = BaseItem()

        super().__init__(*args, **kwargs)

        if self.instance is None:
            from footycollect.collection.models import BaseItem

            self.instance = BaseItem()

        using_api = False
        if (
            "data" in kwargs
            and kwargs["data"]
            and kwargs["data"].get("brand_name")
            or "initial" in kwargs
            and kwargs["initial"]
            and kwargs["initial"].get("brand_name")
        ):
            using_api = True

        if using_api:
            self.fields["brand"].required = False
            self.fields["club"].required = False
            self.fields["season"].required = False
            self.fields["competitions"].required = False
            self.fields["main_color"].required = False
            self.fields["secondary_colors"].required = False

    def _get_main_color_name(self, value):
        """Extract main color name from form data."""
        import logging

        logger = logging.getLogger(__name__)

        main_color_name = self.data.get("main_color")
        logger.debug("clean_main_color - from self.data: %s", main_color_name)

        if not main_color_name and hasattr(self.data, "getlist"):
            color_list = self.data.getlist("main_color")
            if color_list:
                main_color_name = color_list[0]
                logger.debug("clean_main_color - from getlist: %s", main_color_name)

        if not main_color_name:
            main_color_name = self.initial.get("main_color")
            logger.debug("clean_main_color - from initial: %s", main_color_name)

        if not main_color_name and value:
            try:
                color_obj = Color.objects.get(pk=value)
                logger.debug("clean_main_color - found Color by ID: %s", color_obj)
            except (Color.DoesNotExist, ValueError, TypeError):
                pass
            else:
                return color_obj, None

        return None, main_color_name

    def clean_main_color(self):
        """Convert main_color string to Color object."""
        import logging

        logger = logging.getLogger(__name__)

        value = self.cleaned_data.get("main_color")

        if value and hasattr(value, "name"):
            logger.debug("clean_main_color - already Color object: %s", value)
            return value

        color_obj, main_color_name = self._get_main_color_name(value)
        if color_obj:
            return color_obj

        if not main_color_name:
            logger.debug("clean_main_color - no value found, returning None")
            return None

        try:
            color_obj, created = Color.objects.get_or_create(
                name__iexact=main_color_name.strip(),
                defaults={"name": main_color_name.strip().upper()},
            )
            logger.info("clean_main_color - returning Color: %s (created=%s)", color_obj, created)
        except (ValueError, TypeError):
            logger.exception("clean_main_color - error")
            return None
        else:
            return color_obj

    def _get_secondary_colors_names(self):
        """Extract secondary color names from form data.

        Tries multiple sources in order: getlist, direct get, cleaned_data, initial.
        """
        import logging

        logger = logging.getLogger(__name__)

        result = self._get_colors_from_getlist(logger)
        if result:
            return result

        result = self._get_colors_from_direct_get(logger)
        if result:
            return result

        result = self._get_colors_from_cleaned_data(logger)
        if result:
            return result

        result = self._get_colors_from_initial(logger)
        if result:
            return result

        return []

    def _get_colors_from_getlist(self, logger):
        """Try to get colors using getlist for multiple values."""
        if not hasattr(self.data, "getlist"):
            return None
        names = self.data.getlist("secondary_colors")
        if not names:
            return None
        result = [str(n).strip() for n in names if n]
        if result:
            logger.debug("clean_secondary_colors - from getlist: %s", names)
        return result or None

    def _get_colors_from_direct_get(self, logger):
        """Try to get colors using direct get (single value or list)."""
        colors = self.data.get("secondary_colors")
        if not colors:
            return None
        names = colors if isinstance(colors, list) else [colors]
        result = [str(n).strip() for n in names if n]
        if result:
            logger.debug("clean_secondary_colors - from get: %s", result)
        return result or None

    def _get_colors_from_cleaned_data(self, logger):
        """Try to get colors from cleaned_data (from to_python)."""
        if not hasattr(self, "cleaned_data") or not self.cleaned_data:
            return None
        colors = self.cleaned_data.get("secondary_colors")
        if not colors:
            return None
        result = []
        items = colors if isinstance(colors, list) else [colors]
        for c in items:
            if isinstance(c, str):
                result.append(c.strip())
            elif isinstance(c, Color):
                result.append(c.name)
        if result:
            logger.debug("clean_secondary_colors - from cleaned_data: %s", result)
        return result or None

    def _get_colors_from_initial(self, logger):
        """Try to get colors from initial data."""
        colors = self.initial.get("secondary_colors")
        if not colors:
            return None
        names = colors if isinstance(colors, list) else [colors]
        result = [str(n).strip() for n in names if n]
        if result:
            logger.debug("clean_secondary_colors - from initial: %s", result)
        return result or None

    def _convert_color_names_to_objects(self, color_names):
        """Convert color name strings to Color objects."""
        import logging

        logger = logging.getLogger(__name__)

        color_objects = []
        for color_name in color_names:
            if not color_name:
                continue

            if isinstance(color_name, Color):
                color_objects.append(color_name)
                continue

            try:
                color_id = int(color_name)
                color_obj = Color.objects.get(id=color_id)
                color_objects.append(color_obj)
                logger.debug("clean_secondary_colors - found Color by ID: %s", color_obj.name)
                continue
            except (ValueError, TypeError, Color.DoesNotExist):
                pass

            try:
                color_obj, created = Color.objects.get_or_create(
                    name__iexact=str(color_name).strip(),
                    defaults={"name": str(color_name).strip().upper()},
                )
                color_objects.append(color_obj)
                logger.debug("clean_secondary_colors - added Color: %s (created=%s)", color_obj.name, created)
            except (ValueError, TypeError):
                logger.exception("clean_secondary_colors - error for %s", color_name)

        return color_objects

    def clean_secondary_colors(self):
        """Convert secondary_colors strings to Color objects."""
        import logging

        logger = logging.getLogger(__name__)

        secondary_colors_names = self._get_secondary_colors_names()

        if not secondary_colors_names:
            logger.debug("clean_secondary_colors - no values found, returning []")
            return []

        color_objects = self._convert_color_names_to_objects(secondary_colors_names)
        logger.debug("clean_secondary_colors - returning %s colors", len(color_objects))
        return color_objects

    def clean_country_code(self):
        """Validate and return country code."""
        import logging

        logger = logging.getLogger(__name__)

        country_code = self.data.get("country_code")
        logger.debug("clean_country_code - from self.data: %s", country_code)

        if not country_code:
            country_code = self.initial.get("country_code")
            logger.debug("clean_country_code - from initial: %s", country_code)

        if country_code:
            try:
                from django_countries import countries

                if country_code.upper() in dict(countries):
                    logger.debug("clean_country_code - valid: %s", country_code.upper())
                    return country_code.upper()
                logger.warning("clean_country_code - invalid code: %s", country_code)
            except (ValueError, AttributeError, ImportError):
                logger.exception("clean_country_code - error")

        return country_code

    def clean(self):
        import logging

        logger = logging.getLogger(__name__)
        logger.debug("=== JerseyFKAPIForm.clean() CALLED ===")
        data_keys = list(self.data.keys()) if hasattr(self.data, "keys") else "N/A"
        logger.debug("self.data keys: %s", data_keys)
        logger.debug("country_code in data: %s", self.data.get("country_code"))
        cleaned_data = super().clean()
        using_api = bool(self.data.get("brand_name"))
        logger.debug("using_api: %s", using_api)
        logger.debug("cleaned_data keys: %s", list(cleaned_data.keys()))
        logger.debug("country_code in cleaned_data: %s", cleaned_data.get("country_code"))
        logger.debug("main_color in cleaned_data: %s", cleaned_data.get("main_color"))
        logger.debug(
            "secondary_colors in cleaned_data: %s",
            cleaned_data.get("secondary_colors"),
        )
        if using_api:
            for field in [
                "brand",
                "club",
                "season",
                "competitions",
                "main_color",
                "secondary_colors",
            ]:
                if field in self._errors:
                    del self._errors[field]

        return cleaned_data


__all__ = [
    "JerseyFKAPIForm",
]
