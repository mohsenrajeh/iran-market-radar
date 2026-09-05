"""Symbol search, details, candlestick chart, live TSETMC sync, and technical indicators."""
import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from packages.domain.models import Instrument, EODBar, ClientTypeSnapshot, OrderBookSnapshot
from packages.domain.schemas import SymbolChartResponse, BarItem
from packages.feature_engine.indicators import (
    compute_ema,
    compute_sma,
    compute_rsi,
    compute_macd,
    compute_bollinger_bands,
    compute_pivot_points,
    compute_symbol_features,
    compute_ichimoku,
    compute_supertrend,
    compute_adx,
    compute_mfi,
    compute_stochastic_rsi,
    compute_cci,
    compute_williams_r,
    compute_cmf,
)
from packages.data_adapters.tsetmc import TSETMCAdapter
from packages.shared.database import get_sync_db
from packages.shared.datetime_utils import to_jalali_str
from packages.shared.persian import normalize_ticker
from packages.shared.config import settings
from services.collector.trusted_queries import trusted_client_type_query, trusted_eod_query

router = APIRouter(prefix="/symbols", tags=["Symbols & Charts"])


@router.get("")
def list_symbols(q: str | None = None, db: Session = Depends(get_sync_db)):
    """Search symbols by ticker, normalized ticker, or name."""
    query = db.query(Instrument).filter(Instrument.is_active == True)
    if q:
        norm_q = normalize_ticker(q)
        query = query.filter(
            (Instrument.ticker.contains(q)) |
            (Instrument.ticker_normalized.contains(norm_q)) |
            (Instrument.name_fa.contains(q))
        )
    instruments = query.all()
    return [
        {
            "id": inst.id,
            "ticker": inst.ticker,
            "name_fa": inst.name_fa,
            "isin": inst.isin,
            "market": inst.market,
            "board": inst.board,
            "sector": inst.sector.name_fa if inst.sector else None,
        }
        for inst in instruments
    ]


