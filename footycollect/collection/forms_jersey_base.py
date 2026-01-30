from dal import autocomplete
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django_countries import countries

from footycollect.collection.form_fields import (
    ColorModelChoiceField,
    ColorModelMultipleChoiceField,
)
from footycollect.collection.models import BaseItem, Color, Jersey, Size

YEAR_LENGTH = 4


class JerseyForm(forms.ModelForm):
    """Form for Jersey items using Service Layer with STI structure."""

    class Meta:
        model = BaseItem
        fields = [
            "name",
            "condition",
            "description",
            "main_color",
            "secondary_colors",
        ]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)

        if "instance" not in kwargs:
            kwargs["instance"] = BaseItem()
        super().__init__(*args, **kwargs)

        instance = self.instance
        if instance is not None and instance.pk:
            self.fields["name"].initial = instance.name
            self.fields["condition"].initial = instance.condition
            self.fields["detailed_condition"].initial = instance.detailed_condition
            self.fields["description"].initial = instance.description
            self.fields["is_replica"].initial = instance.is_replica
            self.fields["main_color"].initial = instance.main_color_id
            self.fields["secondary_colors"].initial = list(
                instance.secondary_colors.values_list("id", flat=True),
            )
            self.fields["design"].initial = instance.design
            if instance.country:
                self.fields["country_code"].initial = instance.country

            if instance.brand_id:
                self.fields["brand"].initial = instance.brand_id
                self.fields["brand_name"].initial = getattr(instance.brand, "name", "")

            if instance.club_id:
                self.fields["club"].initial = instance.club_id
                self.fields["club_name"].initial = getattr(instance.club, "name", "")

            if instance.season_id:
                self.fields["season"].initial = instance.season_id
                self.fields["season_name"].initial = getattr(instance.season, "name", "")

            competition_ids = list(instance.competitions.values_list("id", flat=True))
            if competition_ids:
                self.fields["competitions"].initial = ",".join(str(cid) for cid in competition_ids)

            jersey = getattr(instance, "jersey", None)
            if jersey is not None:
                self.fields["size"].initial = jersey.size_id
                self.fields["is_fan_version"].initial = jersey.is_fan_version
                self.fields["is_signed"].initial = jersey.is_signed
                self.fields["has_nameset"].initial = jersey.has_nameset
                self.fields["player_name"].initial = jersey.player_name
                self.fields["is_short_sleeve"].initial = jersey.is_short_sleeve
                self.fields["number"].initial = jersey.number

    size = forms.ModelChoiceField(
        queryset=Size.objects.all(),
        label=_("Size"),
        required=True,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    brand = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput(),
    )

    brand_name = forms.CharField(required=False, widget=forms.HiddenInput())

    competitions = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
    )

    competition_name = forms.CharField(required=False, widget=forms.HiddenInput())

    club = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput(),
    )

    club_name = forms.CharField(required=False, widget=forms.HiddenInput())

    season = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput(),
    )

    season_name = forms.CharField(required=False, widget=forms.HiddenInput())

    condition = forms.IntegerField(
        min_value=1,
        max_value=10,
        initial=10,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )

    detailed_condition = forms.ChoiceField(
        choices=BaseItem.CONDITION_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
    )

    is_replica = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input toggle-switch"}),
    )

    main_color = ColorModelChoiceField(
        queryset=Color.objects.all(),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    secondary_colors = ColorModelMultipleChoiceField(
        queryset=Color.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "form-select"}),
    )

    design = forms.ChoiceField(
        choices=BaseItem.DESIGN_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    country_code = forms.ChoiceField(
        choices=countries,
        label=_("Country"),
        required=False,
        widget=autocomplete.Select2(
            url="core:country-autocomplete",
            attrs={
                "data-html": True,
                "data-placeholder": _("Select a country..."),
                "class": "form-control select2",
                "data-theme": "bootstrap-5",
                "data-allow-clear": "true",
                "data-minimum-input-length": 0,
                "data-debug": "true",
            },
        ),
    )

    is_fan_version = forms.BooleanField(
        required=False,
        label=_("Fan Version"),
        widget=forms.CheckboxInput(attrs={"class": "form-check-input toggle-switch"}),
    )

    is_signed = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input toggle-switch"}),
    )

    has_nameset = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input toggle-switch"}),
    )

    player_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    is_short_sleeve = forms.BooleanField(
        required=False,
        initial=True,
        label=_("Short Sleeve"),
        widget=forms.CheckboxInput(attrs={"class": "form-check-input toggle-switch"}),
    )

    number = forms.IntegerField(
        min_value=0,
        max_value=99,
        required=False,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )

    def clean_main_color(self):
        """Normalize main color from string name to Color object."""
        main_color_name = self.data.get("main_color")
        if not main_color_name:
            return self.cleaned_data.get("main_color")

        if isinstance(main_color_name, Color):
            return main_color_name

        try:
            color_id = int(main_color_name)
            return Color.objects.get(id=color_id)
        except (ValueError, TypeError, Color.DoesNotExist):
            pass

        color_obj, _ = Color.objects.get_or_create(
            name__iexact=main_color_name.strip(),
            defaults={"name": main_color_name.strip().upper()},
        )
        return color_obj

    def clean_secondary_colors(self):
        """Normalize secondary colors from string names to Color objects."""
        if hasattr(self.data, "getlist"):
            secondary_colors_names = self.data.getlist("secondary_colors")
        else:
            secondary_colors = self.data.get("secondary_colors")
            if secondary_colors:
                secondary_colors_names = [secondary_colors] if isinstance(secondary_colors, str) else secondary_colors
            else:
                secondary_colors_names = []

        if not secondary_colors_names:
            return []

        color_objects = []
        for color_name in secondary_colors_names:
            if not color_name:
                continue

            if isinstance(color_name, Color):
                color_objects.append(color_name)
                continue

            try:
                color_id = int(color_name)
                color_obj = Color.objects.get(id=color_id)
                color_objects.append(color_obj)
                continue
            except (ValueError, TypeError, Color.DoesNotExist):
                pass

            color_obj, _ = Color.objects.get_or_create(
                name__iexact=color_name.strip(),
                defaults={"name": color_name.strip().upper()},
            )
            color_objects.append(color_obj)

        return color_objects

    def clean(self):
        """Custom validation for the form."""
        cleaned_data = super().clean()

        brand_id = cleaned_data.get("brand")
        brand_name = self.data.get("brand_name")

        if not brand_id and not brand_name:
            raise forms.ValidationError({"brand": _("Please select a brand or provide a brand name.")})

        return cleaned_data

    def _resolve_brand(self):
        """Resolve or create brand from cleaned_data and request data."""
        import contextlib
        import logging

        from django.utils.text import slugify

        from footycollect.core.models import Brand

        logger = logging.getLogger(__name__)

        brand = None
        brand_id = self.cleaned_data.get("brand")
        if brand_id:
            with contextlib.suppress(Brand.DoesNotExist):
                brand = Brand.objects.get(id=brand_id)
                logger.info("Found brand by ID: %s", brand_id)

        if not brand and self.data.get("brand_name"):
            brand_name = self.data.get("brand_name")
            logger.info("Creating brand from name: %s", brand_name)
            try:
                brand, created = Brand.objects.get_or_create(
                    name=brand_name,
                    defaults={"slug": slugify(brand_name)},
                )
                if created:
                    logger.info("Created new brand: %s", brand_name)
                else:
                    logger.info("Found existing brand: %s", brand_name)
            except (ValueError, TypeError):
                logger.exception("Error creating brand %s", brand_name)
                brand = None

        if not brand:
            raise ValidationError(_("Brand could not be resolved. Please try again."))
        return brand

    def _resolve_club(self):
        """Resolve or create club from cleaned_data and request data."""
        import contextlib
        import logging

        from django.utils.text import slugify

        from footycollect.core.models import Club

        logger = logging.getLogger(__name__)

        club = None
        club_id = self.cleaned_data.get("club")
        if club_id:
            with contextlib.suppress(Club.DoesNotExist):
                club = Club.objects.get(id=club_id)
                logger.info("Found club by ID: %s", club_id)

        if not club and self.data.get("club_name"):
            club_name = self.data.get("club_name")
            logger.info("Creating club from name: %s", club_name)
            try:
                club, created = Club.objects.get_or_create(
                    name=club_name,
                    defaults={"slug": slugify(club_name)},
                )
                if created:
                    logger.info("Created new club: %s", club_name)
                else:
                    logger.info("Found existing club: %s", club_name)
            except (ValueError, TypeError):
                logger.exception("Error creating club %s", club_name)
                club = None

        if not club:
            raise ValidationError(_("Club could not be resolved. Please try again."))
        return club

    def _resolve_season(self):
        """Resolve or create season from cleaned_data and request data."""
        import contextlib
        import logging

        from footycollect.core.models import Season

        logger = logging.getLogger(__name__)

        season = None
        season_id = self.cleaned_data.get("season")
        if season_id:
            with contextlib.suppress(Season.DoesNotExist):
                season = Season.objects.get(id=season_id)
                logger.info("Found season by ID: %s", season_id)

        if not season and self.data.get("season_name"):
            season_name = self.data.get("season_name")
            logger.info("Creating season from year: %s", season_name)
            try:
                if "-" in season_name:
                    parts = season_name.split("-")
                    first_year = parts[0]
                    second_year = parts[1] if len(parts) > 1 else ""
                else:
                    first_year = season_name[:YEAR_LENGTH] if len(season_name) >= YEAR_LENGTH else season_name
                    second_year = ""

                season, created = Season.objects.get_or_create(
                    year=season_name,
                    defaults={
                        "first_year": first_year,
                        "second_year": second_year,
                    },
                )
                if created:
                    logger.info(
                        "Created new season: %s (year=%s, first=%s, second=%s)",
                        season_name,
                        season.year,
                        season.first_year,
                        season.second_year,
                    )
                else:
                    logger.info("Found existing season: %s (year=%s)", season_name, season.year)
            except (ValueError, TypeError):
                logger.exception("Error creating season %s", season_name)
                season = None

        if not season:
            raise ValidationError(_("Season could not be resolved. Please try again."))
        return season

    def _extract_base_item_data(self):
        """Extract data for BaseItem creation."""
        brand = self._resolve_brand()
        club = self._resolve_club()
        season = self._resolve_season()

        base_data = {
            "name": self.cleaned_data.get("name", ""),
            "club": club,
            "season": season,
            "brand": brand,
            "condition": self.cleaned_data.get("condition"),
            "detailed_condition": self.cleaned_data.get("detailed_condition"),
            "is_replica": self.cleaned_data.get("is_replica", False),
            "description": self.cleaned_data.get("description", ""),
            "main_color": self.cleaned_data.get("main_color"),
            "design": self.cleaned_data.get("design"),
            "user": self.user,
            "item_type": "jersey",
        }

        country_code = self.cleaned_data.get("country_code")

        if country_code:
            try:
                base_data["country"] = self._convert_country_code(country_code, club)
            except (ValueError, AttributeError, KeyError, TypeError) as e:
                import logging

                logger = logging.getLogger(__name__)
                logger.warning("Error converting country_code %s: %s", country_code, str(e))
                if club and club.country:
                    base_data["country"] = club.country
        elif hasattr(self.instance, "country") and self.instance.country:
            base_data["country"] = self.instance.country
        elif club and club.country:
            base_data["country"] = club.country

        return base_data

    def _convert_country_code(self, country_code, club):
        """Convert country_code string to Country object."""
        if isinstance(country_code, str):
            if country_code.upper() in countries:
                return country_code.upper()
            if club and club.country:
                return club.country
        return country_code

    def _extract_jersey_data(self):
        """Extract data for Jersey creation."""
        return {
            "size": self.cleaned_data.get("size"),
            "is_fan_version": self.cleaned_data.get("is_fan_version", False),
            "is_signed": self.cleaned_data.get("is_signed", False),
            "has_nameset": self.cleaned_data.get("has_nameset", False),
            "player_name": self.cleaned_data.get("player_name", ""),
            "is_short_sleeve": self.cleaned_data.get("is_short_sleeve", False),
            "number": self.cleaned_data.get("number", ""),
        }

    def _extract_many_to_many_data(self):
        """Extract ManyToMany field data."""
        import logging

        from footycollect.core.models import Competition

        logger = logging.getLogger(__name__)
        competitions = []
        competitions_data = self.cleaned_data.get("competitions", "")
        logger.debug(
            "_extract_many_to_many_data - competitions_data: %s (type: %s)",
            competitions_data,
            type(competitions_data),
        )

        if competitions_data:
            if isinstance(competitions_data, str):
                competition_ids = [
                    int(comp_id.strip()) for comp_id in competitions_data.split(",") if comp_id.strip().isdigit()
                ]
                logger.debug("_extract_many_to_many_data - parsed competition_ids from string: %s", competition_ids)
            elif isinstance(competitions_data, list):
                competition_ids = [int(comp_id) for comp_id in competitions_data if comp_id]
                logger.debug("_extract_many_to_many_data - parsed competition_ids from list: %s", competition_ids)
            else:
                competition_ids = [competitions_data] if competitions_data else []
                logger.debug("_extract_many_to_many_data - parsed competition_ids from other: %s", competition_ids)

            if competition_ids:
                competitions = Competition.objects.filter(id__in=competition_ids)
                logger.info(
                    "_extract_many_to_many_data - found competitions: %s (count: %s)",
                    [c.name for c in competitions],
                    competitions.count(),
                )
            else:
                logger.warning(
                    "_extract_many_to_many_data - no valid competition_ids extracted from: %s",
                    competitions_data,
                )

        return {
            "competitions": competitions,
        }

    def save(self, *, commit=True):
        """
        Save the form data using MTI structure.

        - If instance has a primary key, update the existing BaseItem + Jersey.
        - If not, create a new BaseItem + Jersey pair.
        """
        if self.instance is not None and self.instance.pk:
            return self._update_existing_item(commit=commit)

        return self._create_new_item(commit=commit)

    def _update_existing_item(self, *, commit):
        """Update an existing BaseItem and its related Jersey."""
        base_item = self.instance

        brand = self._resolve_brand()
        club = self._resolve_club()
        season = self._resolve_season()

        base_item.name = self.cleaned_data.get("name", base_item.name)
        base_item.brand = brand
        base_item.club = club
        base_item.season = season
        base_item.condition = self.cleaned_data.get("condition", base_item.condition)
        base_item.detailed_condition = self.cleaned_data.get(
            "detailed_condition",
            base_item.detailed_condition,
        )
        base_item.description = self.cleaned_data.get("description", base_item.description)
        base_item.is_replica = self.cleaned_data.get("is_replica", base_item.is_replica)
        base_item.main_color = self.cleaned_data.get("main_color", base_item.main_color)
        base_item.design = self.cleaned_data.get("design", base_item.design)

        country_code = self.cleaned_data.get("country_code")
        if country_code:
            base_item.country = country_code

        if commit:
            base_item.save()
            self._update_many_to_many_relations(base_item)
            self._update_jersey_fields(base_item)

        return base_item

    def _update_many_to_many_relations(self, base_item):
        """Update ManyToMany relations for competitions and secondary colors."""
        many_to_many_data = self._extract_many_to_many_data()
        if many_to_many_data.get("competitions"):
            base_item.competitions.set(many_to_many_data["competitions"])

        secondary_colors = self.cleaned_data.get("secondary_colors", [])
        if secondary_colors:
            base_item.secondary_colors.set(secondary_colors)
        else:
            base_item.secondary_colors.clear()

    def _update_jersey_fields(self, base_item):
        """Update Jersey-specific fields."""
        jersey = getattr(base_item, "jersey", None)
        if jersey is None:
            return

        jersey.size = self.cleaned_data.get("size", jersey.size)
        jersey.is_fan_version = self.cleaned_data.get("is_fan_version", jersey.is_fan_version)
        jersey.is_signed = self.cleaned_data.get("is_signed", jersey.is_signed)
        jersey.has_nameset = self.cleaned_data.get("has_nameset", jersey.has_nameset)
        jersey.player_name = self.cleaned_data.get("player_name", jersey.player_name)
        jersey.is_short_sleeve = self.cleaned_data.get("is_short_sleeve", jersey.is_short_sleeve)
        jersey.number = self.cleaned_data.get("number", jersey.number)
        jersey.save()

    def _create_new_item(self, *, commit):
        """Create a new BaseItem and Jersey pair."""
        import logging

        logger = logging.getLogger(__name__)

        base_item_data = self._extract_base_item_data()
        jersey_data = self._extract_jersey_data()
        many_to_many_data = self._extract_many_to_many_data()

        if not commit:
            base_item = BaseItem(**base_item_data)
            jersey_data["base_item"] = base_item
            return Jersey(**jersey_data)

        logger.debug("Creating BaseItem with data: %s", base_item_data)
        base_item = BaseItem.objects.create(**base_item_data)
        logger.debug("Created BaseItem %s", base_item.id)

        jersey_data.pop("id", None)
        logger.debug("Creating Jersey with base_item=%s", base_item.id)
        jersey = Jersey.objects.create(base_item=base_item, **jersey_data)
        logger.debug("Created Jersey %s", jersey.pk)

        if jersey.base_item.id != base_item.id:
            logger.error("ERROR: Jersey %s not linked to BaseItem %s", jersey.pk, base_item.id)

        self._set_many_to_many_on_create(base_item, many_to_many_data, logger)

        try:
            self._create_kit_for_jersey(base_item, jersey)
        except (ValueError, TypeError, AttributeError):
            logger.exception("Error creating Kit")

        return base_item

    def _set_many_to_many_on_create(self, base_item, many_to_many_data, logger):
        """Set ManyToMany relations when creating a new item."""
        if many_to_many_data.get("competitions"):
            competitions_list = many_to_many_data["competitions"]
            base_item.competitions.set(competitions_list)
            logger.info(
                "Set competitions on BaseItem %s: %s (count: %s)",
                base_item.id,
                [c.name for c in competitions_list],
                len(competitions_list),
            )

        secondary_colors = self.cleaned_data.get("secondary_colors", [])
        if secondary_colors:
            base_item.secondary_colors.set(secondary_colors)
            logger.debug("Set secondary_colors: %s", [c.name for c in secondary_colors])

    def _create_kit_for_jersey(self, base_item, jersey):
        """Create and link Kit to jersey."""
        import logging

        from footycollect.collection.services.kit_service import KitService

        logger = logging.getLogger(__name__)
        kit_service = KitService()
        kit_id = self.cleaned_data.get("kit_id")
        fkapi_data = getattr(self, "fkapi_data", {})

        kit = kit_service.get_or_create_kit_for_jersey(
            base_item=base_item,
            jersey=jersey,
            fkapi_data=fkapi_data,
            kit_id=kit_id,
        )

        jersey.kit = kit
        jersey.save()
        logger.info("Successfully created/linked Kit %s to Jersey %s", kit.id, jersey.pk)


__all__ = [
    "JerseyForm",
    "YEAR_LENGTH",
]
