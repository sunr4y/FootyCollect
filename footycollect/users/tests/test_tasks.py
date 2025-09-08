import pytest

from footycollect.users.tasks import get_users_count
from footycollect.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def test_user_count(settings):
    """A basic test to execute the get_users_count Celery task."""
    batch_size = 3
    UserFactory.create_batch(batch_size)

    # Configure Celery to run tasks synchronously for testing
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True
    settings.CELERY_BROKER_URL = "memory://"
    settings.CELERY_RESULT_BACKEND = "cache+memory://"

    # Test the task function directly instead of using .delay()
    result = get_users_count()
    assert result == batch_size
