"""
Tests for KitService.
"""

from unittest.mock import MagicMock, patch

from django.test import TestCase

from footycollect.collection.factories import (
    BaseItemFactory,
    BrandFactory,
    ClubFactory,
    CompetitionFactory,
    JerseyFactory,
    SeasonFactory,
)
from footycollect.collection.models import BaseItem
from footycollect.collection.services.kit_service import KitService
from footycollect.core.models import Kit, TypeK


class TestKitServiceGetOrCreateKitForJersey(TestCase):
    def setUp(self):
        self.service = KitService()
        self.brand = BrandFactory(name="Nike", slug="nike")
        self.club = ClubFactory(name="Barcelona", slug="barcelona")
        self.season = SeasonFactory(year="2023-24", first_year="2023", second_year="2024")
        self.base_item = BaseItemFactory(
            brand=self.brand,
            club=self.club,
            season=self.season,
            name="Nike Barcelona 2023-24",
        )
        self.jersey = JerseyFactory(base_item=self.base_item)

    def test_get_or_create_kit_creates_new_kit_without_fkapi_data(self):
        kit = self.service.get_or_create_kit_for_jersey(self.base_item, self.jersey)
        assert isinstance(kit, Kit)
        assert kit.name == "Nike Barcelona 2023-24"
        assert kit.team == self.club
        assert kit.season == self.season
        assert kit.brand == self.brand
        assert kit.slug

    def test_get_or_create_kit_with_same_kit_id_returns_existing_kit(self):
        kit_id = "99999"
        kit1 = self.service.get_or_create_kit_for_jersey(self.base_item, self.jersey, kit_id=kit_id)
        kit2 = self.service.get_or_create_kit_for_jersey(self.base_item, self.jersey, kit_id=kit_id)
        assert kit1.id == kit2.id
        assert kit1.id_fka == int(kit_id)

    def test_get_or_create_kit_with_fkapi_data_uses_name_and_slug(self):
        fkapi_data = {"name": "FKAPI Kit Name", "slug": "fkapi-kit-slug"}
        kit = self.service.get_or_create_kit_for_jersey(self.base_item, self.jersey, fkapi_data=fkapi_data)
        assert kit.name == "FKAPI Kit Name"
        assert kit.slug == "fkapi-kit-slug"

    def test_get_or_create_kit_with_kit_id_returns_existing_kit_by_id_fka(self):
        existing_kit = Kit.objects.create(
            name="Existing",
            slug="existing-kit",
            id_fka=12345,
            team=self.club,
            season=self.season,
            brand=self.brand,
            main_img_url="https://example.com/img.png",
        )
        kit = self.service.get_or_create_kit_for_jersey(self.base_item, self.jersey, kit_id="12345")
        assert kit.id == existing_kit.id

    def test_get_or_create_kit_invalid_kit_id_creates_new_kit(self):
        kit = self.service.get_or_create_kit_for_jersey(self.base_item, self.jersey, kit_id="not-a-number")
        assert isinstance(kit, Kit)
        assert kit.id_fka is None

    def test_get_or_create_kit_sets_competitions_from_base_item(self):
        comp = CompetitionFactory()
        self.base_item.competitions.add(comp)
        kit = self.service.get_or_create_kit_for_jersey(self.base_item, self.jersey)
        assert kit.competition.filter(id=comp.id).exists()

    def test_get_or_create_kit_existing_kit_updates_image_when_default(self):
        Kit.objects.create(
            name="Existing",
            slug="nike-barcelona-2023-24",
            id_fka=None,
            team=self.club,
            season=self.season,
            brand=self.brand,
            main_img_url="https://www.footballkitarchive.com/static/logos/not_found.png",
        )
        fkapi_data = {"main_img_url": "https://api.com/real.png"}
        kit = self.service.get_or_create_kit_for_jersey(self.base_item, self.jersey, fkapi_data=fkapi_data)
        kit.refresh_from_db()
        assert kit.main_img_url == "https://api.com/real.png"

    def test_get_or_create_kit_found_existing_by_slug_runs_update_image_path(self):
        existing = Kit.objects.create(
            name="Existing",
            slug="nike-barcelona-2023-24",
            id_fka=None,
            team=self.club,
            season=self.season,
            brand=self.brand,
            main_img_url="https://www.footballkitarchive.com/static/logos/not_found.png",
        )
        fkapi_data = {"main_img_url": "https://new.com/img.png"}
        with patch.object(Kit.objects, "get_or_create", return_value=(existing, False)):
            kit = self.service.get_or_create_kit_for_jersey(self.base_item, self.jersey, fkapi_data=fkapi_data)
        assert kit.id == existing.id
        existing.refresh_from_db()
        assert existing.main_img_url == "https://new.com/img.png"


