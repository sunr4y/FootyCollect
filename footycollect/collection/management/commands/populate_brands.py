from secrets import randbelow

from django.core.management.base import BaseCommand
from django.utils.text import slugify
from faker import Faker

from footycollect.collection.models import Brand

fake = Faker()


class Command(BaseCommand):
    help = "Populates database with 50 Brand items"

    def handle(self, *args, **options):
        brand_names = [
            "Nike",
            "Adidas",
            "Puma",
            "Under Armour",
            "New Balance",
            "Reebok",
            "Umbro",
            "Kappa",
            "Diadora",
            "Joma",
            "Macron",
            "Hummel",
            "Uhlsport",
            "Errea",
            "Mizuno",
        ]

        # Extender la lista para tener más de 50 nombres únicos
        extended_names = brand_names + [f"{fake.company()} Sports" for _ in range(35)]

        for name in extended_names:
            Brand.objects.create(
                id_fka=randbelow(9000) + 1000,  # Generate number between 1000-9999
                name=name,
                slug=slugify(name),
                logo=f"https://example.com/logos/{slugify(name)}.png",
                logo_dark=f"https://example.com/logos/dark/{slugify(name)}.png",
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully created {len(extended_names)} Brand items",
            ),
        )


# End of Selection
