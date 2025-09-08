"""
Factory Boy factories for users app.
"""

import factory
from django.contrib.auth import get_user_model
from factory.django import DjangoModelFactory

User = get_user_model()


class UserFactory(DjangoModelFactory):
    """Factory for creating test users."""

    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    name = factory.Faker("name")
    is_active = True
    is_staff = False
    is_superuser = False


class StaffUserFactory(UserFactory):
    """Factory for creating staff users."""

    is_staff = True


class SuperUserFactory(UserFactory):
    """Factory for creating superusers."""

    is_staff = True
    is_superuser = True


class InactiveUserFactory(UserFactory):
    """Factory for creating inactive users."""

    is_active = False


# Convenience factories for common test scenarios
class UserWithProfileFactory(UserFactory):
    """Factory for creating a user with a complete profile."""

    name = factory.Faker("name")
    biography = factory.Faker("text", max_nb_chars=200)
    location = factory.Faker("city")
