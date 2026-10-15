from datetime import date

import pytest

from src.utils.date_parsing import find_date_phrases, parse_date

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
    ("Mon Oct 5", date(2026, 10, 5)),  # The format the assistant itself uses in replies
    ("Monday, October 5th", date(2026, 10, 5)),
])
def test_parse_date(text, expected):
    assert parse_date(text, today=WEDNESDAY) == expected


@pytest.mark.parametrize("message, phrases", [
    ("push the chem midterm to next friday", ["next friday"]),
    ("I have a book report due in 2 weeks", ["in 2 weeks"]),
    ("move the lab to oct 10 and the essay to monday", ["oct 10", "monday"]),
    ("mark the month-end report as done", []),  # "mon" inside "month" isn't a date
    ("finish the history essay", []),
])
def test_find_date_phrases(message, phrases):
    assert find_date_phrases(message) == phrases


@pytest.mark.parametrize("text", ["", "someday", "feb 30", "2026-13-01", "whenever"])
def test_unparseable_returns_none(text):
    assert parse_date(text, today=WEDNESDAY) is None


@pytest.mark.parametrize("text, expected", [
    ("sept 25", date(2026, 9, 25)),  # 5 days ago: this year, not next (e.g. correcting a due date)
    ("9/16", date(2026, 9, 16)),  # Exactly two weeks ago: still this year
    ("9/15", date(2027, 9, 15)),  # Longer ago: next year
    ("the 10th", date(2026, 10, 10)),  # Day of month: still to come this month...
    ("the 30th", date(2026, 9, 30)),  # ...today counts...
    ("1st", date(2026, 10, 1)),  # ...or next month once it has passed
])
def test_recent_past_and_day_of_month(text, expected):
    assert parse_date(text, today=WEDNESDAY) == expected


def test_day_of_month_wraps_into_january():
    assert parse_date("the 3rd", today=date(2026, 12, 20)) == date(2027, 1, 3)


@pytest.mark.parametrize("message, phrases", [
    ("move the SAT practice test to the 10th", ["the 10th"]),  # "SAT" is a test, not Saturday
    ("I sat the exam, mark it done", []),
    ("the sun safety poster is due monday", ["monday"]),
    ("move it to sat", ["sat"]),  # Abbreviations still count when used as dates
    ("due fri", ["fri"]),
    ("push it to next fri", ["next fri"]),
])
def test_weekday_abbreviations_need_date_context(message, phrases):
    assert find_date_phrases(message) == phrases