class TestKitServiceBuildKitName(TestCase):
    def setUp(self):
        self.service = KitService()
        self.brand = BrandFactory(name="Adidas", slug="adidas")
        self.club = ClubFactory(name="Real Madrid", slug="real-madrid")
        self.season = SeasonFactory(year="2024-25", first_year="2024", second_year="2025")
        self.base_item = BaseItemFactory(brand=self.brand, club=self.club, season=self.season, name="Item")

    def test_build_kit_name_from_fkapi_data(self):
        name = self.service._build_kit_name(self.base_item, {"name": "API Name"})
        assert name == "API Name"

    def test_build_kit_name_fallback_from_base_item(self):
        name = self.service._build_kit_name(self.base_item, {})
        assert "Adidas" in name
        assert "Real Madrid" in name
        assert "2024" in name

    def test_build_kit_name_fallback_no_brand_club_season(self):
        base = MagicMock(spec=BaseItem)
        base.name = "Solo Item"
        base.brand = None
        base.club = None
        base.season = None
        name = self.service._build_kit_name(base, {})
        assert name == "Kit for Solo Item"


class TestKitServiceBuildKitSlug(TestCase):
    def setUp(self):
        self.service = KitService()
        self.base_item = BaseItemFactory(name="Test Item")

    def test_build_kit_slug_from_fkapi_data(self):
        slug = self.service._build_kit_slug(self.base_item, "Some Name", {"slug": "custom-slug"})
        assert slug == "custom-slug"

    def test_build_kit_slug_from_kit_name(self):
        slug = self.service._build_kit_slug(self.base_item, "Nike Barcelona 2024", {})
        assert slug == "nike-barcelona-2024"

    def test_build_kit_slug_collision_uses_counter(self):
        Kit.objects.create(
            name="x",
            slug="nike-barcelona-2024",
            main_img_url="https://example.com/x.png",
        )
        slug = self.service._build_kit_slug(self.base_item, "Nike Barcelona 2024", {})
        assert slug == "nike-barcelona-2024-1"

    def test_build_kit_slug_empty_kit_name_uses_base_item_name(self):
        slug = self.service._build_kit_slug(self.base_item, "---", {})
        assert slug == "test-item"


class TestKitServiceExtractTypeInfo(TestCase):
    def setUp(self):
        self.service = KitService()

    def test_extract_type_info_none_when_no_type(self):
        assert self.service._extract_type_info({}) is None

    def test_extract_type_info_string_type(self):
        result = self.service._extract_type_info({"type": "Home"})
        assert result == ("Home", {})

    def test_extract_type_info_dict_type(self):
        result = self.service._extract_type_info({"type": {"name": "Away", "category": "match"}})
        assert result[0] == "Away"
        assert result[1]["category"] == "match"

    def test_extract_type_info_dict_without_name_returns_none(self):
        assert self.service._extract_type_info({"type": {"category": "match"}}) is None


