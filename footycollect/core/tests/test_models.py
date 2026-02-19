"""
Tests for core models.
"""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError


@pytest.mark.django_db
class TestSeasonModel:
    """Test Season model."""

    def test_season_creation(self):
        """Test creating a season."""
        from footycollect.core.models import Season

        season = Season.objects.create(
            year="2023-24",
            first_year="2023",
            second_year="24",
        )

        assert season.year == "2023-24"
        assert season.first_year == "2023"
        assert season.second_year == "24"
        assert str(season) == "2023-24"

    def test_season_str_representation(self):
        """Test season string representation."""
        from footycollect.core.models import Season

        season = Season.objects.create(
            year="2024-25",
            first_year="2024",
            second_year="2025",
        )
        assert str(season) == "2024-25"

    def test_season_unique_year(self):
        """Test season year uniqueness."""
        from footycollect.core.models import Season

        Season.objects.create(
            year="2023-24",
            first_year="2023",
            second_year="2024",
        )

        # Should raise IntegrityError for duplicate year
        with pytest.raises(IntegrityError):
            Season.objects.create(
                year="2023-24",
                first_year="2023",
                second_year="2024",
            )


@pytest.mark.django_db
class TestTypeKModel:
    """Test TypeK model."""

    def test_typek_creation(self):
        """Test creating a kit type."""
        from footycollect.core.models import TypeK

        typek = TypeK.objects.create(name="Home")

        assert typek.name == "Home"
        assert str(typek) == "Home"

    def test_typek_str_representation(self):
        """Test kit type string representation."""
        from footycollect.core.models import TypeK

        typek = TypeK.objects.create(name="Away")
        assert str(typek) == "Away"

    @pytest.mark.parametrize(
        ("category", "expected_name"),
        [
            ("match", "Game"),
            ("prematch", "Pre-match"),
            ("preseason", "Pre-season"),
            ("training", "Training"),
            ("travel", "Travel"),
        ],
    )
    def test_typek_get_category_display_name(self, category, expected_name):
        """Test TypeK get_category_display_name method."""
        from footycollect.core.models import TypeK

        typek = TypeK.objects.create(name="Test", category=category)
        display_name = typek.get_category_display_name()
        assert display_name == expected_name

    def test_typek_get_category_display_name_unknown_category(self):
        """Test TypeK get_category_display_name with unknown category."""
        from footycollect.core.models import TypeK

        typek = TypeK.objects.create(name="Test", category="unknown")
        display_name = typek.get_category_display_name()
        assert display_name == "unknown"

    def test_typek_is_goalkeeper_field(self):
        """Test TypeK is_goalkeeper field."""
        from footycollect.core.models import TypeK

        typek = TypeK.objects.create(name="GK Kit", is_goalkeeper=True)
        assert typek.is_goalkeeper is True

        typek_normal = TypeK.objects.create(name="Home", is_goalkeeper=False)
        assert typek_normal.is_goalkeeper is False


@pytest.mark.django_db
class TestCompetitionModel:
    """Test Competition model."""

    def test_competition_creation(self):
        """Test creating a competition."""
        from footycollect.core.models import Competition

        competition = Competition.objects.create(
            name="Champions League",
            slug="champions-league",
            logo="https://www.footballkitarchive.com/static/logos/not_found.png",
        )

        assert competition.name == "Champions League"
        assert competition.slug == "champions-league"
        assert competition.logo == "https://www.footballkitarchive.com/static/logos/not_found.png"
        assert str(competition) == "Champions League"

    def test_competition_str_representation(self):
        """Test competition string representation."""
        from footycollect.core.models import Competition

        competition = Competition.objects.create(
            name="Premier League",
            slug="premier-league",
        )
        assert str(competition) == "Premier League"

    def test_competition_unique_slug(self):
        """Test competition slug uniqueness."""
        from footycollect.core.models import Competition

        Competition.objects.create(
            name="La Liga",
            slug="la-liga",
        )

        # Should raise IntegrityError for duplicate slug
        with pytest.raises(IntegrityError):
            Competition.objects.create(
                name="Spanish League",
                slug="la-liga",
            )


