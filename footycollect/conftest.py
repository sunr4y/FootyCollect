import pytest


@pytest.fixture(autouse=True)
def _media_storage(settings, tmpdir) -> None:
    settings.MEDIA_ROOT = tmpdir.strpath


@pytest.fixture
def user(db):
    """Create a test user."""
    from footycollect.users.tests.factories import UserFactory

    return UserFactory()


@pytest.fixture
def brand(db):
    """Create a test brand."""
    from footycollect.core.models import Brand

    return Brand.objects.create(
        name="Nike",
        slug="nike",
        logo="https://www.footballkitarchive.com/static/logos/misc/Nike.png",
    )


@pytest.fixture
def club(db):
    """Create a test club."""
    from footycollect.core.models import Club

    return Club.objects.create(
        name="FC Barcelona",
        slug="fc-barcelona",
        country="ES",
        logo="https://www.footballkitarchive.com/static/logos/teams/6_l.png?v=1664834103&s=128",
    )


@pytest.fixture
def season(db):
    """Create a test season."""
    from footycollect.core.models import Season

    return Season.objects.create(
        year="2023-24",
        first_year="2023",
        second_year="2024",
    )


@pytest.fixture
def typek(db):
    """Create a test kit type."""
    from footycollect.core.models import TypeK

    return TypeK.objects.create(name="Home")


@pytest.fixture
def competition(db):
    """Create a test competition."""
    from footycollect.core.models import Competition

    return Competition.objects.create(
        name="Champions League",
        slug="champions-league",
        logo="https://www.footballkitarchive.com/static/logos/not_found.png",
    )


@pytest.fixture
def size(db):
    """Create a test size."""
    from footycollect.collection.models import Size

    return Size.objects.create(
        name="M",
        category="tops",
    )


@pytest.fixture
def jersey(db, user, brand, club, season, size):  # noqa: PLR0913
    """Create a test jersey."""
    from footycollect.collection.models import Jersey

    return Jersey.objects.create(
        user=user,
        brand=brand,
        club=club,
        season=season,
        size=size,
        condition=10,
    )