class TestKitServiceGetOrCreateTypeK(TestCase):
    def setUp(self):
        self.service = KitService()
        self.base_item = BaseItemFactory()

    def test_get_or_create_type_k_returns_none_when_no_type_info(self):
        result = self.service._get_or_create_type_k(self.base_item, {})
        assert result is None

    def test_get_or_create_type_k_skips_jacket(self):
        result = self.service._get_or_create_type_k(self.base_item, {"type": {"name": "Jacket", "category": "jacket"}})
        assert result is None

    def test_get_or_create_type_k_creates_new_type_k(self):
        result = self.service._get_or_create_type_k(self.base_item, {"type": {"name": "Third", "category": "match"}})
        assert isinstance(result, TypeK)
        assert result.name == "Third"
        assert result.category == "match"

    def test_get_or_create_type_k_returns_existing_type_k(self):
        TypeK.objects.create(name="Home", category="match")
        result = self.service._get_or_create_type_k(self.base_item, {"type": {"name": "Home", "category": "match"}})
        assert TypeK.objects.filter(name="Home").count() == 1
        assert result.name == "Home"

    def test_get_or_create_type_k_updates_existing_when_category_changes(self):
        TypeK.objects.create(name="Away", category="match", is_goalkeeper=False)
        result = self.service._get_or_create_type_k(
            self.base_item, {"type": {"name": "Away", "category": "training", "is_goalkeeper": True}}
        )
        type_k = TypeK.objects.get(name="Away")
        assert type_k.category == "training"
        assert type_k.is_goalkeeper is True
        assert result == type_k

    def test_get_or_create_type_k_string_type_creates_with_defaults(self):
        result = self.service._get_or_create_type_k(self.base_item, {"type": "Goalkeeper"})
        type_k = TypeK.objects.filter(name="Goalkeeper").first()
        assert type_k is not None
        assert type_k.category == "match"
        assert type_k.is_goalkeeper is False
        assert result == type_k

    def test_get_or_create_type_k_returns_none_when_create_raises(self):
        with patch.object(TypeK.objects, "create", side_effect=ValueError("bad")):
            result = self.service._get_or_create_type_k(
                self.base_item, {"type": {"name": "NewType", "category": "match"}}
            )
        assert result is None


class TestKitServiceUpdateExistingKitImage(TestCase):
    def setUp(self):
        self.service = KitService()
        self.brand = BrandFactory()
        self.club = ClubFactory()
        self.season = SeasonFactory()
        self.kit = Kit.objects.create(
            name="K",
            slug="k-slug",
            team=self.club,
            season=self.season,
            brand=self.brand,
            main_img_url="https://www.footballkitarchive.com/static/logos/not_found.png",
        )

    def test_update_existing_kit_image_sets_url_when_default(self):
        self.service._update_existing_kit_image(self.kit, "https://example.com/real.png")
        self.kit.refresh_from_db()
        assert self.kit.main_img_url == "https://example.com/real.png"

    def test_update_existing_kit_image_does_not_overwrite_good_url(self):
        self.kit.main_img_url = "https://example.com/good.png"
        self.kit.save(update_fields=["main_img_url"])
        self.service._update_existing_kit_image(self.kit, "https://example.com/other.png")
        self.kit.refresh_from_db()
        assert self.kit.main_img_url == "https://example.com/good.png"

    def test_update_existing_kit_image_skips_when_no_url_provided(self):
        original = self.kit.main_img_url
        self.service._update_existing_kit_image(self.kit, None)
        self.kit.refresh_from_db()
        assert self.kit.main_img_url == original

    def test_update_existing_kit_image_skips_when_empty_url(self):
        original = self.kit.main_img_url
        self.service._update_existing_kit_image(self.kit, "")
        self.kit.refresh_from_db()
        assert self.kit.main_img_url == original


class TestKitServiceGetMainImgUrl(TestCase):
    def setUp(self):
        self.service = KitService()
        self.base_item = BaseItemFactory()

    def test_get_main_img_url_from_fkapi_data(self):
        url = self.service._get_main_img_url(self.base_item, {"main_img_url": "https://api.com/img.png"})
        assert url == "https://api.com/img.png"

    def test_get_main_img_url_empty_when_no_fkapi_and_no_photos(self):
        url = self.service._get_main_img_url(self.base_item, {})
        assert url == ""

    def test_get_main_img_url_from_base_item_photos(self):
        mock_photo = MagicMock()
        mock_photo.get_image_url.return_value = "https://cdn.example.com/photo.jpg"
        mock_base = MagicMock()
        mock_base.photos.order_by.return_value.first.return_value = mock_photo
        url = self.service._get_main_img_url(mock_base, {})
        assert url == "https://cdn.example.com/photo.jpg"
