"""Unit tests for Persian normalization, digits, and Jalali formatting."""
from datetime import datetime, timezone
from packages.shared.persian import normalize_persian_text, normalize_ticker, to_persian_digits, to_ascii_digits
from packages.shared.datetime_utils import to_jalali_str, jalali_day_name_fa


def test_normalize_persian_characters():
    raw = "شركت پتروشيمي خليج‌فارس"
    norm = normalize_persian_text(raw)
    assert "ی" in norm
    assert "ک" in norm
    assert "ي" not in norm
    assert "ك" not in norm


def test_normalize_ticker():
    assert normalize_ticker("فولاد ۱") == "فولاد 1"
    assert normalize_ticker("فملی-") == "فملی-"


def test_digit_conversions():
    assert to_persian_digits(12345) == "۱۲۳۴۵"
    assert to_ascii_digits("۱۲۳۴۵") == "12345"


def test_jalali_formatting():
    dt = datetime(2026, 8, 15, 10, 30, tzinfo=timezone.utc)
    j_str = to_jalali_str(dt, include_time=False, persian_digits=False)
    assert j_str.startswith("1405/")
