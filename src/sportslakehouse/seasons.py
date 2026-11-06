"""Season arithmetic for European football seasons (August to May)."""

from __future__ import annotations

from datetime import date


def season_label(start_year: int) -> str:
    """2024 -> '2024-25'."""
    return f"{start_year}-{(start_year + 1) % 100:02d}"


def fd_code(start_year: int) -> str:
    """football-data.co.uk folder code: 2024 -> '2425', 1999 -> '9900'."""
    return f"{start_year % 100:02d}{(start_year + 1) % 100:02d}"


def parse_season(value: str | int) -> int:
    """Accept 2024, '2024', '2024-25' or '2024/25' and return the start year."""
    text = str(value).strip().replace("/", "-")
    head = text.split("-")[0]
    if not head.isdigit() or len(head) != 4:
        raise ValueError(f"Cannot parse season: {value!r}")
    return int(head)


def current_season_start(today: date | None = None) -> int:
    """The Bundesliga season starts in August, so July onwards counts as the new season."""
    today = today or date.today()
    return today.year if today.month >= 7 else today.year - 1


def season_range(first_start: int, today: date | None = None) -> list[int]:
    """All season start years from `first_start` up to and including the current season."""
    return list(range(first_start, current_season_start(today) + 1))


def is_completed(start_year: int, today: date | None = None) -> bool:
    return start_year < current_season_start(today)
