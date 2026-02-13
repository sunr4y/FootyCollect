from unittest.mock import MagicMock, patch

import pytest
from django.core.management import call_command

from footycollect.core.management.commands.setup_beat_schedule import DEFAULTS


@pytest.mark.django_db
def test_setup_beat_schedule_creates_or_updates_tasks():
    with (
        patch(
            "footycollect.core.management.commands.setup_beat_schedule.IntervalSchedule",
        ) as mock_interval,
        patch(
            "footycollect.core.management.commands.setup_beat_schedule.PeriodicTask",
        ) as mock_periodic_task,
    ):
        mock_interval.objects.get_or_create.return_value = (MagicMock(), True)
        mock_periodic_task.objects.update_or_create.return_value = (MagicMock(), True)

        call_command("setup_beat_schedule")

    assert mock_interval.objects.get_or_create.call_count == len(DEFAULTS)
    assert mock_periodic_task.objects.update_or_create.call_count == len(DEFAULTS)


@pytest.mark.django_db
def test_setup_beat_schedule_dry_run_executes_without_persisting(capsys):
    with (
        patch(
            "footycollect.core.management.commands.setup_beat_schedule.IntervalSchedule",
        ) as mock_interval,
        patch(
            "footycollect.core.management.commands.setup_beat_schedule.PeriodicTask",
        ) as mock_periodic_task,
    ):
        mock_interval.objects.get_or_create.return_value = (MagicMock(), True)
        mock_periodic_task.objects.update_or_create.return_value = (MagicMock(), True)

        call_command("setup_beat_schedule", "--dry-run")

    assert mock_interval.objects.get_or_create.call_count == len(DEFAULTS)
    assert mock_periodic_task.objects.update_or_create.call_count == len(DEFAULTS)

    captured = capsys.readouterr()
    assert "DRY RUN: no changes will be saved" in captured.out


@pytest.mark.django_db
def test_setup_beat_schedule_propagates_errors():
    with patch(
        "footycollect.core.management.commands.setup_beat_schedule.IntervalSchedule",
    ) as mock_interval:
        mock_interval.objects.get_or_create.side_effect = RuntimeError("db error")

        with pytest.raises(RuntimeError, match="db error"):
            call_command("setup_beat_schedule")
