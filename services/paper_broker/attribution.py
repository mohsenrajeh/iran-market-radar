"""Indicator Performance Attribution System."""
from sqlalchemy.orm import Session
from packages.domain.models import PaperTradeLog, IndicatorPerformance
from packages.shared.datetime_utils import now_utc

# Map indicator & fundamental signals to their feature keys and bullish threshold
INDICATOR_DEFINITIONS = {
    "ema_trend": {"key": "ema_trend_score", "bullish_threshold": 0.5, "name_fa": "روند EMA"},
    "rsi_14": {"key": "rsi_14", "bullish_threshold": 50.0, "name_fa": "شاخص قدرت نسبی (RSI)"},
    "macd_hist": {"key": "macd_hist", "bullish_threshold": 0.0, "name_fa": "هیستوگرام MACD"},
    "supertrend": {"key": "supertrend_direction", "bullish_threshold": 0.5, "name_fa": "سوپرترند"},
    "ichimoku_cloud": {"key": "ichimoku_above_cloud", "bullish_threshold": 0.5, "name_fa": "ابر ایچیموکو"},
    "adx_14": {"key": "adx_14", "bullish_threshold": 25.0, "name_fa": "قدرت روند (ADX)"},
    "mfi_14": {"key": "mfi_14", "bullish_threshold": 50.0, "name_fa": "شاخص جریان پول (MFI)"},
    "obv_slope": {"key": "obv_slope_20d", "bullish_threshold": 0.0, "name_fa": "شیب OBV"},
    "cmf_20": {"key": "cmf_20", "bullish_threshold": 0.0, "name_fa": "جریان پول چایکین"},
    "volume_z": {"key": "vol_z_score_20d", "bullish_threshold": 1.0, "name_fa": "امتیاز حجم غیرعادی"},
    "bb_squeeze": {"key": "bb_squeeze", "bullish_threshold": 0.5, "name_fa": "فشردگی بولینگر"},
    "client_flow": {"key": "real_buyer_power_ratio", "bullish_threshold": 1.1, "name_fa": "قدرت خریدار حقیقی"},
    "stoch_rsi": {"key": "stoch_rsi_k", "bullish_threshold": 20.0, "name_fa": "RSI تصادفی"},
    "williams_r": {"key": "williams_r_14", "bullish_threshold": -50.0, "name_fa": "ویلیامز R%"},
    "cci_20": {"key": "cci_20", "bullish_threshold": 0.0, "name_fa": "CCI"},
    # Fundamental & Codal News Signals
    "codal_sales_growth": {"key": "sales_growth", "bullish_threshold": 25.0, "name_fa": "رشد فروش ماهانه کدال (YoY)"},
    "codal_material_disclosure": {"key": "codal_disclosure_score", "bullish_threshold": 6.0, "name_fa": "افشای بااهمیت سودآور در کدال"},
    "piotroski_f_score": {"key": "piotroski", "bullish_threshold": 7.0, "name_fa": "سلامت ترازنامه (پیوتروسکی)"},
    "valuation_pe_discount": {"key": "pe_discount_ratio", "bullish_threshold": 0.85, "name_fa": "ارزندگی و تخفیف P/E نسبت به صنعت"},
}


def update_indicator_attribution(db: Session, trade_log: PaperTradeLog):
    """After a trade is closed, evaluate which indicators and fundamental signals were correct."""
    features = trade_log.features_at_entry or {}
    is_profitable = trade_log.net_pnl > 0
    indicator_scores = {}
    
    for ind_name, defn in INDICATOR_DEFINITIONS.items():
        key = defn["key"]
        threshold = defn["bullish_threshold"]
        value = features.get(key)
        
        if value is None:
            continue
        
        was_bullish = value >= threshold
        
        # Score: 1.0 if indicator was correct, 0.0 if wrong
        if was_bullish and is_profitable:
            score = 1.0  # Correctly bullish
        elif not was_bullish and not is_profitable:
            score = 1.0  # Correctly bearish/neutral
        else:
            score = 0.0  # Wrong
        
        indicator_scores[ind_name] = score
        
        # Update cumulative performance
        perf = db.query(IndicatorPerformance).filter(
            IndicatorPerformance.indicator_name == ind_name
        ).first()
        
        if not perf:
            perf = IndicatorPerformance(
                indicator_name=ind_name,
                display_name_fa=defn["name_fa"],
                total_signals=0,
                profitable_signals=0,
                loss_signals=0,
                avg_return_when_bullish=0.0,
                avg_return_when_bearish=0.0,
                precision=0.0,
                recall=0.0,
                f1_score=0.0,
                cumulative_pnl=0.0,
            )
            db.add(perf)
        
        perf.total_signals = (perf.total_signals or 0) + 1
        if is_profitable:
            perf.profitable_signals = (perf.profitable_signals or 0) + 1
            # Running average
            n = perf.profitable_signals
            curr_avg = perf.avg_return_when_bullish or 0.0
            perf.avg_return_when_bullish = (
                curr_avg * (n - 1) + trade_log.return_pct
            ) / n
        else:
            perf.loss_signals = (perf.loss_signals or 0) + 1
            n = perf.loss_signals
            curr_avg = perf.avg_return_when_bearish or 0.0
            perf.avg_return_when_bearish = (
                curr_avg * (n - 1) + trade_log.return_pct
            ) / n
        
        perf.cumulative_pnl = (perf.cumulative_pnl or 0.0) + trade_log.net_pnl
        
        # Precision = correct bullish / total bullish signals
        if perf.total_signals > 0:
            perf.precision = perf.profitable_signals / perf.total_signals
        
        perf.last_updated_at = now_utc()
    
    trade_log.indicator_scores = indicator_scores
    db.flush()
