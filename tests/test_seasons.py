from datetime import date

import pytest

from sportslakehouse.seasons import (
    current_season_start,
    fd_code,
    is_completed,
    parse_season,
    season_label,
    season_range,
)


def test_labels_and_codes():
    assert season_label(2000) == "2000-01"
    assert season_label(2024) == "2024-25"
    assert season_label(1999) == "1999-00"
    assert fd_code(2000) == "0001"
    assert fd_code(2024) == "2425"
    assert fd_code(1999) == "9900"


@pytest.mark.parametrize("value", [2024, "2024", "2024-25", "2024/25"])
def test_parse_season(value):
    assert parse_season(value) == 2024


def test_parse_season_rejects_garbage():
    with pytest.raises(ValueError):
        parse_season("abc")


def test_current_season_switches_in_july():
    assert current_season_start(date(2026, 6, 30)) == 2025
    assert current_season_start(date(2026, 7, 1)) == 2026
    assert current_season_start(date(2026, 11, 6)) == 2026


def test_season_range_and_completed():
    seasons = season_range(2000, today=date(2026, 11, 6))
    assert seasons[0] == 2000 and seasons[-1] == 2026
    assert len(seasons) == 27
    assert is_completed(2025, today=date(2026, 11, 6))
    assert not is_completed(2026, today=date(2026, 11, 6))
