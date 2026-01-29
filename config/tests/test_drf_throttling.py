from django.conf import settings


def test_drf_api_throttle_configuration():
    assert "DEFAULT_THROTTLE_CLASSES" in settings.REST_FRAMEWORK
    assert "DEFAULT_THROTTLE_RATES" in settings.REST_FRAMEWORK
    rates = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
    assert "user" in rates
    assert "anon" in rates
    assert "/" in rates["user"]
    assert "/" in rates["anon"]
    assert settings.REST_FRAMEWORK.get("EXCEPTION_HANDLER") == "config.exceptions.drf_exception_handler"
