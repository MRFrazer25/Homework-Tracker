from datetime import date

import pytest

from src.utils.date_parsing import parse_date

WEDNESDAY = date(2026, 9, 30)


@pytest.mark.parametrize("text, expected", [
    ("today", date(2026, 9, 30)),
    ("tomorrow", date(2026, 10, 1)),
    ("friday", date(2026, 10, 2)),
    ("Fri", date(2026, 10, 2)),
    ("due this friday", date(2026, 10, 2)),
    ("next friday", date(2026, 10, 9)),
    ("monday", date(2026, 10, 5)),
    ("next monday", date(2026, 10, 5)),  # No Monday left this week, so "next" is the coming one
    ("wednesday", date(2026, 9, 30)),  # Today counts
    ("next wednesday", date(2026, 10, 7)),
    ("in 3 days", date(2026, 10, 3)),
    ("in two weeks", date(2026, 10, 14)),
    ("next week", date(2026, 10, 7)),
    ("oct 10", date(2026, 10, 10)),
    ("October 10th", date(2026, 10, 10)),
    ("10 oct", date(2026, 10, 10)),
    ("sept 1", date(2027, 9, 1)),  # Already passed this year, so next year
    ("2026-12-25", date(2026, 12, 25)),
    ("10/10", date(2026, 10, 10)),
    ("1/5/27", date(2027, 1, 5)),
])
def test_parse_date(text, expected):
    assert parse_date(text, today=WEDNESDAY) == expected


@pytest.mark.parametrize("text", ["", "someday", "feb 30", "2026-13-01", "whenever"])
def test_unparseable_returns_none(text):
    assert parse_date(text, today=WEDNESDAY) is None
