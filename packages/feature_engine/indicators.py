"""Deterministic technical, volume, and client-flow indicator computations."""
import numpy as np
import polars as pl


def compute_ema(series: np.ndarray, period: int) -> np.ndarray:
    """Computes Exponential Moving Average (EMA)."""
    alpha = 2.0 / (period + 1.0)
    out = np.zeros_like(series, dtype=float)
    if len(series) == 0:
        return out
    out[0] = series[0]
    for i in range(1, len(series)):
        out[i] = alpha * series[i] + (1.0 - alpha) * out[i - 1]
    return out


def compute_sma(series: np.ndarray, period: int) -> np.ndarray:
    """Computes Simple Moving Average (SMA)."""
    n = len(series)
    out = np.zeros_like(series, dtype=float)
    for i in range(n):
        start_idx = max(0, i - period + 1)
        out[i] = float(np.mean(series[start_idx : i + 1]))
    return out


def compute_atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
    """Computes Average True Range (ATR)."""
    n = len(close)
    if n == 0:
        return np.array([])
    tr = np.zeros(n, dtype=float)
    tr[0] = high[0] - low[0]
    for i in range(1, n):
        tr[i] = max(
            high[i] - low[i],
            abs(high[i] - close[i - 1]),
            abs(low[i] - close[i - 1]),
        )
    return compute_ema(tr, period)


def compute_rsi(close: np.ndarray, period: int = 14) -> np.ndarray:
    """Computes Relative Strength Index (RSI 14)."""
    n = len(close)
    rsi = np.full(n, 50.0, dtype=float)
    if n < 2:
        return rsi

    deltas = np.diff(close)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    avg_gain = np.zeros(n, dtype=float)
    avg_loss = np.zeros(n, dtype=float)

    if n > period:
        avg_gain[period] = np.mean(gains[:period])
        avg_loss[period] = np.mean(losses[:period])

        for i in range(period + 1, n):
            avg_gain[i] = (avg_gain[i - 1] * (period - 1) + gains[i - 1]) / period
            avg_loss[i] = (avg_loss[i - 1] * (period - 1) + losses[i - 1]) / period

        for i in range(period, n):
            if avg_loss[i] == 0:
                rsi[i] = 100.0
            else:
                rs = avg_gain[i] / avg_loss[i]
                rsi[i] = round(float(100.0 - (100.0 / (1.0 + rs))), 2)

    return rsi


