"""Dynamic price limits, tick sizes, and base volume rules in the Iranian market."""
import math


def calculate_static_limits(
    yesterday_price: float,
    limit_pct: float = 0.05,
    tick_size: float = 1.0,
) -> tuple[float, float]:
    """
    Computes static lower and upper price bounds based on yesterday's closing price.
    In Iran, standard limit is ±5% rounded to tick size.
    """
    if yesterday_price <= 0:
        return 0.0, 0.0

    raw_min = yesterday_price * (1.0 - limit_pct)
    raw_max = yesterday_price * (1.0 + limit_pct)

    # Floor / Ceil to tick size
    allowed_min = math.floor(raw_min / tick_size) * tick_size
    allowed_max = math.ceil(raw_max / tick_size) * tick_size

    return float(allowed_min), float(allowed_max)


def apply_base_volume_rule(
    yesterday_price: float,
    weighted_avg_price: float,
    traded_volume: int,
    base_volume: int | None,
) -> float:
    """
    Computes official closing price (قیمت پایانی) considering Base Volume (حجم مبنا).
    If traded volume < base volume:
    closing_price = yesterday_price + (weighted_avg_price - yesterday_price) * (traded_volume / base_volume)
    """
    if base_volume is None or base_volume <= 0 or traded_volume >= base_volume:
        return weighted_avg_price

    volume_ratio = min(1.0, traded_volume / base_volume)
    price_delta = weighted_avg_price - yesterday_price
    closing_price = yesterday_price + (price_delta * volume_ratio)
    return float(round(closing_price))
