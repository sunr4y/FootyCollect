"""
Factory Boy factories for core app.
"""

import factory
from factory.django import DjangoModelFactory

from footycollect.core.models import SiteConfiguration


class SiteConfigurationFactory(DjangoModelFactory):
    """Factory for creating test site configurations."""

    class Meta:
        model = SiteConfiguration

    site_name = factory.Faker("company")
    site_description = factory.Faker("text", max_nb_chars=200)
    contact_email = factory.Faker("email")
    is_maintenance_mode = False