def compute_macd(
    close: np.ndarray, fast: int = 12, slow: int = 26, signal_period: int = 9
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Computes MACD Line, Signal Line, and Histogram."""
    ema_fast = compute_ema(close, fast)
    ema_slow = compute_ema(close, slow)
    macd_line = ema_fast - ema_slow
    signal_line = compute_ema(macd_line, signal_period)
    histogram = macd_line - signal_line
    return np.round(macd_line, 2), np.round(signal_line, 2), np.round(histogram, 2)


def compute_bollinger_bands(
    close: np.ndarray, period: int = 20, num_std: float = 2.0
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Computes Upper, Middle, and Lower Bollinger Bands."""
    n = len(close)
    middle = compute_sma(close, period)
    upper = np.zeros_like(close, dtype=float)
    lower = np.zeros_like(close, dtype=float)

    for i in range(n):
        start_idx = max(0, i - period + 1)
        window = close[start_idx : i + 1]
        std = np.std(window) if len(window) > 1 else 0.0
        upper[i] = middle[i] + num_std * std
        lower[i] = middle[i] - num_std * std

    return np.round(upper, 2), np.round(middle, 2), np.round(lower, 2)


def compute_pivot_points(high: float, low: float, close: float) -> dict[str, float]:
    """Computes Classical Floor Pivot Points & S/R Levels."""
    pivot = (high + low + close) / 3.0
    r1 = (2.0 * pivot) - low
    s1 = (2.0 * pivot) - high
    r2 = pivot + (high - low)
    s2 = pivot - (high - low)
    r3 = high + 2.0 * (pivot - low)
    s3 = low - 2.0 * (high - pivot)
    return {
        "pivot": round(pivot),
        "r1": round(r1),
        "r2": round(r2),
        "r3": round(r3),
        "s1": round(s1),
        "s2": round(s2),
        "s3": round(s3),
    }


def compute_robust_volume_zscore(volume: np.ndarray, period: int = 20) -> np.ndarray:
    """
    Computes Robust Volume Z-score using Median and Median Absolute Deviation (MAD).
    Less sensitive to extreme single-day outliers than standard deviation.
    """
    n = len(volume)
    z_scores = np.zeros(n, dtype=float)
    for i in range(n):
        start_idx = max(0, i - period + 1)
        window = volume[start_idx : i + 1]
        if len(window) < 3:
            z_scores[i] = 0.0
            continue
        med = np.median(window)
        mad = np.median(np.abs(window - med))
        if mad > 1e-6:
            z_scores[i] = float(0.6745 * (volume[i] - med) / mad)
        else:
            z_scores[i] = 0.0
    return z_scores


def compute_ichimoku(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, tenkan=9, kijun=26, senkou_b=52) -> dict[str, np.ndarray]:
    n = len(closes)
    tenkan_sen = np.zeros(n, dtype=float)
    kijun_sen = np.zeros(n, dtype=float)
    senkou_a = np.zeros(n, dtype=float)
    senkou_b_arr = np.zeros(n, dtype=float)
    chikou_span = np.zeros(n, dtype=float)

    for i in range(n):
        if i >= tenkan - 1:
            tenkan_sen[i] = (np.max(highs[i - tenkan + 1 : i + 1]) + np.min(lows[i - tenkan + 1 : i + 1])) / 2.0
        else:
            tenkan_sen[i] = (np.max(highs[: i + 1]) + np.min(lows[: i + 1])) / 2.0

        if i >= kijun - 1:
            kijun_sen[i] = (np.max(highs[i - kijun + 1 : i + 1]) + np.min(lows[i - kijun + 1 : i + 1])) / 2.0
        else:
            kijun_sen[i] = (np.max(highs[: i + 1]) + np.min(lows[: i + 1])) / 2.0
            
    senkou_a = (tenkan_sen + kijun_sen) / 2.0
    
    for i in range(n):
        if i >= senkou_b - 1:
            senkou_b_arr[i] = (np.max(highs[i - senkou_b + 1 : i + 1]) + np.min(lows[i - senkou_b + 1 : i + 1])) / 2.0
        else:
            senkou_b_arr[i] = (np.max(highs[: i + 1]) + np.min(lows[: i + 1])) / 2.0

    senkou_a = np.roll(senkou_a, kijun)
    senkou_a[:kijun] = 0.0
    senkou_b_arr = np.roll(senkou_b_arr, kijun)
    senkou_b_arr[:kijun] = 0.0
    chikou_span = np.roll(closes, -kijun)

    return {
        "tenkan_sen": tenkan_sen,
        "kijun_sen": kijun_sen,
        "senkou_a": senkou_a,
        "senkou_b": senkou_b_arr,
        "chikou_span": chikou_span
    }


def compute_adx(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    n = len(closes)
    plus_dm = np.zeros(n, dtype=float)
    minus_dm = np.zeros(n, dtype=float)
    tr = np.zeros(n, dtype=float)
    
    if n > 0:
        tr[0] = highs[0] - lows[0]
        
    for i in range(1, n):
        up_move = highs[i] - highs[i - 1]
        down_move = lows[i - 1] - lows[i]
        
        if up_move > down_move and up_move > 0:
            plus_dm[i] = up_move
        if down_move > up_move and down_move > 0:
            minus_dm[i] = down_move
            
        tr[i] = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))

    tr_ema = compute_ema(tr, period)
    plus_di = np.zeros(n, dtype=float)
    minus_di = np.zeros(n, dtype=float)
    
    smooth_plus_dm = compute_ema(plus_dm, period)
    smooth_minus_dm = compute_ema(minus_dm, period)

    for i in range(n):
        if tr_ema[i] > 0:
            plus_di[i] = 100.0 * smooth_plus_dm[i] / tr_ema[i]
            minus_di[i] = 100.0 * smooth_minus_dm[i] / tr_ema[i]

    dx = np.zeros(n, dtype=float)
    for i in range(n):
        di_sum = plus_di[i] + minus_di[i]
        if di_sum > 0:
            dx[i] = 100.0 * abs(plus_di[i] - minus_di[i]) / di_sum

    adx = compute_ema(dx, period)
    return adx, plus_di, minus_di


