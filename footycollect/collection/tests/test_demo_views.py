"""Tests for collection.views.demo_views."""

from django.test import SimpleTestCase

from footycollect.collection.views.demo_views import _distribute_kits_to_columns


def _make_kits(n, team_prefix="Team"):
    return [{"team_name": f"{team_prefix}{i}", "name": f"Kit {i}"} for i in range(n)]


class TestDistributeKitsToColumns(SimpleTestCase):
    def test_returns_empty_columns_when_kits_empty(self):
        result = _distribute_kits_to_columns([], num_columns=3, kits_per_column=2)
        assert result == [[], [], []]

    def test_non_empty_kits_distributed_across_columns(self):
        kits = _make_kits(5)
        num_columns = 3
        kits_per_column = 2
        result = _distribute_kits_to_columns(kits, num_columns=num_columns, kits_per_column=kits_per_column)
        assert len(result) == num_columns
        total_placed = sum(len(col) // 3 for col in result)
        expected_placed = 5
        assert total_placed == expected_placed
        for col in result:
            assert len(col) <= kits_per_column * 3

    def test_kits_exceed_total_slots_truncates_to_slots(self):
        kits = _make_kits(10)
        num_columns = 2
        kits_per_column = 2
        result = _distribute_kits_to_columns(kits, num_columns=num_columns, kits_per_column=kits_per_column)
        assert len(result) == num_columns
        total_placed = sum(len(col) // 3 for col in result)
        max_slots = num_columns * kits_per_column
        assert total_placed == max_slots
        for col in result:
            assert len(col) == kits_per_column * 3

    def test_fewer_kits_than_columns_leaves_empty_columns(self):
        kits = _make_kits(2)
        num_columns = 4
        kits_per_column = 2
        result = _distribute_kits_to_columns(kits, num_columns=num_columns, kits_per_column=kits_per_column)
        assert len(result) == num_columns
        total_placed = sum(len(col) // 3 for col in result)
        expected_placed = 2
        assert total_placed == expected_placed
        min_empty_columns = 2
        empty_count = sum(1 for col in result if len(col) == 0)
        assert empty_count >= min_empty_columns

