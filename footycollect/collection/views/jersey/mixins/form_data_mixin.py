"""
Mixin for handling form data manipulation and validation.

This mixin provides methods to fill form fields, set initial values,
and ensure cleaned_data contains required fields.
"""

import logging

from footycollect.collection.models import Color

logger = logging.getLogger(__name__)


class FormDataMixin:
    """
    Mixin for form data manipulation functionality.

    Note: This mixin may depend on EntityProcessingMixin for
    _update_club_country and _create_club_from_api_data methods.
    """

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
                logger.debug("Converted main_color name '%s' to ID %s", main_color_value, color_obj.id)
            except Color.DoesNotExist:
                logger.warning("Main color '%s' not found in database", main_color_value)
        else:
            form.fields["main_color"].initial = main_color_value
            logger.debug("Set main_color initial to ID: %s", main_color_value)

    def _set_secondary_colors_initial(self, form):
        """Convert secondary_colors names to IDs for template."""
        if hasattr(form.data, "getlist"):
            secondary_colors_value = form.data.getlist("secondary_colors")
        else:
            secondary_colors_value = form.data.get("secondary_colors")
            if secondary_colors_value and not isinstance(secondary_colors_value, list):
                secondary_colors_value = [secondary_colors_value]

        if not secondary_colors_value:
            return

        color_ids = []
        for color_val in secondary_colors_value:
            if not color_val:
                continue
            if isinstance(color_val, str) and not color_val.isdigit():
                try:
                    color_obj = Color.objects.get(name__iexact=color_val.strip())
                    color_ids.append(color_obj.id)
                    logger.debug("Converted secondary_color name '%s' to ID %s", color_val, color_obj.id)
                except Color.DoesNotExist:
                    logger.warning("Secondary color '%s' not found in database", color_val)
            else:
                color_ids.append(color_val)

        if color_ids:
            form.fields["secondary_colors"].initial = color_ids
            logger.debug("Set secondary_colors initial to: %s", color_ids)

    def _ensure_country_code_in_cleaned_data(self, form):
        """Ensure country_code is in cleaned_data."""
        country_code = form.cleaned_data.get("country_code")
        if not country_code:
            if form.data.get("country_code"):
                country_code = form.data.get("country_code")
                form.cleaned_data["country_code"] = country_code
                logger.info("Set country_code in cleaned_data from form.data: %s", country_code)
            elif hasattr(self, "fkapi_data") and "team_country" in self.fkapi_data:
                country_code = self.fkapi_data["team_country"]
                form.cleaned_data["country_code"] = country_code
                logger.info("Set country_code in cleaned_data from fkapi_data: %s", country_code)

    def _ensure_main_color_in_cleaned_data(self, form):
        """Ensure main_color is in cleaned_data."""
        main_color = form.cleaned_data.get("main_color")
        if not main_color and form.data.get("main_color"):
            main_color_str = form.data.get("main_color")
            if main_color_str:
                color_obj, _created = Color.objects.get_or_create(
                    name__iexact=main_color_str.strip(),
                    defaults={"name": main_color_str.strip().upper()},
                )
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
            if hasattr(form.data, "getlist"):
                secondary_colors_raw = form.data.getlist("secondary_colors")
            else:
                secondary_colors_raw = form.data.get("secondary_colors", [])
                if isinstance(secondary_colors_raw, str):
                    secondary_colors_raw = [c.strip() for c in secondary_colors_raw.split(",") if c.strip()]
                elif not isinstance(secondary_colors_raw, list):
                    secondary_colors_raw = []

            if secondary_colors_raw:
                color_objects = []
                for color_str in secondary_colors_raw:
                    if isinstance(color_str, str) and color_str.strip():
                        color_obj, _created = Color.objects.get_or_create(
                            name__iexact=color_str.strip(),
                            defaults={"name": color_str.strip().upper()},
                        )
                        color_objects.append(color_obj)
                if color_objects:
                    form.cleaned_data["secondary_colors"] = color_objects
                    logger.info(
                        "Set secondary_colors in cleaned_data from form.data: %s",
                        [c.name for c in color_objects],
                    )

    def _ensure_form_cleaned_data(self, form):
        """Ensure country_code and colors are in cleaned_data before processing."""
        self._ensure_country_code_in_cleaned_data(form)
        self._ensure_main_color_in_cleaned_data(form)
        self._ensure_secondary_colors_in_cleaned_data(form)

    def _fill_form_with_api_data(self, form):
        """Fill form fields with API data. Makes form.data mutable and sets name if needed."""
        try:
            form.data = form.data.copy()
        except AttributeError:
            form.data = dict(form.data)

        if not form.data.get("name") and form.instance.name:
            form.data["name"] = form.instance.name

        self._fill_club_field(form)
        self._fill_brand_field(form)
        self._fill_season_field(form)

    def _setup_form_instance(self, form):
        """Set up form instance for jersey creation (STI)."""
        from footycollect.collection.models import BaseItem

        if form.instance is None:
            if hasattr(form, "_meta") and form._meta is not None and hasattr(form._meta, "model"):
                form.instance = form._meta.model()
            else:
                form.instance = BaseItem()

        form.instance.item_type = "jersey"

        if not form.instance.name:
            name = form.data.get("name")
            if not name:
                club_name = form.data.get("club_name", "")
                season_name = form.data.get("season_name", "")
                if club_name and season_name:
                    form.instance.name = f"{club_name} {season_name}"
                else:
                    form.instance.name = "Jersey"
            else:
                form.instance.name = name

        if not form.data.get("name") and form.instance.name:
            try:
                form.data = form.data.copy()
            except AttributeError:
                form.data = dict(form.data)
            form.data["name"] = form.instance.name

        if hasattr(self, "request") and self.request and hasattr(self.request, "user"):
            form.instance.user = self.request.user

        if form.data.get("country_code"):
            form.instance.country = form.data["country_code"]
            logger.info("Set country to %s", form.data["country_code"])

    def _preprocess_form_data(self, form):
        """Set up form instance, process kit data if kit_id present, then fill from API."""
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

        try:
            brand = Brand.objects.get(name=form.data["brand_name"])
            form.data["brand"] = brand.id
        except Brand.DoesNotExist:
            slug = form.data["brand_name"].lower().replace(" ", "-")
            try:
                brand = Brand.objects.get(slug=slug)
                form.data["brand"] = brand.id
            except Brand.DoesNotExist:
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