def compute_supertrend(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 10, multiplier: float = 3.0) -> tuple[np.ndarray, np.ndarray]:
    n = len(closes)
    atr = compute_atr(highs, lows, closes, period)
    hl2 = (highs + lows) / 2.0
    
    basic_upper = hl2 + multiplier * atr
    basic_lower = hl2 - multiplier * atr
    
    final_upper = np.zeros(n, dtype=float)
    final_lower = np.zeros(n, dtype=float)
    supertrend = np.zeros(n, dtype=float)
    direction = np.ones(n, dtype=float)
    
    if n > 0:
        final_upper[0] = basic_upper[0]
        final_lower[0] = basic_lower[0]
        supertrend[0] = final_lower[0]
    
    for i in range(1, n):
        if basic_upper[i] < final_upper[i - 1] or closes[i - 1] > final_upper[i - 1]:
            final_upper[i] = basic_upper[i]
        else:
            final_upper[i] = final_upper[i - 1]
            
        if basic_lower[i] > final_lower[i - 1] or closes[i - 1] < final_lower[i - 1]:
            final_lower[i] = basic_lower[i]
        else:
            final_lower[i] = final_lower[i - 1]
            
        if supertrend[i - 1] == final_upper[i - 1] and closes[i] <= final_upper[i]:
            supertrend[i] = final_upper[i]
            direction[i] = -1
        elif supertrend[i - 1] == final_upper[i - 1] and closes[i] > final_upper[i]:
            supertrend[i] = final_lower[i]
            direction[i] = 1
        elif supertrend[i - 1] == final_lower[i - 1] and closes[i] >= final_lower[i]:
            supertrend[i] = final_lower[i]
            direction[i] = 1
        elif supertrend[i - 1] == final_lower[i - 1] and closes[i] < final_lower[i]:
            supertrend[i] = final_upper[i]
            direction[i] = -1
            
    return supertrend, direction


def compute_stochastic_rsi(closes: np.ndarray, rsi_period: int = 14, stoch_period: int = 14, k_smooth: int = 3, d_smooth: int = 3) -> tuple[np.ndarray, np.ndarray]:
    n = len(closes)
    rsi = compute_rsi(closes, rsi_period)
    stoch_rsi = np.zeros(n, dtype=float)
    
    for i in range(n):
        start_idx = max(0, i - stoch_period + 1)
        window = rsi[start_idx : i + 1]
        highest = np.max(window)
        lowest = np.min(window)
        if highest != lowest:
            stoch_rsi[i] = 100.0 * (rsi[i] - lowest) / (highest - lowest)
        else:
            stoch_rsi[i] = 0.0
            
    k_line = compute_sma(stoch_rsi, k_smooth)
    d_line = compute_sma(k_line, d_smooth)
    return k_line, d_line