@pytest.mark.django_db
class TestClubModel:
    """Test Club model."""

    def test_club_creation(self):
        """Test creating a club."""
        from footycollect.core.models import Club

        club = Club.objects.create(
            name="FC Barcelona",
            slug="fc-barcelona",
            country="ES",
            logo="https://www.footballkitarchive.com//static/logos/teams/6_l.png?v=1664834103&s=128",
        )

        assert club.name == "FC Barcelona"
        assert club.slug == "fc-barcelona"
        assert club.country == "ES"
        assert club.logo == "https://www.footballkitarchive.com//static/logos/teams/6_l.png?v=1664834103&s=128"
        assert str(club) == "FC Barcelona"

    def test_club_str_representation(self):
        """Test club string representation."""
        from footycollect.core.models import Club

        club = Club.objects.create(
            name="Real Madrid",
            slug="real-madrid",
            country="ES",
        )
        assert str(club) == "Real Madrid"

    def test_club_unique_slug(self):
        """Test club slug uniqueness."""
        from footycollect.core.models import Club

        Club.objects.create(
            name="Barcelona",
            slug="fc-barcelona",
            country="ES",
        )

        # Should raise IntegrityError for duplicate slug
        with pytest.raises(IntegrityError):
            Club.objects.create(
                name="FC Barcelona",
                slug="fc-barcelona",
                country="ES",
            )

    def test_club_slug_validation(self):
        """Test club slug validation with special characters."""
        from footycollect.core.models import Club

        # Valid slug with Nordic characters
        club = Club.objects.create(
            name="Stabæk JK",
            slug="stabaek-jk",
            country="NO",
        )
        assert club.slug == "stabaek-jk"

        # Invalid slug should raise ValidationError
        club = Club()
        club.name = "Test Club"
        club.slug = "invalid@slug!"
        club.country = "ES"

        with pytest.raises(ValidationError):
            club.full_clean()


@pytest.mark.django_db
class TestBrandModel:
    """Test Brand model."""

    def test_brand_creation(self):
        """Test creating a brand."""
        from footycollect.core.models import Brand

        brand = Brand.objects.create(
            name="Nike",
            slug="nike",
            logo="https://www.footballkitarchive.com/static/logos/misc/Nike.png",
        )

        assert brand.name == "Nike"
        assert brand.slug == "nike"
        assert brand.logo == "https://www.footballkitarchive.com/static/logos/misc/Nike.png"
        assert str(brand) == "Nike"

    def test_brand_str_representation(self):
        """Test brand string representation."""
        from footycollect.core.models import Brand

        brand = Brand.objects.create(
            name="Adidas",
            slug="adidas",
        )
        assert str(brand) == "Adidas"

    def test_brand_unique_slug(self):
        """Test brand slug uniqueness."""
        from footycollect.core.models import Brand

        Brand.objects.create(
            name="Nike",
            slug="nike",
        )

        # Should raise IntegrityError for duplicate slug
        with pytest.raises(IntegrityError):
            Brand.objects.create(
                name="Nike Sportswear",
                slug="nike",
            )


