"""Date parsing and calculations for the PDS pipeline."""

from datetime import date, datetime, timedelta

import pandas as pd

FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%Y/%m/%d"]


def parse_date(value) -> date | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, (datetime, pd.Timestamp)):
        ts = value
        if pd.isna(ts):
            return None
        return ts.date()

    s = str(value).strip()
    if not s or s.lower() in ("nan", "nat", "none", ""):
        return None

    for fmt in FORMATS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def date_to_str(d, fmt: str = "%Y-%m-%d") -> str | None:
    if d is None or (isinstance(d, float) and pd.isna(d)):
        return None
    if isinstance(d, pd.Timestamp) and pd.isna(d):
        return None
    parsed = parse_date(d)
    if parsed is None:
        return None
    return parsed.strftime(fmt)


def days_between(d1, d2) -> int | None:
    a = parse_date(d1) if not isinstance(d1, date) else d1
    b = parse_date(d2) if not isinstance(d2, date) else d2
    if a is None or b is None:
        return None
    return (b - a).days


def add_days(d, n: int) -> date | None:
    base = parse_date(d) if not isinstance(d, date) else d
    if base is None:
        return None
    return base + timedelta(days=n)


def next_business_day(d: date | None = None) -> date:
    if d is None:
        d = date.today() + timedelta(days=1)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def is_overdue(d, today: date | None = None) -> bool:
    parsed = parse_date(d)
    if parsed is None:
        return False
    today = today or date.today()
    return parsed < today


def days_until(d, today: date | None = None) -> int | None:
    parsed = parse_date(d) if not isinstance(d, date) else d
    if parsed is None:
        return None
    today = today or date.today()
    return (parsed - today).days