def compute_williams_r(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> np.ndarray:
    n = len(closes)
    williams_r = np.zeros(n, dtype=float)
    
    for i in range(n):
        start_idx = max(0, i - period + 1)
        highest_high = np.max(highs[start_idx : i + 1])
        lowest_low = np.min(lows[start_idx : i + 1])
        
        if highest_high != lowest_low:
            williams_r[i] = -100.0 * (highest_high - closes[i]) / (highest_high - lowest_low)
        else:
            williams_r[i] = -50.0
            
    return williams_r


def compute_cci(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 20) -> np.ndarray:
    n = len(closes)
    cci = np.zeros(n, dtype=float)
    tp = (highs + lows + closes) / 3.0
    
    for i in range(n):
        start_idx = max(0, i - period + 1)
        window = tp[start_idx : i + 1]
        sma_tp = np.mean(window)
        mad = np.mean(np.abs(window - sma_tp))
        if mad > 0:
            cci[i] = (tp[i] - sma_tp) / (0.015 * mad)
        else:
            cci[i] = 0.0
            
    return cci


def compute_mfi(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, volumes: np.ndarray, period: int = 14) -> np.ndarray:
    n = len(closes)
    mfi = np.full(n, 50.0, dtype=float)
    tp = (highs + lows + closes) / 3.0
    rmf = tp * volumes
    
    for i in range(1, n):
        start_idx = max(1, i - period + 1)
        pos_mf = 0.0
        neg_mf = 0.0
        
        for j in range(start_idx, i + 1):
            if tp[j] > tp[j - 1]:
                pos_mf += rmf[j]
            elif tp[j] < tp[j - 1]:
                neg_mf += rmf[j]
                
        if neg_mf == 0:
            mfi[i] = 100.0 if pos_mf > 0 else 50.0
        else:
            mfr = pos_mf / neg_mf
            mfi[i] = 100.0 - (100.0 / (1.0 + mfr))
            
    return mfi


def compute_obv(closes: np.ndarray, volumes: np.ndarray) -> np.ndarray:
    n = len(closes)
    obv = np.zeros(n, dtype=float)
    if n == 0:
        return obv
        
    obv[0] = volumes[0]
    for i in range(1, n):
        if closes[i] > closes[i - 1]:
            obv[i] = obv[i - 1] + volumes[i]
        elif closes[i] < closes[i - 1]:
            obv[i] = obv[i - 1] - volumes[i]
        else:
            obv[i] = obv[i - 1]
            
    return obv


def compute_cmf(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, volumes: np.ndarray, period: int = 20) -> np.ndarray:
    n = len(closes)
    cmf = np.zeros(n, dtype=float)
    mfv = np.zeros(n, dtype=float)
    
    for i in range(n):
        if highs[i] != lows[i]:
            mfm = ((closes[i] - lows[i]) - (highs[i] - closes[i])) / (highs[i] - lows[i])
        else:
            mfm = 0.0
        mfv[i] = mfm * volumes[i]
        
    for i in range(n):
        start_idx = max(0, i - period + 1)
        vol_sum = np.sum(volumes[start_idx : i + 1])
        if vol_sum > 0:
            cmf[i] = np.sum(mfv[start_idx : i + 1]) / vol_sum
            
    return cmf


def compute_keltner_channels(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, ema_period: int = 20, atr_mult: float = 1.5, atr_period: int = 10) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    middle = compute_ema(closes, ema_period)
    atr = compute_atr(highs, lows, closes, atr_period)
    
    upper = middle + (atr_mult * atr)
    lower = middle - (atr_mult * atr)
    
    return upper, middle, lower


def compute_donchian_channels(highs: np.ndarray, lows: np.ndarray, period: int = 20) -> tuple[np.ndarray, np.ndarray]:
    n = len(highs)
    upper = np.zeros(n, dtype=float)
    lower = np.zeros(n, dtype=float)
    
    for i in range(n):
        start_idx = max(0, i - period + 1)
        upper[i] = np.max(highs[start_idx : i + 1])
        lower[i] = np.min(lows[start_idx : i + 1])
        
    return upper, lower


def detect_candlestick_patterns(opens: np.ndarray, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray) -> dict[str, np.ndarray]:
    n = len(closes)
    hammer = np.zeros(n, dtype=bool)
    inverted_hammer = np.zeros(n, dtype=bool)
    bullish_engulfing = np.zeros(n, dtype=bool)
    bearish_engulfing = np.zeros(n, dtype=bool)
    doji = np.zeros(n, dtype=bool)
    morning_star = np.zeros(n, dtype=bool)
    evening_star = np.zeros(n, dtype=bool)
    piercing_line = np.zeros(n, dtype=bool)
    
    for i in range(n):
        o = opens[i]
        h = highs[i]
        l = lows[i]
        c = closes[i]
        
        body = abs(c - o)
        upper_shadow = h - max(o, c)
        lower_shadow = min(o, c) - l
        
        # Doji
        if body <= (h - l) * 0.1:
            doji[i] = True
            
        # Hammer (small body, long lower shadow, small upper shadow)
        if body > 0 and lower_shadow >= 2 * body and upper_shadow <= body * 0.1:
            hammer[i] = True
            
        # Inverted Hammer
        if body > 0 and upper_shadow >= 2 * body and lower_shadow <= body * 0.1:
            inverted_hammer[i] = True
            
        if i >= 1:
            prev_o = opens[i - 1]
            prev_c = closes[i - 1]
            prev_body = abs(prev_c - prev_o)
            
            # Bullish Engulfing
            if prev_c < prev_o and c > o and c >= prev_o and o <= prev_c and body > prev_body:
                bullish_engulfing[i] = True
                
            # Bearish Engulfing
            if prev_c > prev_o and c < o and c <= prev_o and o >= prev_c and body > prev_body:
                bearish_engulfing[i] = True
                
            # Piercing Line
            if prev_c < prev_o and c > o and o < prev_c and c > (prev_o + prev_c) / 2.0 and c < prev_o:
                piercing_line[i] = True
                
        if i >= 2:
            prev_prev_o = opens[i - 2]
            prev_prev_c = closes[i - 2]
            prev_o = opens[i - 1]
            prev_c = closes[i - 1]
            
            # Morning Star
            if prev_prev_c < prev_prev_o and abs(prev_c - prev_o) <= (highs[i - 1] - lows[i - 1]) * 0.1 and c > o and c > (prev_prev_o + prev_prev_c) / 2.0:
                morning_star[i] = True
                
            # Evening Star
            if prev_prev_c > prev_prev_o and abs(prev_c - prev_o) <= (highs[i - 1] - lows[i - 1]) * 0.1 and c < o and c < (prev_prev_o + prev_prev_c) / 2.0:
                evening_star[i] = True
                
    return {
        "hammer": hammer,
        "inverted_hammer": inverted_hammer,
        "bullish_engulfing": bullish_engulfing,
        "bearish_engulfing": bearish_engulfing,
        "doji": doji,
        "morning_star": morning_star,
        "evening_star": evening_star,
        "piercing_line": piercing_line
    }


def compute_symbol_features(
    bars: list[dict],
    client_types: list[dict] | None = None,
) -> dict[str, float]:
    """
    Extracts complete deterministic feature vector for the latest bar in the series.
    Strictly point-in-time: uses only data at or prior to the latest bar.
    """
    if not bars:
        return {}

    n = len(bars)
    closes = np.array([b["close"] for b in bars], dtype=float)
    opens = np.array([b.get("open", b["close"]) for b in bars], dtype=float)
    highs = np.array([b["high"] for b in bars], dtype=float)
    lows = np.array([b["low"] for b in bars], dtype=float)
    volumes = np.array([b["volume"] for b in bars], dtype=float)
    values = np.array([b["value"] for b in bars], dtype=float)

    curr_close = closes[-1]
    
    # 1. Multi-horizon Returns
    def calc_ret(lookback: int) -> float:
        if n > lookback and closes[-1 - lookback] > 0:
            return float((curr_close - closes[-1 - lookback]) / closes[-1 - lookback])
        return 0.0

    ret_1d = calc_ret(1)
    ret_3d = calc_ret(3)
    ret_5d = calc_ret(5)
    ret_20d = calc_ret(20)
    ret_60d = calc_ret(60)
    ret_120d = calc_ret(120)

    # 2. Moving Averages & Trend Stacking
    ema_10 = float(compute_ema(closes, 10)[-1]) if n >= 5 else curr_close
    ema_20 = float(compute_ema(closes, 20)[-1]) if n >= 5 else curr_close
    ema_50 = float(compute_ema(closes, 50)[-1]) if n >= 5 else curr_close
    ema_100 = float(compute_ema(closes, 100)[-1]) if n >= 5 else curr_close

    ema_trend_score = 0.0
    if curr_close > ema_10: ema_trend_score += 0.25
    if ema_10 > ema_20: ema_trend_score += 0.25
    if ema_20 > ema_50: ema_trend_score += 0.25
    if ema_50 >= ema_100: ema_trend_score += 0.25

    # 3. Volatility & ATR
    atr_series = compute_atr(highs, lows, closes, 14)
    atr_14 = float(atr_series[-1]) if len(atr_series) > 0 else float(curr_close * 0.02)
    atr_pct = float((atr_14 / curr_close) * 100.0) if curr_close > 0 else 2.0

    # 4. Breakout & Channel Indicators
    rolling_20_high = float(np.max(highs[-min(n, 20):])) if n > 0 else curr_close
    rolling_20_low = float(np.min(lows[-min(n, 20):])) if n > 0 else curr_close
    dist_to_20_high = float((curr_close - rolling_20_high) / rolling_20_high) if rolling_20_high > 0 else 0.0
    channel_pos_20d = (
        float((curr_close - rolling_20_low) / (rolling_20_high - rolling_20_low))
        if (rolling_20_high - rolling_20_low) > 0 else 0.5
    )

    # 5. Volume Anomaly
    vol_z_20d = float(compute_robust_volume_zscore(volumes, 20)[-1])
    vol_20_mean = float(np.mean(volumes[-min(n, 20):])) if n > 0 else volumes[-1]
    volume_ratio_20d = float(volumes[-1] / vol_20_mean) if vol_20_mean > 0 else 1.0
    avg_turnover_20d = float(np.mean(values[-min(n, 20):])) if n > 0 else values[-1]

    # 6. حقیقی / حقوقی Client Type Flow
    real_buyer_power_ratio = 1.0
    net_real_inflow_pct = 0.0
    real_accumulation_streak = 0

    # 7. New Technical Indicators
    ichimoku = compute_ichimoku(highs, lows, closes)
    adx, plus_di, minus_di = compute_adx(highs, lows, closes)
    st_line, st_dir = compute_supertrend(highs, lows, closes)
    stoch_k, stoch_d = compute_stochastic_rsi(closes)
    will_r = compute_williams_r(highs, lows, closes)
    cci = compute_cci(highs, lows, closes)
    mfi = compute_mfi(highs, lows, closes, volumes)
    obv = compute_obv(closes, volumes)
    cmf = compute_cmf(highs, lows, closes, volumes)
    keltner_u, keltner_m, keltner_l = compute_keltner_channels(highs, lows, closes)
    donchian_u, donchian_l = compute_donchian_channels(highs, lows)
    patterns = detect_candlestick_patterns(opens, highs, lows, closes)

    ichimoku_above_cloud = 1.0 if (curr_close > ichimoku["senkou_a"][-1] and curr_close > ichimoku["senkou_b"][-1]) else 0.0
    
    obv_slope_20d = 0.0
    if n > 1:
        lookback = min(n, 20)
        obv_diff = obv[-1] - obv[-lookback]
        avg_vol = np.mean(volumes[-lookback:])
        obv_slope_20d = float(obv_diff / (avg_vol * lookback)) if avg_vol > 0 else 0.0
        
    bb_u, bb_m, bb_l = compute_bollinger_bands(closes, 20)
    bb_squeeze = 1.0 if (bb_u[-1] < keltner_u[-1] and bb_l[-1] > keltner_l[-1]) else 0.0
    
    donchian_breakout = 1.0 if curr_close >= donchian_u[-1] else 0.0

    if client_types and len(client_types) > 0:
        latest_ct = client_types[-1]
        
        real_buy_val = float(latest_ct.get("real_buy_value", 0.0))
        real_buy_cnt = max(1, int(latest_ct.get("real_buy_count", 1)))
        real_sell_val = float(latest_ct.get("real_sell_value", 0.0))
        real_sell_cnt = max(1, int(latest_ct.get("real_sell_count", 1)))

        real_buy_per_capita = real_buy_val / real_buy_cnt
        real_sell_per_capita = real_sell_val / real_sell_cnt

        if real_sell_per_capita > 0:
            real_buyer_power_ratio = float(real_buy_per_capita / real_sell_per_capita)

        total_val = real_buy_val + float(latest_ct.get("legal_buy_value", 0.0))
        if total_val > 0:
            net_real_inflow_pct = float((real_buy_val - real_sell_val) / total_val)

        streak = 0
        for ct in reversed(client_types[-3:]):
            b_val = float(ct.get("real_buy_value", 0.0))
            s_val = float(ct.get("real_sell_value", 0.0))
            if b_val > s_val:
                streak += 1
            else:
                break
        real_accumulation_streak = streak

    return {
        "close": float(curr_close),
        "ret_1d": ret_1d,
        "ret_3d": ret_3d,
        "ret_5d": ret_5d,
        "ret_20d": ret_20d,
        "ret_60d": ret_60d,
        "ret_120d": ret_120d,
        "ema_10": float(ema_10),
        "ema_20": float(ema_20),
        "ema_50": float(ema_50),
        "ema_100": float(ema_100),
        "ema_trend_score": float(ema_trend_score),
        "atr_14": atr_14,
        "atr_pct": atr_pct,
        "dist_to_20_high": dist_to_20_high,
        "channel_pos_20d": channel_pos_20d,
        "vol_z_score_20d": vol_z_20d,
        "volume_ratio_20d": volume_ratio_20d,
        "avg_turnover_20d": avg_turnover_20d,
        "real_buyer_power_ratio": real_buyer_power_ratio,
        "net_real_inflow_pct": net_real_inflow_pct,
        "real_accumulation_streak": float(real_accumulation_streak),
        "ichimoku_tenkan": float(ichimoku["tenkan_sen"][-1]),
        "ichimoku_kijun": float(ichimoku["kijun_sen"][-1]),
        "ichimoku_senkou_a": float(ichimoku["senkou_a"][-1]),
        "ichimoku_senkou_b": float(ichimoku["senkou_b"][-1]),
        "ichimoku_above_cloud": float(ichimoku_above_cloud),
        "adx_14": float(adx[-1]),
        "plus_di_14": float(plus_di[-1]),
        "minus_di_14": float(minus_di[-1]),
        "supertrend_direction": float(st_dir[-1]),
        "stoch_rsi_k": float(stoch_k[-1]),
        "stoch_rsi_d": float(stoch_d[-1]),
        "williams_r_14": float(will_r[-1]),
        "cci_20": float(cci[-1]),
        "mfi_14": float(mfi[-1]),
        "obv_slope_20d": float(obv_slope_20d),
        "cmf_20": float(cmf[-1]),
        "keltner_upper": float(keltner_u[-1]),
        "keltner_lower": float(keltner_l[-1]),
        "bb_squeeze": float(bb_squeeze),
        "donchian_upper": float(donchian_u[-1]),
        "donchian_lower": float(donchian_l[-1]),
        "donchian_breakout": float(donchian_breakout),
        "pattern_hammer": float(1.0 if patterns["hammer"][-1] else 0.0),
        "pattern_bullish_engulfing": float(1.0 if patterns["bullish_engulfing"][-1] else 0.0),
        "pattern_bearish_engulfing": float(1.0 if patterns["bearish_engulfing"][-1] else 0.0),
        "pattern_doji": float(1.0 if patterns["doji"][-1] else 0.0),
        "pattern_morning_star": float(1.0 if patterns["morning_star"][-1] else 0.0),
    }
