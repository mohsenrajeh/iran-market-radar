"""Tehran Stock Exchange (TSE) Trading Hours and Adaptive Cadence Engine."""
from datetime import datetime, time, timezone, timedelta
from typing import Tuple
from zoneinfo import ZoneInfo
import jdatetime

from packages.shared.datetime_utils import now_utc
from packages.shared.logger import logger

# Tehran Timezone
TEHRAN_TZ = ZoneInfo("Asia/Tehran")

# Official TSE Trading Sessions (Tehran Local Time)
# Pre-market / Auction: 08:45 - 09:00
# Continuous Trading: 09:00 - 12:30
TSE_PREMARKET_START = time(8, 45)
TSE_MARKET_OPEN = time(9, 0)
TSE_MARKET_CLOSE = time(12, 30)

# Weekly working days in Iran: Saturday (0 in Jalali, 5 in Gregorian ISO) to Wednesday (4 in Jalali, 2 in Gregorian ISO)
# In Python datetime.weekday(): Monday=0, Tuesday=1, Wednesday=2, Thursday=3, Friday=4, Saturday=5, Sunday=6
IRAN_TRADING_WEEKDAYS = {5, 6, 0, 1, 2}  # شنبه، یکشنبه، دوشنبه، سه‌شنبه، چهارشنبه


def get_tehran_now() -> datetime:
    """Returns current datetime in Tehran timezone."""
    return datetime.now(TEHRAN_TZ)


def is_tse_trading_day(dt: datetime | None = None) -> bool:
    """Returns True if the given date is an official trading weekday (Sat-Wed)."""
    if dt is None:
        dt = get_tehran_now()
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=TEHRAN_TZ)
    else:
        dt = dt.astimezone(TEHRAN_TZ)

    # Check weekday (Saturday=5 to Wednesday=2)
    return dt.weekday() in IRAN_TRADING_WEEKDAYS


def is_tse_market_open(dt: datetime | None = None) -> bool:
    """
    Returns True if current time is within official continuous trading hours
    (09:00 to 12:30 Tehran time on Saturday through Wednesday).
    """
    if dt is None:
        dt = get_tehran_now()
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=TEHRAN_TZ)
    else:
        dt = dt.astimezone(TEHRAN_TZ)

    if not is_tse_trading_day(dt):
        return False

    current_time = dt.time()
    return TSE_MARKET_OPEN <= current_time <= TSE_MARKET_CLOSE


def is_tse_premarket(dt: datetime | None = None) -> bool:
    """Returns True during pre-market order entry auction (08:45 - 09:00)."""
    if dt is None:
        dt = get_tehran_now()
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=TEHRAN_TZ)
    else:
        dt = dt.astimezone(TEHRAN_TZ)

    if not is_tse_trading_day(dt):
        return False

    current_time = dt.time()
    return TSE_PREMARKET_START <= current_time < TSE_MARKET_OPEN


def get_market_session_state(dt: datetime | None = None) -> dict:
    """Returns full market status dictionary with Persian labels and cadence."""
    if dt is None:
        dt = get_tehran_now()
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=TEHRAN_TZ)
    else:
        dt = dt.astimezone(TEHRAN_TZ)

    is_open = is_tse_market_open(dt)
    is_pre = is_tse_premarket(dt)
    is_workday = is_tse_trading_day(dt)

    if is_open:
        status_code = "OPEN"
        status_fa = "بازار باز است (معاملات پیوسته)"
        cadence_seconds = 10  # Ultra-fast 10-second live updates during continuous trading
        auto_trade_interval_minutes = 3  # Run auto-trader every 3 minutes during market hours
    elif is_pre:
        status_code = "PRE_MARKET"
        status_fa = "پیش‌گشایش و حراج اولیه (ثبت سفارش)"
        cadence_seconds = 15
        auto_trade_interval_minutes = 10
    elif is_workday and dt.time() < TSE_PREMARKET_START:
        status_code = "PRE_SESSION"
        status_fa = "قبل از شروع بازار (انتظار برای پیش‌گشایش)"
        cadence_seconds = 60
        auto_trade_interval_minutes = 30
    elif is_workday and dt.time() > TSE_MARKET_CLOSE:
        status_code = "POST_MARKET"
        status_fa = "بسته — تسویه و محاسبات پایانی روز"
        cadence_seconds = 60  # 1 min when market is closed
        auto_trade_interval_minutes = 60
    else:
        status_code = "WEEKEND"
        status_fa = "تعطیلات پایان هفته (پنجشنبه و جمعه)"
        cadence_seconds = 120  # 2 min during weekend
        auto_trade_interval_minutes = 120

    return {
        "status_code": status_code,
        "status_fa": status_fa,
        "is_open": is_open,
        "is_premarket": is_pre,
        "is_workday": is_workday,
        "cadence_seconds": cadence_seconds,
        "auto_trade_interval_minutes": auto_trade_interval_minutes,
        "tehran_time": dt.strftime("%H:%M:%S"),
        "tehran_date": dt.strftime("%Y-%m-%d"),
    }


def get_dynamic_scheduler_cadence_seconds() -> int:
    """
    Returns appropriate sleep interval in seconds based on current market state:
    - Market Open: 900 seconds (15 min) for active scan & trade
    - Market Closed / Weekend: 3600 seconds (60 min) or 7200 seconds (120 min)
    """
    state = get_market_session_state()
    return state["auto_trade_interval_minutes"] * 60
