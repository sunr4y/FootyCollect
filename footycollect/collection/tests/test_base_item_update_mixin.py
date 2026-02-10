from unittest.mock import MagicMock

from django.test import TestCase

from footycollect.collection.factories import BaseItemFactory
from footycollect.collection.models import Color
from footycollect.collection.views.jersey.mixins.base_item_update_mixin import BaseItemUpdateMixin


class TestBaseItemUpdateMixin(TestCase):
    def setUp(self):
        class TestView(BaseItemUpdateMixin):
            pass

        self.view = TestView()

    def test_update_base_item_country_skips_when_already_set(self):
        base_item = BaseItemFactory(country="ES")
        form = MagicMock()
        form.cleaned_data = {"country_code": "FR"}

        changed = self.view._update_base_item_country(base_item, country_code_post="DE", form=form)

        assert changed is False
        assert base_item.country == "ES"

    def test_update_base_item_country_prefers_post_then_form_then_fkapi(self):
        base_item = BaseItemFactory(country=None)
        form = MagicMock()
        form.cleaned_data = {"country_code": "FR"}

        self.view.fkapi_data = {"team_country": "PT"}

        changed = self.view._update_base_item_country(base_item, country_code_post="DE", form=form)
        assert changed is True
        assert base_item.country == "DE"

        base_item.country = None
        changed = self.view._update_base_item_country(base_item, country_code_post="", form=form)
        assert changed is True
        assert base_item.country == "FR"

        base_item.country = None
        form.cleaned_data["country_code"] = ""
        changed = self.view._update_base_item_country(base_item, country_code_post="", form=form)
        assert changed is True
        assert base_item.country == "PT"

    def test_update_base_item_main_color_uses_cleaned_data_or_creates_from_post(self):
        base_item = BaseItemFactory(main_color=None)
        existing_color = Color.objects.create(name="RED")
        form = MagicMock()
        form.cleaned_data = {"main_color": existing_color}

        changed = self.view._update_base_item_main_color(
            base_item,
            main_color_post="BLUE",
            form=form,
        )
        assert changed is True
        assert base_item.main_color == existing_color

        base_item.main_color = None
        form.cleaned_data["main_color"] = None

        changed = self.view._update_base_item_main_color(
            base_item,
            main_color_post="blue",
            form=form,
        )
        assert changed is True
        assert base_item.main_color is not None
        assert base_item.main_color.name == "BLUE"

    def test_process_secondary_colors_from_post_handles_string_and_list(self):
        result = self.view._process_secondary_colors_from_post("red, blue ,  ,")
        names = sorted(c.name for c in result)
        assert names == ["BLUE", "RED"]

        result = self.view._process_secondary_colors_from_post(["green", "Green"])
        names = sorted(c.name for c in result)
        assert names == ["GREEN", "GREEN"]

        result = self.view._process_secondary_colors_from_post(None)
        assert result == []

    def test_update_base_item_secondary_colors_uses_cleaned_data_or_post(self):
        base_item = BaseItemFactory()

        color1 = Color.objects.create(name="YELLOW")
        color2 = Color.objects.create(name="BLACK")

        form = MagicMock()
        form.cleaned_data = {"secondary_colors": [color1, color2]}

        changed = self.view._update_base_item_secondary_colors(
            base_item,
            secondary_colors_post=None,
            form=form,
        )
        assert changed is True
        assert list(base_item.secondary_colors.order_by("name")) == [color2, color1]

        base_item.secondary_colors.clear()
        form.cleaned_data["secondary_colors"] = []

        changed = self.view._update_base_item_secondary_colors(
            base_item,
            secondary_colors_post="red, blue",
            form=form,
        )
        assert changed is True
        names = sorted(c.name for c in base_item.secondary_colors.all())
        assert names == ["BLUE", "RED"]
