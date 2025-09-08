"""
Factories for users app tests.
"""

import factory
from django.contrib.auth import get_user_model

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    """Factory for creating test users."""

    class Meta:
        model = User

    username = factory.Faker("user_name")
    email = factory.Faker("email")
    password = factory.PostGenerationMethodCall("set_password", "testpass123")
    name = factory.Faker("name")
    biography = factory.Faker("text", max_nb_chars=200)
    location = factory.Faker("city")
    is_active = True
    is_staff = False
    is_superuser = False
    is_private = False


class AdminUserFactory(UserFactory):
    """Factory for creating admin users."""

    is_staff = True
    is_superuser = True


class PrivateUserFactory(UserFactory):
    """Factory for creating private users."""

    is_private = True


class InactiveUserFactory(UserFactory):
    """Factory for creating inactive users."""

    is_active = False
