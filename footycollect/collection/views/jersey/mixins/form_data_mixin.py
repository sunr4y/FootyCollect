"""
Mixin for handling form data manipulation and validation.

This mixin provides methods to fill form fields, set initial values,
and ensure cleaned_data contains required fields.
"""

import logging

from django.db import IntegrityError

from footycollect.collection.models import Color

logger = logging.getLogger(__name__)


class FormDataMixin:
    """
    Mixin for form data manipulation functionality.

    Note: This mixin may depend on EntityProcessingMixin for
    _update_club_country and _create_club_from_api_data methods.
    """

    DEFAULT_ITEM_NAME = "Jersey"

    def _set_main_color_initial(self, form):
        """Convert main_color name to ID for template."""
        main_color_value = form.data.get("main_color") or (
            form.initial.get("main_color") if hasattr(form, "initial") else None
        )
        if not main_color_value:
            return

        if isinstance(main_color_value, str) and not main_color_value.isdigit():
            try:
                color_obj = Color.objects.get(name__iexact=main_color_value.strip())
                form.fields["main_color"].initial = color_obj.id
            except Color.DoesNotExist:
                logger.warning("Main color '%s' not found in database", main_color_value)
        else:
            form.fields["main_color"].initial = main_color_value

    def _set_secondary_colors_initial(self, form):
        """Convert secondary_colors names to IDs for template."""
        secondary_colors_value = self._get_secondary_colors_from_data(form)
        if not secondary_colors_value:
            return

        color_ids = []
        for color_val in secondary_colors_value:
            color_id = self._resolve_secondary_color_id(color_val)
            if color_id is not None:
                color_ids.append(color_id)

        if color_ids:
            form.fields["secondary_colors"].initial = color_ids

    def _get_secondary_colors_from_data(self, form):
        """Return secondary_colors from form.data as a normalized list."""
        return self._parse_secondary_colors_from_data(form, allow_comma_split=False)

    def _resolve_secondary_color_id(self, color_val):
        """Resolve a color value (name or ID) to a numeric ID when possible."""
        if not color_val:
            return None
        if isinstance(color_val, str) and not color_val.isdigit():
            try:
                color_obj = Color.objects.get(name__iexact=color_val.strip())
            except Color.DoesNotExist:
                logger.warning("Secondary color '%s' not found in database", color_val)
                return None
            return color_obj.id
        if isinstance(color_val, str) and color_val.isdigit():
            return int(color_val)
        return color_val

    def _ensure_country_code_in_cleaned_data(self, form):
        """Ensure country_code is in cleaned_data."""
        country_code = form.cleaned_data.get("country_code")
        if not country_code:
            if form.data.get("country_code"):
                country_code = form.data.get("country_code")
                form.cleaned_data["country_code"] = country_code
            elif hasattr(self, "fkapi_data") and "team_country" in self.fkapi_data:
                country_code = self.fkapi_data["team_country"]
                form.cleaned_data["country_code"] = country_code

    def _ensure_main_color_in_cleaned_data(self, form):
        """Ensure main_color is in cleaned_data."""
        main_color = form.cleaned_data.get("main_color")
        if not main_color and form.data.get("main_color"):
            main_color_str = form.data.get("main_color")
            if main_color_str:
                normalized = main_color_str.strip()
                try:
                    color_obj, _ = Color.objects.get_or_create(
                        name__iexact=normalized,
                        defaults={"name": normalized.upper()},
                    )
                except IntegrityError:
                    color_obj = Color.objects.get(name__iexact=normalized)
                form.cleaned_data["main_color"] = color_obj
                logger.info(
                    "Set main_color in cleaned_data from form.data: %s -> %s",
                    main_color_str,
                    color_obj.name,
                )

    def _ensure_secondary_colors_in_cleaned_data(self, form):
        """Ensure secondary_colors are in cleaned_data."""
        secondary_colors = form.cleaned_data.get("secondary_colors", [])
        if not secondary_colors:
            secondary_colors_raw = self._get_secondary_colors_raw_for_cleaned_data(form)
            if secondary_colors_raw:
                color_objects = self._build_secondary_color_objects(secondary_colors_raw)
                if color_objects:
                    form.cleaned_data["secondary_colors"] = color_objects
                    logger.info(
                        "Set secondary_colors in cleaned_data from form.data: %s",
                        [c.name for c in color_objects],
                    )

    def _get_secondary_colors_raw_for_cleaned_data(self, form):
        """Return secondary_colors from form.data as list of strings for cleaned_data."""
        return self._parse_secondary_colors_from_data(form, allow_comma_split=True)

    def _parse_secondary_colors_from_data(self, form, *, allow_comma_split: bool):
        """Internal helper to normalize secondary_colors from form.data."""
        if hasattr(form.data, "getlist"):
            values = form.data.getlist("secondary_colors")
        else:
            raw_value = form.data.get("secondary_colors")
            if isinstance(raw_value, str):
                values = [c.strip() for c in raw_value.split(",") if c.strip()] if allow_comma_split else [raw_value]
            elif isinstance(raw_value, list):
                values = raw_value
            else:
                values = []
        return values or []

    def _build_secondary_color_objects(self, secondary_colors_raw):
        """Create Color objects from the raw secondary color strings."""
        color_objects = []
        for color_str in secondary_colors_raw:
            if isinstance(color_str, str) and color_str.strip():
                normalized = color_str.strip()
                try:
                    color_obj, _ = Color.objects.get_or_create(
                        name__iexact=normalized,
                        defaults={"name": normalized.upper()},
                    )
                except IntegrityError:
                    color_obj = Color.objects.get(name__iexact=normalized)
                color_objects.append(color_obj)
        return color_objects

    def _ensure_form_cleaned_data(self, form):
        """Ensure country_code and colors are in cleaned_data before processing."""
        self._ensure_country_code_in_cleaned_data(form)
        self._ensure_main_color_in_cleaned_data(form)
        self._ensure_secondary_colors_in_cleaned_data(form)

    def _ensure_mutable_form_data(self, form):
        """
        Ensure form.data is a mutable mapping.

        Assigns a shallow copy (form.data.copy()). Falls back to dict(form.data)
        on AttributeError. Mutates the form in-place. Used by FormDataMixin to
        allow safe modifications of request-bound form data.
        """
        try:
            form.data = form.data.copy()
        except AttributeError:
            form.data = dict(form.data)

    def _fill_form_with_api_data(self, form):
        """Fill form fields with API data. Makes form.data mutable and sets name if needed."""
        self._ensure_mutable_form_data(form)

        if not form.data.get("name") and form.instance.name:
            form.data["name"] = form.instance.name

        self._fill_club_field(form)
        self._fill_brand_field(form)
        self._fill_season_field(form)

    def _setup_form_instance(self, form):
        """Set up form instance for jersey creation (STI)."""
        from footycollect.collection.models import BaseItem

        self._ensure_form_instance(form, BaseItem)
        form.instance.item_type = "jersey"
        self._ensure_instance_name(form)
        self._ensure_form_name_matches_instance(form)
        self._set_instance_user(form)
        self._set_instance_country_from_data(form)

    def _ensure_form_instance(self, form, base_model):
        """Ensure form.instance exists and has a model instance."""
        if getattr(form, "instance", None) is not None:
            return

        if (
            hasattr(form, "_meta")
            and getattr(form, "_meta", None) is not None
            and hasattr(form._meta, "model")
            and form._meta.model is not None
        ):
            instance = form._meta.model()
        else:
            instance = base_model()

        form.instance = instance

    def _ensure_instance_name(self, form):
        """Ensure the instance has a name derived from form data when missing."""
        if form.instance.name:
            return
        name = form.data.get("name")
        if name:
            form.instance.name = name
            return
        club_name = form.data.get("club_name", "")
        season_name = form.data.get("season_name", "")
        if club_name and season_name:
            form.instance.name = f"{club_name} {season_name}"
        else:
            form.instance.name = self.DEFAULT_ITEM_NAME

    def _ensure_form_name_matches_instance(self, form):
        """Ensure form.data['name'] is populated from instance.name when needed."""
        if form.data.get("name") or not form.instance.name:
            return
        form.data["name"] = form.instance.name

    def _set_instance_user(self, form):
        """Attach the current request user to the instance when available."""
        if hasattr(self, "request") and self.request and hasattr(self.request, "user"):
            form.instance.user = self.request.user

    def _set_instance_country_from_data(self, form):
        """Set instance.country from form data when provided."""
        country_code = form.data.get("country_code")
        if country_code:
            form.instance.country = country_code
            logger.info("Set country to %s", country_code)

    def _preprocess_form_data(self, form):
        """
        Set up form instance, process kit data if kit_id present, then fill from API.

        Relies on _fill_form_with_api_data to ensure form.data is mutable for
        any subsequent modifications performed by this mixin.
        """
        self._setup_form_instance(form)
        kit_id = form.data.get("kit_id")
        if kit_id:
            self._process_kit_data(form, kit_id)
        self._fill_form_with_api_data(form)

    def _fill_club_field(self, form):
        """Fill club field from API data."""
        if not form.data.get("club_name") or form.data.get("club"):
            return

        from footycollect.core.models import Club

        try:
            club = Club.objects.get(name=form.data["club_name"])
            self._update_club_country(club)
            form.data["club"] = club.id
        except Club.DoesNotExist:
            club = self._create_club_from_api_data(form)
            form.data["club"] = club.id

    def _fill_brand_field(self, form):
        """Fill brand field from API data."""
        if not form.data.get("brand_name") or form.data.get("brand"):
            return

        from footycollect.core.models import Brand

        slug = form.data["brand_name"].lower().replace(" ", "-")
        brand = Brand.objects.filter(slug=slug).first()
        if not brand:
            brand = Brand.objects.filter(name__iexact=form.data["brand_name"]).first()
        if not brand:
            brand = Brand.objects.create(
                name=form.data["brand_name"],
                slug=slug,
            )
        form.data["brand"] = brand.id

    def _fill_season_field(self, form):
        """Fill season field from API data."""
        if not form.data.get("season_name") or form.data.get("season"):
            return

        from footycollect.core.models import Season

        try:
            season = Season.objects.get(year=form.data["season_name"])
            form.data["season"] = season.id
        except Season.DoesNotExist:
            season = Season.objects.create(
                year=form.data["season_name"],
                first_year=form.data["season_name"].split("-")[0],
                second_year=form.data["season_name"].split("-")[1] if "-" in form.data["season_name"] else "",
            )
            form.data["season"] = season.id

    def _ensure_country_in_cleaned_data(self, cleaned_data, country_code_post, form):
        """Ensure country_code is in cleaned_data."""
        if not cleaned_data.get("country_code"):
            if country_code_post:
                cleaned_data["country_code"] = country_code_post
                logger.info("Set country_code in cleaned_data from POST: %s", country_code_post)
            elif form.data.get("country_code"):
                cleaned_data["country_code"] = form.data.get("country_code")
                logger.info("Set country_code in cleaned_data from form.data: %s", form.data.get("country_code"))
            elif hasattr(self, "fkapi_data") and "team_country" in self.fkapi_data:
                cleaned_data["country_code"] = self.fkapi_data["team_country"]
                logger.info("Set country_code in cleaned_data from fkapi_data: %s", self.fkapi_data["team_country"])
