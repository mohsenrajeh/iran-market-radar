"""Date and time utilities with Jalali (Shamsi) and UTC timezone support."""
from datetime import datetime, timezone, date
from zoneinfo import ZoneInfo
import jdatetime

from packages.shared.persian import to_persian_digits


TEHRAN_TZ = ZoneInfo("Asia/Tehran")


def now_utc() -> datetime:
    """Returns current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def to_utc_iso(dt: datetime | None) -> str | None:
    """Converts a datetime to standard UTC ISO 8601 string."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.isoformat()


def to_jalali_str(dt: datetime | date | None, include_time: bool = True, persian_digits: bool = True) -> str:
    """
    Converts Gregorian date/datetime to formatted Jalali string.
    Example: 1405/05/24 12:30:00
    """
    if dt is None:
        return "-"

    if isinstance(dt, datetime):
        # Persisted datetimes are UTC; all user-facing Jalali clocks are Tehran local.
        if dt.tzinfo is None:
            local_dt = dt.replace(tzinfo=timezone.utc).astimezone(TEHRAN_TZ)
        else:
            local_dt = dt.astimezone(TEHRAN_TZ)
        jdt = jdatetime.datetime.fromgregorian(datetime=local_dt.replace(tzinfo=None))

        if include_time:
            res = jdt.strftime("%Y/%m/%d %H:%M:%S")
        else:
            res = jdt.strftime("%Y/%m/%d")
    elif isinstance(dt, date):
        jdt = jdatetime.date.fromgregorian(date=dt)
        res = jdt.strftime("%Y/%m/%d")
    else:
        return str(dt)

    return to_persian_digits(res) if persian_digits else res


def jalali_day_name_fa(dt: datetime | date | None) -> str:
    """Returns Persian name of the day of the week (e.g. شنبه، یکشنبه)."""
    if dt is None:
        return ""
    if isinstance(dt, datetime):
        d = dt.date()
    else:
        d = dt
    jdt = jdatetime.date.fromgregorian(date=d)
    return jdt.j_weekdays_fa()[jdt.weekday()]
