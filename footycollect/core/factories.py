"""
Factory Boy factories for the core app.

These factories provide convenient ways to create core models such as
Season, TypeK, Competition, Club, Brand, and Kit for tests.
"""

import factory
from factory.django import DjangoModelFactory

from footycollect.core.models import Brand, Club, Competition, Kit, Season, TypeK


class SeasonFactory(DjangoModelFactory):
    """Factory for creating Season instances."""

    class Meta:
        model = Season

    id_fka = None
    year = factory.Sequence(lambda n: f"{2000 + n}-{2001 + n}")
    first_year = factory.LazyAttribute(lambda obj: obj.year.split("-")[0])
    second_year = factory.LazyAttribute(lambda obj: obj.year.split("-")[1])


class TypeKFactory(DjangoModelFactory):
    """Factory for creating TypeK instances."""

    class Meta:
        model = TypeK

    name = factory.Sequence(lambda n: f"Type {n}")
    category = factory.Iterator(["match", "prematch", "preseason", "training", "travel"])
    is_goalkeeper = False


class CompetitionFactory(DjangoModelFactory):
    """Factory for creating Competition instances."""

    class Meta:
        model = Competition

    id_fka = None
    name = factory.Sequence(lambda n: f"Competition {n}")
    slug = factory.Sequence(lambda n: f"competition-{n}")
    logo = factory.Faker("url")
    logo_dark = factory.Faker("url")


class ClubFactory(DjangoModelFactory):
    """Factory for creating Club instances."""

    class Meta:
        model = Club

    id_fka = None
    name = factory.Sequence(lambda n: f"Club {n}")
    country = "ES"
    slug = factory.Sequence(lambda n: f"club-{n}")
    logo = factory.Faker("url")
    logo_dark = factory.Faker("url")


class BrandFactory(DjangoModelFactory):
    """Factory for creating Brand instances."""

    class Meta:
        model = Brand

    id_fka = None
    name = factory.Sequence(lambda n: f"Brand {n}")
    slug = factory.Sequence(lambda n: f"brand-{n}")
    logo = factory.Faker("url")
    logo_dark = factory.Faker("url")


class KitFactory(DjangoModelFactory):
    """Factory for creating Kit instances."""

    class Meta:
        model = Kit

    id_fka = None
    name = factory.Sequence(lambda n: f"Kit {n}")
    slug = factory.Sequence(lambda n: f"kit-{n}")
    team = factory.SubFactory(ClubFactory)
    season = factory.SubFactory(SeasonFactory)
    type = factory.SubFactory(TypeKFactory)
    brand = factory.SubFactory(BrandFactory)
    main_img_url = factory.Faker("url")

    @factory.post_generation
    def competition(self, create, extracted, **kwargs):
        """
        Optionally add related Competition instances.

        If `extracted` is provided, it should be an iterable of Competition
        instances to add to the many-to-many field. Otherwise a single
        Competition is created and added.
        """
        if not create:
            return

        if extracted:
            for competition in extracted:
                self.competition.add(competition)
        else:
            self.competition.add(CompetitionFactory())