@router.get("/{symbol_or_id}/chart", response_model=SymbolChartResponse)
def get_symbol_chart(symbol_or_id: str, limit: int = Query(120, le=300), db: Session = Depends(get_sync_db)):
    """Returns rich candlestick bars with EMA, Bollinger Bands, RSI, MACD, Ichimoku, Supertrend, MFI, حقیقی/حقوقی flows, and Technical analysis."""
    inst = (
        db.query(Instrument)
        .filter((Instrument.id == symbol_or_id) | (Instrument.ticker == symbol_or_id))
        .first()
    )
    if not inst:
        raise HTTPException(status_code=404, detail="نماد مورد نظر یافت نشد.")
    is_fixture = bool((inst.source_instrument_code or "").startswith("INS_"))
    if settings.market_data_mode != "official" or is_fixture:
        raise HTTPException(status_code=503, detail="نمودار این نماد provenance رسمی ندارد.")

    bars = (
        trusted_eod_query(db, inst.id)
        .order_by(EODBar.trading_date.desc())
        .limit(limit)
        .all()
    )
    bars.reverse()

    if not bars:
        raise HTTPException(status_code=404, detail="تاریخچه رسمی و متصل به batch برای این نماد هنوز تکمیل نشده است.")

    # 1. Compute Array-based Technical Series
    closes = np.array([b.close for b in bars], dtype=float)
    highs = np.array([b.high for b in bars], dtype=float)
    lows = np.array([b.low for b in bars], dtype=float)
    volumes = np.array([b.volume for b in bars], dtype=float)

    ema_20_arr = compute_ema(closes, 20)
    ema_50_arr = compute_ema(closes, 50)
    ema_100_arr = compute_ema(closes, 100)
    bb_u_arr, bb_m_arr, bb_l_arr = compute_bollinger_bands(closes, 20, 2.0)
    rsi_arr = compute_rsi(closes, 14)
    macd_l_arr, macd_s_arr, macd_h_arr = compute_macd(closes, 12, 26, 9)
    vol_ma_20_arr = compute_sma(volumes, 20)

    # Compute advanced indicators
    ichimoku = compute_ichimoku(highs, lows, closes)
    st_line, st_dir = compute_supertrend(highs, lows, closes)
    adx_arr, _, _ = compute_adx(highs, lows, closes)
    mfi_arr = compute_mfi(highs, lows, closes, volumes)
    stoch_k, stoch_d = compute_stochastic_rsi(closes)
    cci_arr = compute_cci(highs, lows, closes)
    will_r_arr = compute_williams_r(highs, lows, closes)
    cmf_arr = compute_cmf(highs, lows, closes, volumes)

    # 2. Client-Type Snapshots (حقیقی و حقوقی)
    ct_snapshots = (
        trusted_client_type_query(db, inst.id)
        .all()
    )
    ct_map = {ct.trading_date: ct for ct in ct_snapshots}

    bar_items = []
    for i, b in enumerate(bars):
        ct = ct_map.get(b.trading_date)
        bp_ratio = None
        r_buy_val = None
        l_buy_val = None
        r_sell_val = None
        l_sell_val = None
        net_flow = None

        if ct:
            r_buy_val = float(ct.real_buy_value)
            l_buy_val = float(ct.legal_buy_value)
            r_sell_val = float(ct.real_sell_value)
            l_sell_val = float(ct.legal_sell_value)
            net_flow = r_buy_val - r_sell_val

            if ct.real_sell_value > 0 and ct.real_sell_count > 0:
                b_per = ct.real_buy_value / max(1, ct.real_buy_count)
                s_per = ct.real_sell_value / max(1, ct.real_sell_count)
                bp_ratio = round(b_per / max(1.0, s_per), 2)

        bar_items.append(
            BarItem(
                date_str=b.trading_date.isoformat(),
                jalali_date=to_jalali_str(b.trading_date, include_time=False, persian_digits=False),
                open=b.open,
                high=b.high,
                low=b.low,
                close=b.close,
                last=b.last,
                volume=b.volume,
                value=b.value,
                trade_count=b.trade_count,
                allowed_min=b.allowed_min,
                allowed_max=b.allowed_max,
                real_buy_power_ratio=bp_ratio,
                ema_20=round(float(ema_20_arr[i]), 1),
                ema_50=round(float(ema_50_arr[i]), 1),
                ema_100=round(float(ema_100_arr[i]), 1),
                bb_upper=round(float(bb_u_arr[i]), 1),
                bb_middle=round(float(bb_m_arr[i]), 1),
                bb_lower=round(float(bb_l_arr[i]), 1),
                rsi_14=round(float(rsi_arr[i]), 1),
                macd=round(float(macd_l_arr[i]), 1),
                macd_signal=round(float(macd_s_arr[i]), 1),
                macd_hist=round(float(macd_h_arr[i]), 1),
                vol_ma_20=round(float(vol_ma_20_arr[i])),
                real_buy_val=r_buy_val,
                legal_buy_val=l_buy_val,
                real_sell_val=r_sell_val,
                legal_sell_val=l_sell_val,
                net_real_inflow=net_flow,
                ichimoku_tenkan=round(float(ichimoku["tenkan_sen"][i]), 1),
                ichimoku_kijun=round(float(ichimoku["kijun_sen"][i]), 1),
                ichimoku_senkou_a=round(float(ichimoku["senkou_a"][i]), 1),
                ichimoku_senkou_b=round(float(ichimoku["senkou_b"][i]), 1),
                supertrend=round(float(st_line[i]), 1),
                supertrend_dir=float(st_dir[i]),
                adx_14=round(float(adx_arr[i]), 1),
                mfi_14=round(float(mfi_arr[i]), 1),
                stoch_rsi_k=round(float(stoch_k[i]), 1),
                stoch_rsi_d=round(float(stoch_d[i]), 1),
                cci_20=round(float(cci_arr[i]), 1),
                williams_r=round(float(will_r_arr[i]), 1),
                cmf_20=round(float(cmf_arr[i]), 3),
            )
        )

    # 3. Compute Key Support & Resistance Pivot Levels
    last_bar = bars[-1]
    pivots = compute_pivot_points(last_bar.high, last_bar.low, last_bar.close)

    resistance = [round(max(highs[-20:])), round(max(highs)), pivots["r1"], pivots["r2"]]
    support = [round(min(lows[-20:])), round(min(lows)), pivots["s1"], pivots["s2"]]

    # 4. Multi-factor Technical Analysis Synthesis (تابلوخوانی و تکنیکال)
    last_close = last_bar.close
    last_rsi = float(rsi_arr[-1])
    last_macd = float(macd_l_arr[-1])
    last_macd_sig = float(macd_s_arr[-1])
    last_bp = bar_items[-1].real_buy_power_ratio

    # Trend Status Badge
    if last_close > ema_20_arr[-1] > ema_50_arr[-1]:
        trend_badge = "روند صعودی پرقدرت (بالای میانگین‌های ۲۰ و ۵۰)"
        trend_state = "bullish"
    elif last_close < ema_20_arr[-1] < ema_50_arr[-1]:
        trend_badge = "روند نزولی (زیر میانگین‌های کوتاه و میان‌مدت)"
        trend_state = "bearish"
    else:
        trend_badge = "روند خنثی / در حال نوسان درون باند بولینگر"
        trend_state = "neutral"

    # RSI Status
    if last_rsi >= 70:
        rsi_badge = f"اشباع خرید (RSI: {last_rsi}) - احتمال استراحت یا اصلاح موقت"
    elif last_rsi <= 30:
        rsi_badge = f"اشباع فروش (RSI: {last_rsi}) - منطقه جذاب واگرایی مثبت"
    else:
        rsi_badge = f"محدوده تعادلی (RSI: {last_rsi})"

    # MACD Status
    if last_macd >= last_macd_sig:
        macd_badge = "سیگنال صعودی MACD (خط مکدی بالای خط سیگنال)"
    else:
        macd_badge = "سیگنال اصلاحی MACD (خط مکدی زیر خط سیگنال)"

    # Client Flow (تابلوخوانی حقیقی/حقوقی)
    if last_bp is None:
        flow_badge = "داده حقیقی/حقوقی معتبر برای این تاریخ ثبت نشده است."
    elif last_bp >= 1.5:
        flow_badge = f"ورود پول هوشمند سنگین حقیقی (قدرت خریدار {last_bp} برابر)"
    elif last_bp >= 1.1:
        flow_badge = f"برتری نسبی خریداران حقیقی ({last_bp} برابر)"
    else:
        flow_badge = f"فشار فروش حقوقی یا برتری نسبی فروشندگان ({last_bp} برابر)"

    technical_analysis = {
        "trend_badge": trend_badge,
        "trend_state": trend_state,
        "rsi_val": last_rsi,
        "rsi_badge": rsi_badge,
        "macd_badge": macd_badge,
        "power_ratio": last_bp,
        "flow_badge": flow_badge,
        "pivot_points": pivots,
        "key_reasons_fa": [
            f"قیمت پایانی: {last_close:,.0f} ریال (فاصله تا سقف ۲۰ روزه: {((last_close - pivots['r1']) / pivots['r1'] * 100):.1f}٪)",
            f"میانگین ۲۰ روزه (EMA 20): {ema_20_arr[-1]:,.0f} ریال | باند بولینگر بالا: {bb_u_arr[-1]:,.0f} ریال",
            f"محدوده حمایت اول (S1): {pivots['s1']:,} ریال | مقاومت اول (R1): {pivots['r1']:,} ریال",
            flow_badge,
        ],
    }

    latest_orderbook = (
        db.query(OrderBookSnapshot)
        .filter(OrderBookSnapshot.instrument_id == inst.id)
        .order_by(OrderBookSnapshot.source_timestamp.desc())
        .first()
    )
    orderbook = list(latest_orderbook.depth_levels or []) if latest_orderbook else []

    return SymbolChartResponse(
        symbol=inst.ticker,
        name_fa=inst.name_fa,
        isin=inst.isin,
        market=inst.market,
        sector=inst.sector.name_fa if inst.sector else None,
        bars=bar_items,
        resistance_levels=resistance,
        support_levels=support,
        technical_analysis=technical_analysis,
        orderbook_depth=orderbook,
    )


