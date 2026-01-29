"""
Tests for verify_staticfiles management command.
"""

from io import StringIO

import pytest
from django.core.management import call_command


@pytest.mark.django_db
class TestVerifyStaticfilesCommand:
    """Test verify_staticfiles management command."""

    def test_verify_staticfiles_success(self):
        """verify_staticfiles runs successfully with default (test) storage."""
        out = StringIO()
        call_command("verify_staticfiles", stdout=out)
        result = out.getvalue().lower()
        assert "verification passed" in result or "staticfiles backend" in result

    def test_verify_staticfiles_skip_dry_run(self):
        """verify_staticfiles --skip-dry-run only checks config, does not run collectstatic."""
        out = StringIO()
        call_command("verify_staticfiles", "--skip-dry-run", stdout=out)
        result = out.getvalue().lower()
        assert "backend" in result or "static" in result

    def test_verify_staticfiles_missing_staticfiles_exits_nonzero(self):
        """verify_staticfiles exits with error when STORAGES['staticfiles'] is missing."""
        from unittest.mock import patch

        out = StringIO()
        err = StringIO()
        with patch("footycollect.core.management.commands.verify_staticfiles.settings") as mock_settings:
            mock_settings.STORAGES = {}
            mock_settings.STATIC_URL = "/static/"
            with pytest.raises(SystemExit) as exc_info:
                call_command("verify_staticfiles", "--skip-dry-run", stdout=out, stderr=err)
            assert exc_info.value.code == 1
