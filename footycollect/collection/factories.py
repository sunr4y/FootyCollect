"""
Factory Boy factories for collection app.
"""

import factory
from django.contrib.auth import get_user_model
from factory.django import DjangoModelFactory

from footycollect.collection.models import (
    BaseItem,
    Brand,
    Club,
    Competition,
    Jersey,
    Photo,
    Season,
    Size,
)

User = get_user_model()


class UserFactory(DjangoModelFactory):
    """Factory for creating test users."""

    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"testuser{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    name = factory.Faker("name")
    is_active = True
    is_staff = False
    is_superuser = False


class BrandFactory(DjangoModelFactory):
    """Factory for creating test brands."""

    class Meta:
        model = Brand

    name = factory.Sequence(lambda n: f"Brand {n}")
    slug = factory.Sequence(lambda n: f"brand-{n}")
    logo = factory.Faker("image_url")


class ClubFactory(DjangoModelFactory):
    """Factory for creating test clubs."""

    class Meta:
        model = Club

    name = factory.Sequence(lambda n: f"Club {n}")
    slug = factory.Sequence(lambda n: f"club-{n}")
    logo = factory.Faker("image_url")
    country = factory.Faker("country_code")


class SeasonFactory(DjangoModelFactory):
    """Factory for creating test seasons."""

    class Meta:
        model = Season

    year = factory.Sequence(lambda n: f"202{n % 10}-{n % 10 + 1}")
    first_year = factory.LazyAttribute(lambda obj: obj.year.split("-")[0])
    second_year = factory.LazyAttribute(lambda obj: obj.year.split("-")[1])


class CompetitionFactory(DjangoModelFactory):
    """Factory for creating test competitions."""

    class Meta:
        model = Competition

    name = factory.Sequence(lambda n: f"Competition {n}")
    slug = factory.Sequence(lambda n: f"competition-{n}")
    logo = factory.Faker("image_url")


class SizeFactory(DjangoModelFactory):
    """Factory for creating test sizes."""

    class Meta:
        model = Size

    name = factory.Iterator(["XS", "S", "M", "L", "XL", "XXL"])
    category = factory.Iterator(["tops", "bottoms", "other"])


class BaseItemFactory(DjangoModelFactory):
    """Factory for creating test base items."""

    class Meta:
        model = BaseItem

    name = factory.LazyAttribute(lambda obj: f"{obj.brand.name} {obj.club.name} Jersey")
    item_type = "jersey"
    user = factory.SubFactory(UserFactory)
    brand = factory.SubFactory(BrandFactory)
    club = factory.SubFactory(ClubFactory)
    season = factory.SubFactory(SeasonFactory)
    condition = factory.Faker("random_int", min=1, max=10)
    detailed_condition = "EXCELLENT"
    description = factory.Faker("text", max_nb_chars=200)
    is_replica = False
    is_private = False
    is_draft = False
    design = ""
    main_color = None
    country = ""


class JerseyFactory(DjangoModelFactory):
    """Factory for creating test jerseys."""

    class Meta:
        model = Jersey

    base_item = factory.SubFactory(BaseItemFactory)
    size = factory.SubFactory(SizeFactory)
    kit = None
    is_fan_version = True
    is_signed = False
    has_nameset = False
    player_name = ""
    number = None
    is_short_sleeve = True

    @factory.post_generation
    def competitions(self, create, extracted, **kwargs):
        """Add competitions to the jersey."""
        if not create:
            return

        if extracted:
            # If competitions are provided, use them
            for competition in extracted:
                self.base_item.competitions.add(competition)
        else:
            # Otherwise, add a random competition
            competition = CompetitionFactory()
            self.base_item.competitions.add(competition)


class PhotoFactory(DjangoModelFactory):
    """Factory for creating test photos."""

    class Meta:
        model = Photo

    content_object = factory.SubFactory(JerseyFactory)
    image = factory.django.ImageField(color="blue")
    caption = factory.Faker("sentence")
    order = factory.Sequence(lambda n: n)
    user = factory.SubFactory(UserFactory)


# Convenience factories for common test scenarios
class CompleteJerseyFactory(JerseyFactory):
    """Factory for creating a jersey with all related objects."""

    @factory.post_generation
    def competitions(self, create, extracted, **kwargs):
        """Add multiple competitions to the jersey."""
        if not create:
            return

        # Add 2-3 random competitions
        competitions = CompetitionFactory.create_batch(3)
        for competition in competitions:
            self.competitions.add(competition)


class UserWithJerseysFactory(UserFactory):
    """Factory for creating a user with multiple jerseys."""

    @factory.post_generation
    def jerseys(self, create, extracted, **kwargs):
        """Create jerseys for the user."""
        if not create:
            return

        # Create 3 jerseys for the user
        JerseyFactory.create_batch(3, user=self)
