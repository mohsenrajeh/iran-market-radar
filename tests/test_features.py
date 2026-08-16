"""Unit tests for point-in-time deterministic indicators."""
from packages.feature_engine.indicators import compute_symbol_features


def test_symbol_features_point_in_time():
    # Build synthetic 40 bars
    bars = []
    curr_price = 1000.0
    for i in range(40):
        curr_price += 10.0
        bars.append({
            "trading_date": f"2026-01-{i+1:02d}",
            "open": curr_price - 5,
            "high": curr_price + 15,
            "low": curr_price - 10,
            "close": curr_price,
            "last": curr_price,
            "volume": 1_000_000 + (i * 10_000),
            "value": curr_price * 1_000_000,
        })

    client_types = [
        {
            "trading_date": f"2026-01-{i+1:02d}",
            "real_buy_count": 500,
            "real_buy_volume": 800_000,
            "real_buy_value": 800_000 * curr_price,
            "real_sell_count": 400,
            "real_sell_volume": 600_000,
            "real_sell_value": 600_000 * curr_price,
            "legal_buy_value": 200_000 * curr_price,
            "legal_sell_value": 400_000 * curr_price,
        }
        for i in range(40)
    ]

    features = compute_symbol_features(bars, client_types)
    assert features["ret_1d"] > 0
    assert features["ret_20d"] > 0
    assert features["ema_trend_score"] == 1.0  # Steady uptrend
    assert features["real_buyer_power_ratio"] > 1.0
    assert features["atr_14"] > 0