@router.post("/{symbol_or_id}/sync-live")
async def sync_symbol_live(symbol_or_id: str, db: Session = Depends(get_sync_db)):
    """Fetches real-time live market updates from TSETMC web service for this symbol."""
    inst = (
        db.query(Instrument)
        .filter((Instrument.id == symbol_or_id) | (Instrument.ticker == symbol_or_id))
        .first()
    )
    if not inst:
        raise HTTPException(status_code=404, detail="نماد مورد نظر یافت نشد.")

    # Fetch only from the official TSETMC live service; never label EOD as live.
    tsetmc = TSETMCAdapter()
    last_price = None
    close_price = None
    volume = None
    
    try:
        watch = await tsetmc.fetch_market_watch()
        match = next((item for item in (watch or []) if item.get("lVal18AFC") == inst.isin or item.get("lVal30") == inst.ticker), None)
        if match:
            last_price = float(match.get("pDrCotVal", 0.0))
            close_price = float(match.get("pClosing", 0.0))
            volume = int(match.get("qTotTran5J", 0))
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"دریافت زنده TSETMC ناموفق بود: {exc.__class__.__name__}") from exc

    if not last_price:
        raise HTTPException(status_code=503, detail="TSETMC برای این نماد snapshot زنده معتبر برنگرداند.")

    return {
        "success": True,
        "symbol": inst.ticker,
        "last_price": last_price,
        "close_price": close_price,
        "volume": volume,
        "message": f"داده‌های زنده نماد {inst.ticker} با موفقیت از سرور TSETMC همگام‌سازی و بروزرسانی شد.",
    }
