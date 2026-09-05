"""Tehran market calendar and the sole live-upstream request window.

The ordinary cash session is Saturday-Wednesday, 09:00-12:30 Asia/Tehran.
TAL (12:45-13:00) is intentionally not mixed into this feed because it has a
different instrument/session contract. No TSETMC request is allowed outside
the ordinary continuous session.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from packages.shared.datetime_utils import to_jalali_str


TEHRAN_TZ = ZoneInfo("Asia/Tehran")
TSE_PREMARKET_START = time(8, 45)
TSE_MARKET_OPEN = time(9, 0)
TSE_MARKET_CLOSE = time(12, 30)

# datetime.weekday(): Monday=0 ... Saturday=5, Sunday=6.
IRAN_TRADING_WEEKDAYS = {5, 6, 0, 1, 2}


def _as_tehran(dt: datetime | None) -> datetime:
    if dt is None:
        return datetime.now(TEHRAN_TZ)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=TEHRAN_TZ)
    return dt.astimezone(TEHRAN_TZ)


def _parse_holiday_dates(raw: str) -> frozenset[date]:
    values: set[date] = set()
    for item in (raw or "").replace(";", ",").split(","):
        value = item.strip()
        if not value:
            continue
        try:
            values.add(date.fromisoformat(value))
        except ValueError:
            # An invalid optional date must not crash availability endpoints.
            continue
    return frozenset(values)


def configured_market_holidays() -> frozenset[date]:
    """Return operator-reviewed Gregorian closure dates from configuration."""
    from packages.shared.config import settings

    return _parse_holiday_dates(settings.iran_market_holidays)


def get_tehran_now() -> datetime:
    return datetime.now(TEHRAN_TZ)


def is_tse_trading_day(
    dt: datetime | None = None,
    *,
    holiday_dates: frozenset[date] | set[date] | None = None,
) -> bool:
    """True only for a Sat-Wed date that is not a configured closure."""
    local = _as_tehran(dt)
    holidays = configured_market_holidays() if holiday_dates is None else holiday_dates
    return local.weekday() in IRAN_TRADING_WEEKDAYS and local.date() not in holidays


def is_tse_market_open(
    dt: datetime | None = None,
    *,
    holiday_dates: frozenset[date] | set[date] | None = None,
) -> bool:
    """True during the half-open ordinary session [09:00, 12:30)."""
    local = _as_tehran(dt)
    if not is_tse_trading_day(local, holiday_dates=holiday_dates):
        return False
    return TSE_MARKET_OPEN <= local.time() < TSE_MARKET_CLOSE


def is_tse_premarket(
    dt: datetime | None = None,
    *,
    holiday_dates: frozenset[date] | set[date] | None = None,
) -> bool:
    local = _as_tehran(dt)
    if not is_tse_trading_day(local, holiday_dates=holiday_dates):
        return False
    return TSE_PREMARKET_START <= local.time() < TSE_MARKET_OPEN


def next_tse_market_open(
    dt: datetime | None = None,
    *,
    holiday_dates: frozenset[date] | set[date] | None = None,
) -> datetime:
    """Return the next ordinary-session open in Asia/Tehran."""
    local = _as_tehran(dt)
    holidays = configured_market_holidays() if holiday_dates is None else holiday_dates
    if is_tse_market_open(local, holiday_dates=holidays):
        return local
    if is_tse_trading_day(local, holiday_dates=holidays) and local.time() < TSE_MARKET_OPEN:
        return datetime.combine(local.date(), TSE_MARKET_OPEN, tzinfo=TEHRAN_TZ)

    for offset in range(1, 370):
        candidate_day = local.date() + timedelta(days=offset)
        candidate = datetime.combine(candidate_day, TSE_MARKET_OPEN, tzinfo=TEHRAN_TZ)
        if is_tse_trading_day(candidate, holiday_dates=holidays):
            return candidate
    raise RuntimeError("No Tehran trading day found in the configured calendar horizon.")


def seconds_until_next_market_open(dt: datetime | None = None) -> int:
    local = _as_tehran(dt)
    if is_tse_market_open(local):
        return 0
    return max(1, int((next_tse_market_open(local) - local).total_seconds()))


def get_market_session_state(dt: datetime | None = None) -> dict:
    """Return an API-safe market state and exact upstream request policy."""
    local = _as_tehran(dt)
    holidays = configured_market_holidays()
    is_holiday = local.date() in holidays
    is_open = is_tse_market_open(local, holiday_dates=holidays)
    is_pre = is_tse_premarket(local, holiday_dates=holidays)
    is_workday = is_tse_trading_day(local, holiday_dates=holidays)

    if is_open:
        status_code = "OPEN"
        status_fa = "بازار باز است — دریافت زنده هر ۶۰ ثانیه"
        cadence_seconds = 60
        next_open = local
    else:
        next_open = next_tse_market_open(local, holiday_dates=holidays)
        cadence_seconds = max(1, int((next_open - local).total_seconds()))
        if is_holiday:
            status_code = "HOLIDAY"
            status_fa = "تعطیل رسمی بازار — درخواست منبع متوقف است"
        elif is_pre:
            status_code = "PRE_MARKET"
            status_fa = "پیش‌گشایش — دریافت زنده از ساعت ۰۹:۰۰ آغاز می‌شود"
        elif is_workday and local.time() < TSE_PREMARKET_START:
            status_code = "PRE_SESSION"
            status_fa = "پیش از جلسه — درخواست منبع متوقف است"
        elif is_workday and local.time() >= TSE_MARKET_CLOSE:
            status_code = "POST_MARKET"
            status_fa = "بازار بسته — آخرین snapshot تا جلسه بعد نمایش داده می‌شود"
        else:
            status_code = "WEEKEND"
            status_fa = "تعطیلات پایان هفته — درخواست منبع متوقف است"

    next_open_utc = next_open.astimezone(timezone.utc)
    return {
        "status_code": status_code,
        "status_fa": status_fa,
        "is_open": is_open,
        "is_premarket": is_pre,
        "is_workday": is_workday,
        "is_holiday": is_holiday,
        "upstream_requests_allowed": is_open,
        "live_collection_allowed": is_open,
        "cadence_seconds": cadence_seconds,
        "auto_trade_interval_minutes": 1 if is_open else max(1, (cadence_seconds + 59) // 60),
        "seconds_until_next_open": 0 if is_open else cadence_seconds,
        "next_open_at_tehran": next_open.isoformat(),
        "next_open_at_utc": next_open_utc.isoformat(),
        "next_open_jalali": to_jalali_str(next_open, include_time=True),
        "session_open_tehran": "09:00:00",
        "session_close_tehran": "12:30:00",
        "tehran_time": local.strftime("%H:%M:%S"),
        "tehran_date": local.strftime("%Y-%m-%d"),
    }


def get_dynamic_scheduler_cadence_seconds() -> int:
    """One minute in-session; otherwise sleep exactly until the next open."""
    return get_market_session_state()["cadence_seconds"]
