"""Tests for all 12 advanced technical indicators and candlestick pattern recognition."""
import numpy as np
import pytest

from packages.feature_engine.indicators import (
    compute_ichimoku,
    compute_adx,
    compute_supertrend,
    compute_stochastic_rsi,
    compute_williams_r,
    compute_cci,
    compute_mfi,
    compute_obv,
    compute_cmf,
    compute_keltner_channels,
    compute_donchian_channels,
    detect_candlestick_patterns,
    compute_symbol_features,
)


@pytest.fixture
def sample_ohlcv():
    np.random.seed(42)
    n = 100
    base = 10000.0
    returns = np.random.normal(0.001, 0.02, n)
    closes = base * np.cumprod(1 + returns)
    highs = closes * (1 + np.abs(np.random.normal(0.005, 0.01, n)))
    lows = closes * (1 - np.abs(np.random.normal(0.005, 0.01, n)))
    opens = closes * (1 + np.random.normal(0.0, 0.005, n))
    volumes = np.random.randint(100_000, 5_000_000, n).astype(float)
    values = closes * volumes
    return opens, highs, lows, closes, volumes, values


def test_compute_ichimoku(sample_ohlcv):
    opens, highs, lows, closes, volumes, values = sample_ohlcv
    res = compute_ichimoku(highs, lows, closes)
    assert "tenkan_sen" in res
    assert "kijun_sen" in res
    assert "senkou_a" in res
    assert "senkou_b" in res
    assert "chikou_span" in res
    assert len(res["tenkan_sen"]) == len(closes)
    assert res["tenkan_sen"][-1] > 0
    assert res["kijun_sen"][-1] > 0


def test_compute_adx(sample_ohlcv):
    opens, highs, lows, closes, volumes, values = sample_ohlcv
    adx, plus_di, minus_di = compute_adx(highs, lows, closes, period=14)
    assert len(adx) == len(closes)
    assert 0 <= adx[-1] <= 100
    assert plus_di[-1] >= 0
    assert minus_di[-1] >= 0


def test_compute_supertrend(sample_ohlcv):
    opens, highs, lows, closes, volumes, values = sample_ohlcv
    st_line, st_dir = compute_supertrend(highs, lows, closes, period=10, multiplier=3.0)
    assert len(st_line) == len(closes)
    assert len(st_dir) == len(closes)
    assert st_dir[-1] in (1.0, -1.0)


def test_compute_stochastic_rsi(sample_ohlcv):
    opens, highs, lows, closes, volumes, values = sample_ohlcv
    k, d = compute_stochastic_rsi(closes)
    assert len(k) == len(closes)
    assert len(d) == len(closes)
    assert 0 <= k[-1] <= 100
    assert 0 <= d[-1] <= 100


def test_compute_williams_r(sample_ohlcv):
    opens, highs, lows, closes, volumes, values = sample_ohlcv
    wr = compute_williams_r(highs, lows, closes, period=14)
    assert len(wr) == len(closes)
    assert -100 <= wr[-1] <= 0


def test_compute_cci(sample_ohlcv):
    opens, highs, lows, closes, volumes, values = sample_ohlcv
    cci = compute_cci(highs, lows, closes, period=20)
    assert len(cci) == len(closes)
    assert not np.isnan(cci[-1])


def test_compute_mfi(sample_ohlcv):
    opens, highs, lows, closes, volumes, values = sample_ohlcv
    mfi = compute_mfi(highs, lows, closes, volumes, period=14)
    assert len(mfi) == len(closes)
    assert 0 <= mfi[-1] <= 100


def test_compute_obv_and_cmf(sample_ohlcv):
    opens, highs, lows, closes, volumes, values = sample_ohlcv
    obv = compute_obv(closes, volumes)
    assert len(obv) == len(closes)

    cmf = compute_cmf(highs, lows, closes, volumes, period=20)
    assert len(cmf) == len(closes)
    assert -1.0 <= cmf[-1] <= 1.0


def test_compute_channels(sample_ohlcv):
    opens, highs, lows, closes, volumes, values = sample_ohlcv
    ku, km, kl = compute_keltner_channels(highs, lows, closes)
    assert len(ku) == len(closes)
    assert ku[-1] >= km[-1] >= kl[-1]

    du, dl = compute_donchian_channels(highs, lows, period=20)
    assert len(du) == len(closes)
    assert du[-1] >= dl[-1]


def test_candlestick_patterns(sample_ohlcv):
    opens, highs, lows, closes, volumes, values = sample_ohlcv
    patterns = detect_candlestick_patterns(opens, highs, lows, closes)
    assert "hammer" in patterns
    assert "bullish_engulfing" in patterns
    assert "bearish_engulfing" in patterns
    assert "doji" in patterns
    assert "morning_star" in patterns
    assert len(patterns["doji"]) == len(closes)


def test_compute_symbol_features_full(sample_ohlcv):
    opens, highs, lows, closes, volumes, values = sample_ohlcv
    bars = [
        {
            "trading_date": f"2026-01-{i+1:02d}",
            "open": opens[i],
            "high": highs[i],
            "low": lows[i],
            "close": closes[i],
            "last": closes[i],
            "volume": volumes[i],
            "value": values[i],
            "trade_count": 500,
        }
        for i in range(len(closes))
    ]
    ct = [
        {
            "trading_date": f"2026-01-{i+1:02d}",
            "real_buy_count": 100,
            "real_buy_value": 500_000_000,
            "real_sell_count": 120,
            "real_sell_value": 300_000_000,
            "legal_buy_value": 100_000_000,
            "legal_sell_value": 300_000_000,
        }
        for i in range(len(closes))
    ]
    feats = compute_symbol_features(bars, ct)
    assert "ichimoku_tenkan" in feats
    assert "adx_14" in feats
    assert "supertrend_direction" in feats
    assert "stoch_rsi_k" in feats
    assert "williams_r_14" in feats
    assert "cci_20" in feats
    assert "mfi_14" in feats
    assert "bb_squeeze" in feats
    assert "real_buyer_power_ratio" in feats
    assert feats["real_buyer_power_ratio"] > 1.0