@pytest.mark.django_db
class TestKitModel:
    """Test Kit model."""

    def test_kit_creation(self, club, season, typek, brand, competition):
        """Test creating a kit."""
        from footycollect.core.models import Kit

        kit = Kit.objects.create(
            name="Granada CF 2025-26 Third",
            slug="granada-cf-2025-26-third",
            team=club,
            season=season,
            type=typek,
            brand=brand,
            main_img_url="https://cdn.footballkitarchive.com/2025/08/20/W0Kw7NHhJViCEKR.jpg",
        )

        # Add competition
        kit.competition.add(competition)

        assert kit.name == "Granada CF 2025-26 Third"
        assert kit.slug == "granada-cf-2025-26-third"
        assert kit.team == club
        assert kit.season == season
        assert kit.type == typek
        assert kit.brand == brand
        assert kit.main_img_url == "https://cdn.footballkitarchive.com/2025/08/20/W0Kw7NHhJViCEKR.jpg"
        assert competition in kit.competition.all()
        assert str(kit) == "Granada CF 2025-26 Third"

    def test_kit_str_representation(self, club, season, typek, brand):
        """Test kit string representation."""
        from footycollect.core.models import Kit

        kit = Kit.objects.create(
            name="Test Kit",
            slug="test-kit",
            team=club,
            season=season,
            type=typek,
            brand=brand,
            main_img_url="https://example.com/test.jpg",
        )
        assert str(kit) == "Test Kit"

    def test_kit_generate_slug(self, club, season, typek, brand):
        """Test kit slug generation."""
        from footycollect.core.models import Kit

        kit = Kit.objects.create(
            name="Granada CF 2025-26 Third",
            slug="granada-cf-2025-26-third",
            team=club,
            season=season,
            type=typek,
            brand=brand,
            main_img_url="https://cdn.footballkitarchive.com/2025/08/20/W0Kw7NHhJViCEKR.jpg",
        )

        generated_slug = kit.generate_slug()
        assert generated_slug == "granada-cf-2025-26-third"

    def test_kit_generate_slug_lowercase_and_hyphens(self, club, season, typek, brand):
        """Test kit generate_slug converts to lowercase and replaces spaces with hyphens."""
        from footycollect.core.models import Kit

        kit = Kit.objects.create(
            name="Test Kit Name With Spaces",
            slug="test-kit-name-with-spaces",
            team=club,
            season=season,
            type=typek,
            brand=brand,
            main_img_url="https://example.com/test.jpg",
        )

        generated_slug = kit.generate_slug()
        assert generated_slug == "test-kit-name-with-spaces"
        assert generated_slug.islower()
        assert " " not in generated_slug

    def test_kit_unique_slug(self, club, season, typek, brand):
        """Test kit slug uniqueness."""
        from footycollect.core.models import Kit

        Kit.objects.create(
            name="Granada CF 2025-26 Third",
            slug="granada-cf-2025-26-third",
            team=club,
            season=season,
            type=typek,
            brand=brand,
            main_img_url="https://cdn.footballkitarchive.com/2025/08/20/W0Kw7NHhJViCEKR.jpg",
        )

        # Should raise IntegrityError for duplicate slug
        with pytest.raises(IntegrityError):
            Kit.objects.create(
                name="Granada CF 2025-26 Third",
                slug="granada-cf-2025-26-third",
                team=club,
                season=season,
                type=typek,
                brand=brand,
                main_img_url="https://cdn.footballkitarchive.com/2025/08/20/W0Kw7NHhJViCEKR.jpg",
            )


@pytest.mark.django_db
class TestCoreFactories:
    """Tests for factories defined in footycollect.core.factories."""

    def test_core_factories_import_and_attributes(self):
        from footycollect.core import factories as core_factories

        assert hasattr(core_factories, "SeasonFactory")
        assert hasattr(core_factories, "TypeKFactory")
        assert hasattr(core_factories, "CompetitionFactory")
        assert hasattr(core_factories, "ClubFactory")
        assert hasattr(core_factories, "BrandFactory")
        assert hasattr(core_factories, "KitFactory")

    def test_core_factories_kit_factory_creates_valid_instance(self):
        from footycollect.core import factories as core_factories
        from footycollect.core.models import Brand, Club, Competition, Kit, Season, TypeK

        kit = core_factories.KitFactory()

        assert isinstance(kit, Kit)
        assert kit.pk is not None

        assert isinstance(kit.team, Club)
        assert isinstance(kit.season, Season)
        assert isinstance(kit.type, TypeK)
        assert isinstance(kit.brand, Brand)
        assert isinstance(kit.main_img_url, str)
        assert kit.main_img_url != ""

        competitions = list(kit.competition.all())
        assert len(competitions) >= 1
        assert all(isinstance(comp, Competition) for comp in competitions)

    def test_kit_factory_create_false_skips_competition_post_generation(self):
        from footycollect.core import factories as core_factories

        kit = core_factories.KitFactory.build()
        assert kit is not None

    def test_kit_factory_without_extracted_adds_one_competition(self):
        from footycollect.core import factories as core_factories

        kit = core_factories.KitFactory()
        assert kit.competition.count() == 1

    def test_kit_factory_with_extracted_competitions_adds_them(self):
        from footycollect.core import factories as core_factories
        from footycollect.core.models import Kit

        comp1 = core_factories.CompetitionFactory(name="League A")
        comp2 = core_factories.CompetitionFactory(name="League B")
        expected_competition_count = 2
        kit = core_factories.KitFactory(competition=[comp1, comp2])
        assert isinstance(kit, Kit)
        assert kit.competition.count() == expected_competition_count
        assert set(kit.competition.values_list("name", flat=True)) == {"League A", "League B"}
