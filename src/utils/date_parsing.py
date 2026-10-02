"""Turns everyday date phrases ("friday", "next monday", "oct 10", "in 3 days") into dates.

Small language models are unreliable at calendar math, so the assistant passes dates through
exactly as the user said them and this module resolves them deterministically.
"""

import re
from datetime import date, datetime, timedelta

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
WEEKDAY_ALIASES = {"mon": 0, "tue": 1, "tues": 1, "wed": 2, "thu": 3, "thur": 3, "thurs": 3,
                   "fri": 4, "sat": 5, "sun": 6}
MONTHS = ["january", "february", "march", "april", "may", "june", "july",
          "august", "september", "october", "november", "december"]

_WEEKDAY_PATTERN = "|".join(WEEKDAYS + sorted(WEEKDAY_ALIASES, key=len, reverse=True))
_MONTH_PATTERN = "|".join(m[:3] + r"[a-z]*" for m in MONTHS)


_DATE_PHRASE = re.compile(
    rf"\b(?:today|tonight|tomorrow|next week"
    rf"|in (?:\d+|a|one|two|three) (?:days?|weeks?)"
    rf"|(?:next |this )?(?:{_WEEKDAY_PATTERN})"
    rf"|(?:{_MONTH_PATTERN}) \d{{1,2}}(?:st|nd|rd|th)?"
    rf"|\d{{1,2}}(?:st|nd|rd|th)? (?:of )?(?:{_MONTH_PATTERN})"
    rf"|\d{{4}}-\d{{1,2}}-\d{{1,2}}|\d{{1,2}}/\d{{1,2}}(?:/\d{{2,4}})?)\b",
    re.IGNORECASE)


def find_date_phrases(text):
    """Returns the date phrases in a message, e.g. "push it to next friday" -> ["next friday"]."""
    return [m.group(0) for m in _DATE_PHRASE.finditer(text or "")]


def _weekday_index(word):
    word = word.lower()
    if word in WEEKDAYS:
        return WEEKDAYS.index(word)
    return WEEKDAY_ALIASES.get(word)


def _safe_date(year, month, day):
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _upcoming(year, month, day, today):
    """A month/day with no year means the next time that date comes around."""
    candidate = _safe_date(year, month, day)
    if candidate and candidate < today:
        candidate = _safe_date(year + 1, month, day)
    return candidate


def parse_date(text, today=None):
    """
    Resolve a date phrase relative to `today`.

    Weekday names mean the next occurrence (today counts), and "next <weekday>" means the
    occurrence after that only when that weekday is still to come this week, e.g. on a
    Wednesday "friday" is in 2 days and "next friday" is in 9 days, while "next monday" is
    in 5 days because there is no Monday left this week.

    Returns:
        date | None: The resolved date, or None if the text isn't recognised.
    """
    if today is None:
        today = date.today()
    if isinstance(today, datetime):
        today = today.date()
    if isinstance(text, (date, datetime)):
        return text.date() if isinstance(text, datetime) else text
    if not text:
        return None

    s = text.strip().lower()
    s = re.sub(r"[,]", " ", s)
    s = re.sub(r"\b(due|by|on|the|this|of|at|end of day|eod)\b", " ", s)
    s = re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", s)
    s = " ".join(s.split())

    if s in ("today", "tonight"):
        return today
    if s == "tomorrow":
        return today + timedelta(days=1)
    if s in ("next week", "a week", "in a week", "1 week"):
        return today + timedelta(days=7)

    match = re.fullmatch(r"in (\d+|a|one|two|three) (day|days|week|weeks)", s)
    if match:
        amount = {"a": 1, "one": 1, "two": 2, "three": 3}.get(match.group(1)) or int(match.group(1))
        return today + timedelta(days=amount * (7 if match.group(2).startswith("week") else 1))

    match = re.fullmatch(rf"(next )?({_WEEKDAY_PATTERN})", s)
    if match:
        target = _weekday_index(match.group(2))
        days_ahead = (target - today.weekday()) % 7
        if match.group(1) and target > today.weekday():
            days_ahead += 7  # "next friday" said on a Wednesday skips this week's Friday
        elif match.group(1) and days_ahead == 0:
            days_ahead = 7
        return today + timedelta(days=days_ahead)

    # A weekday in front of a full date ("Mon Oct 5", "Monday, October 5") adds nothing; parse the rest
    match = re.fullmatch(rf"({_WEEKDAY_PATTERN}) (.+)", s)
    if match:
        return parse_date(match.group(2), today)

    match = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", s)
    if match:
        return _safe_date(*map(int, match.groups()))

    match = re.fullmatch(r"(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?", s)  # US style month/day[/year]
    if match:
        month, day, year = match.groups()
        if year:
            year = int(year) + (2000 if len(year) == 2 else 0)
            return _safe_date(year, int(month), int(day))
        return _upcoming(today.year, int(month), int(day), today)

    match = re.fullmatch(rf"({_MONTH_PATTERN}) (\d{{1,2}})(?: (\d{{4}}))?", s)  # "oct 10", "october 10 2027"
    if not match:
        match = re.fullmatch(rf"(\d{{1,2}}) ({_MONTH_PATTERN})(?: (\d{{4}}))?", s)  # "10 oct"
        if match:
            match_groups = (match.group(2), match.group(1), match.group(3))
        else:
            match_groups = None
    else:
        match_groups = match.groups()
    if match_groups:
        month_word, day, year = match_groups
        month = next(i + 1 for i, m in enumerate(MONTHS) if month_word.startswith(m[:3]))
        if year:
            return _safe_date(int(year), month, int(day))
        return _upcoming(today.year, month, int(day), today)

    return None
