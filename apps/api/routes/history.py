"""Closed Trade History API routes, multi-filter search, server pagination, and accounting export."""
import csv
import io
from datetime import datetime, timezone, timedelta
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, desc, asc

from packages.domain.models import (
    ClosedTradeHistory,
    TradeExecutionTimeline,
    TradePostMortem,
    StructuredLesson,
    Portfolio,
    Position,
    Instrument,
    EODBar,
    TradeExitReason,
    TradeOutcomeStatus,
)
from packages.domain.schemas import (
    ClosedTradeResponse,
    ClosedTradeDetailResponse,
    TradeExecutionTimelineItem,
    TradePostMortemResponse,
    PaginatedClosedTradesResponse,
    HistorySummaryResponse,
)
from packages.shared.database import get_sync_db
from packages.shared.datetime_utils import now_utc, to_jalali_str
from services.paper_broker.learning_engine import learning_engine

router = APIRouter(prefix="/trade-history", tags=["Closed Trade History"])


def _seed_initial_closed_trades_if_empty(db: Session):
    """Populates diverse historical closed trades with complete execution timelines and post-mortems if empty."""
    count = db.query(ClosedTradeHistory).count()
    if count >= 10:
        return

    port = db.query(Portfolio).first()
    if not port:
        port = Portfolio(
            id="port_default_paper",
            name="پورتفوی آزمایشی پیش‌فرض (۱ میلیارد تومان)",
            mode="paper",
            cash=10_000_000_000.0,
            initial_cash=10_000_000_000.0,
        )
        db.add(port)
        db.commit()

    base_time = now_utc() - timedelta(days=60)
    seed_records = [
        {
            "symbol": "فولاد", "company": "فولاد مبارکه اصفهان", "sector": "فلزات اساسی",
            "strategy": "s01_momentum", "strategy_fa": "مومنتوم مقطعی", "strategy_ver": "v1.0",
            "open_days_ago": 45, "close_days_ago": 38, "holding_sessions": 7,
            "planned_entry": 5240.0, "avg_entry": 5260.0, "avg_exit": 5850.0, "qty": 150_000,
            "initial_stop": 4980.0, "final_stop": 5400.0, "target1": 5750.0, "target2": 6100.0,
            "exit_reason": "TARGET_1", "exit_reason_fa": "اصابت تارگت اول (+۱۱.۲٪)",
            "regime_entry": "risk_on", "regime_exit": "risk_on",
            "mfe": 12.8, "mae": 1.4, "decision_method": "شکست مقاومت با تایید حجم ۳x",
        },
        {
            "symbol": "فملی", "company": "ملی صنایع مس ایران", "sector": "فلزات اساسی",
            "strategy": "s03_breakout", "strategy_fa": "شکست حجم و نوسان", "strategy_ver": "v1.0",
            "open_days_ago": 40, "close_days_ago": 32, "holding_sessions": 8,
            "planned_entry": 7080.0, "avg_entry": 7100.0, "avg_exit": 7950.0, "qty": 110_000,
            "initial_stop": 6720.0, "final_stop": 7350.0, "target1": 7780.0, "target2": 8250.0,
            "exit_reason": "TRAILING_STOP", "exit_reason_fa": "خروج با تریلینگ‌استاپ بعد از رشد +۱۲.۰٪",
            "regime_entry": "risk_on", "regime_exit": "risk_on",
            "mfe": 14.5, "mae": 1.1, "decision_method": "شکست فشردگی بولینگر با حجم غیرعادی",
        },
        {
            "symbol": "شپنا", "company": "پالایش نفت اصفهان", "sector": "فرآورده‌های نفتی",
            "strategy": "s05_reversion", "strategy_fa": "بازگشت به میانگین انتخابی", "strategy_ver": "v1.0",
            "open_days_ago": 35, "close_days_ago": 30, "holding_sessions": 5,
            "planned_entry": 4600.0, "avg_entry": 4610.0, "avg_exit": 4380.0, "qty": 180_000,
            "initial_stop": 4370.0, "final_stop": 4370.0, "target1": 5050.0, "target2": 5300.0,
            "exit_reason": "STOP_LOSS", "exit_reason_fa": "اصابت دقیق حد ضرر مجاز (-۵.۰٪)",
            "regime_entry": "neutral", "regime_exit": "risk_off",
            "mfe": 1.8, "mae": 5.1, "decision_method": "واگرایی RSI در کف کانال دونچیان",
        },
        {
            "symbol": "نوری", "company": "پتروشیمی نوری", "sector": "محصولات شیمیایی",
            "strategy": "s07_client_flow", "strategy_fa": "جریان پول هوشمند و تجمیع حقیقی", "strategy_ver": "v1.0",
            "open_days_ago": 28, "close_days_ago": 16, "holding_sessions": 12,
            "planned_entry": 24350.0, "avg_entry": 24400.0, "avg_exit": 26900.0, "qty": 35_000,
            "initial_stop": 23100.0, "final_stop": 25500.0, "target1": 26900.0, "target2": 28500.0,
            "exit_reason": "TARGET_1", "exit_reason_fa": "اصابت تارگت اول نهایی (+۱۰.۲٪)",
            "regime_entry": "risk_on", "regime_exit": "risk_on",
            "mfe": 11.5, "mae": 0.8, "decision_method": "قدرت خریدار حقیقی بالای ۲.۴x و انباشت ۴ روزه",
        },
        {
            "symbol": "کچاد", "company": "معدنی و صنعتی چادرملو", "sector": "استخراج کانه‌های فلزی",
            "strategy": "s08_ichimoku", "strategy_fa": "ایچیموکو — روند ابری", "strategy_ver": "v1.0",
            "open_days_ago": 22, "close_days_ago": 14, "holding_sessions": 8,
            "planned_entry": 4380.0, "avg_entry": 4390.0, "avg_exit": 4850.0, "qty": 180_000,
            "initial_stop": 4150.0, "final_stop": 4550.0, "target1": 4800.0, "target2": 5100.0,
            "exit_reason": "TARGET_1", "exit_reason_fa": "اصابت تارگت اول (+۱۰.۵٪)",
            "regime_entry": "risk_on", "regime_exit": "neutral",
            "mfe": 11.8, "mae": 1.2, "decision_method": "شکست ابر کومو و کراس تنکان-کیجون با ADX>28",
        },
        {
            "symbol": "وغدیر", "company": "سرمایه‌گذاری غدیر", "sector": "سرمایه‌گذاری‌ها",
            "strategy": "s02_trend", "strategy_fa": "روند سری زمانی", "strategy_ver": "v1.0",
            "open_days_ago": 20, "close_days_ago": 17, "holding_sessions": 3,
            "planned_entry": 18200.0, "avg_entry": 18250.0, "avg_exit": 17280.0, "qty": 45_000,
            "initial_stop": 17250.0, "final_stop": 17250.0, "target1": 20100.0, "target2": 21500.0,
            "exit_reason": "STOP_LOSS", "exit_reason_fa": "اصابت حد ضرر به علت چرخش منفی شاخص",
            "regime_entry": "neutral", "regime_exit": "risk_off",
            "mfe": 1.2, "mae": 5.3, "decision_method": "شکست میانگین متحرک ۲۰ روزه",
        },
        {
            "symbol": "وبملت", "company": "بانک ملت", "sector": "بانک‌ها و مؤسسات اعتباری",
            "strategy": "s06_volume", "strategy_fa": "ناهنجاری حجم معاملات", "strategy_ver": "v1.0",
            "open_days_ago": 18, "close_days_ago": 10, "holding_sessions": 8,
            "planned_entry": 2450.0, "avg_entry": 2460.0, "avg_exit": 2720.0, "qty": 350_000,
            "initial_stop": 2320.0, "final_stop": 2550.0, "target1": 2720.0, "target2": 2900.0,
            "exit_reason": "TARGET_1", "exit_reason_fa": "اصابت تارگت اول (+۱۰.۶٪)",
            "regime_entry": "risk_on", "regime_exit": "risk_on",
            "mfe": 11.4, "mae": 1.0, "decision_method": "ورود پول سنگین با نسبت خریدار ۲.۱x",
        },
        {
            "symbol": "خودرو", "company": "ایران خودرو", "sector": "خودرو و ساخت قطعات",
            "strategy": "s10_bb_squeeze", "strategy_fa": "فشردگی بولینگر — انفجار نوسان", "strategy_ver": "v1.0",
            "open_days_ago": 14, "close_days_ago": 8, "holding_sessions": 6,
            "planned_entry": 2850.0, "avg_entry": 2860.0, "avg_exit": 3150.0, "qty": 250_000,
            "initial_stop": 2720.0, "final_stop": 2980.0, "target1": 3120.0, "target2": 3350.0,
            "exit_reason": "TARGET_1", "exit_reason_fa": "اصابت تارگت اول (+۱۰.۱٪)",
            "regime_entry": "risk_on", "regime_exit": "risk_on",
            "mfe": 11.2, "mae": 1.3, "decision_method": "شکست کانال کلتنر با سیگنال سوپرترند صعودی",
        },
        {
            "symbol": "زاگرس", "company": "پتروشیمی زاگرس", "sector": "محصولات شیمیایی",
            "strategy": "s11_confluence", "strategy_fa": "تأیید چندگانه اندیکاتوری", "strategy_ver": "v1.0",
            "open_days_ago": 12, "close_days_ago": 6, "holding_sessions": 6,
            "planned_entry": 132000.0, "avg_entry": 132200.0, "avg_exit": 146000.0, "qty": 6_000,
            "initial_stop": 126000.0, "final_stop": 138000.0, "target1": 145000.0, "target2": 155000.0,
            "exit_reason": "TARGET_1", "exit_reason_fa": "اصابت تارگت اول با همگرایی ۷ اندیکاتور",
            "regime_entry": "risk_on", "regime_exit": "risk_on",
            "mfe": 11.8, "mae": 0.8, "decision_method": "تایید همزمان ۷ اندیکاتور مستقل (RSI, MACD, OBV, Ichimoku, CMF)",
        },
        {
            "symbol": "فارس", "company": "صنایع پتروشیمی خلیج فارس", "sector": "محصولات شیمیایی",
            "strategy": "s09_sector_rotation", "strategy_fa": "چرخش و همگرایی صنعت", "strategy_ver": "v1.0",
            "open_days_ago": 10, "close_days_ago": 3, "holding_sessions": 7,
            "planned_entry": 11400.0, "avg_entry": 11450.0, "avg_exit": 11600.0, "qty": 70_000,
            "initial_stop": 10900.0, "final_stop": 11400.0, "target1": 12600.0, "target2": 13400.0,
            "exit_reason": "TIME_STOP", "exit_reason_fa": "خروج بر اساس زمان (عدم حرکت پس از ۷ جلسه)",
            "regime_entry": "neutral", "regime_exit": "neutral",
            "mfe": 2.5, "mae": 1.5, "decision_method": "پیشتازی گروه پتروشیمی در نرخ بازده هفتگی",
        },
        {
            "symbol": "حکشتی", "company": "کشتیرانی جمهوری اسلامی ایران", "sector": "حمل و نقل",
            "strategy": "s12_smart_money_divergence", "strategy_fa": "واگرایی پول هوشمند", "strategy_ver": "v1.0",
            "open_days_ago": 8, "close_days_ago": 2, "holding_sessions": 6,
            "planned_entry": 14500.0, "avg_entry": 14550.0, "avg_exit": 16100.0, "qty": 50_000,
            "initial_stop": 13900.0, "final_stop": 15200.0, "target1": 15900.0, "target2": 17000.0,
            "exit_reason": "TARGET_1", "exit_reason_fa": "اصابت تارگت اول (+۱۰.۶٪)",
            "regime_entry": "risk_on", "regime_exit": "risk_on",
            "mfe": 11.2, "mae": 0.7, "decision_method": "واگرایی صعودی OBV و MFI در برابر افت قیمت ۵ روزه",
        },
    ]

    for rec in seed_records:
        opened_dt = now_utc() - timedelta(days=rec["open_days_ago"])
        closed_dt = now_utc() - timedelta(days=rec["close_days_ago"])
        holding_h = (closed_dt - opened_dt).total_seconds() / 3600.0

        buy_val = rec["avg_entry"] * rec["qty"]
        sell_val = rec["avg_exit"] * rec["qty"]
        entry_fee = buy_val * 0.003712
        exit_fee = sell_val * 0.003850
        tax_val = sell_val * 0.005000
        slip_cost = abs(rec["avg_entry"] - rec["planned_entry"]) * rec["qty"]
        total_costs = entry_fee + exit_fee + tax_val

        gross_pnl = sell_val - buy_val
        net_pnl = gross_pnl - total_costs
        net_ret = (net_pnl / buy_val) * 100.0

        # R calculation
        r_unit = max(1.0, rec["avg_entry"] - rec["initial_stop"])
        realized_r = round((rec["avg_exit"] - rec["avg_entry"]) / r_unit, 2)

        if net_pnl > 0:
            outcome = "WIN"
        elif net_pnl < -100_000:
            outcome = "LOSS"
        else:
            outcome = "BREAKEVEN"

        trade = ClosedTradeHistory(
            portfolio_id=port.id,
            symbol=rec["symbol"],
            company_name=rec["company"],
            sector=rec["sector"],
            strategy_id=rec["strategy"],
            strategy_name_fa=rec["strategy_fa"],
            strategy_version=rec["strategy_ver"],
            model_version="v2.4-isotonic-brier",
            risk_policy_version="POL-TSE-2026-V2.5",
            market_rules_version="TSE-RULES-2026-V1.0",
            dataset_version="tse-pit-2026-08",
            decision_method=rec["decision_method"],
            opened_at=opened_dt,
            closed_at=closed_dt,
            holding_sessions=rec["holding_sessions"],
            holding_duration_hours=round(holding_h, 1),
            planned_entry=rec["planned_entry"],
            avg_entry_price=rec["avg_entry"],
            avg_exit_price=rec["avg_exit"],
            total_quantity=rec["qty"],
            gross_buy_value=buy_val,
            gross_sell_value=sell_val,
            entry_fees=entry_fee,
            exit_fees=exit_fee,
            tax=tax_val,
            slippage_cost=slip_cost,
            total_cost=total_costs,
            gross_pnl=gross_pnl,
            net_pnl=net_pnl,
            net_return_pct=round(net_ret, 2),
            initial_risk_amount=buy_val * 0.04,
            initial_risk_pct_nav=0.35,
            realized_R=realized_r,
            MFE=rec["mfe"],
            MAE=rec["mae"],
            initial_stop=rec["initial_stop"],
            final_stop=rec["final_stop"],
            target1=rec["target1"],
            target2=rec["target2"],
            exit_reason=rec["exit_reason"],
            exit_reason_detail=rec["exit_reason_fa"],
            market_regime_at_entry=rec["regime_entry"],
            market_regime_at_exit=rec["regime_exit"],
            portfolio_nav_at_entry=100_000_000_000.0,
            portfolio_nav_at_exit=100_000_000_000.0 + net_pnl,
            position_weight_at_entry=round(buy_val / 100_000_000_000.0, 3),
            outcome_status=outcome,
            reason_fa=f"سیگنال {rec['strategy_fa']} در نماد {rec['symbol']} با تصمیم {rec['decision_method']}",
            lesson_fa=f"معامله با بازده خالص {net_ret:+.2f}٪ ({realized_r:+.2f}R) بسته شد.",
        )
        db.add(trade)
        db.flush()

        # Seed Execution Timeline
        t1 = TradeExecutionTimeline(
            trade_id=trade.id,
            event_type="SIGNAL_TRIGGER",
            timestamp=opened_dt - timedelta(minutes=15),
            price=rec["planned_entry"],
            quantity=0,
            portion_pct=0.0,
            fees=0.0,
            notes_fa=f"صدور سیگنال معتبر {rec['strategy_fa']}",
        )
        t2 = TradeExecutionTimeline(
            trade_id=trade.id,
            event_type="ENTRY_FILL",
            timestamp=opened_dt,
            price=rec["avg_entry"],
            quantity=int(rec["qty"] * 0.50),
            portion_pct=50.0,
            fees=entry_fee * 0.50,
            notes_fa="اجرای پله اول خرید (۵۰٪ حجم تخصیصی)",
        )
        t3 = TradeExecutionTimeline(
            trade_id=trade.id,
            event_type="SCALE_IN_FILL",
            timestamp=opened_dt + timedelta(days=1),
            price=rec["avg_entry"] * 1.005,
            quantity=int(rec["qty"] * 0.50),
            portion_pct=50.0,
            fees=entry_fee * 0.50,
            notes_fa="تکمیل پله دوم خرید پس از تثبیت قیمت",
        )
        t4 = TradeExecutionTimeline(
            trade_id=trade.id,
            event_type="STOP_ADJUST",
            timestamp=opened_dt + timedelta(days=3),
            price=rec["final_stop"],
            quantity=0,
            portion_pct=0.0,
            fees=0.0,
            notes_fa=f"انتقال استاپ به {rec['final_stop']:,.0f} ریال (حفاظت از سود)",
        )
        t5 = TradeExecutionTimeline(
            trade_id=trade.id,
            event_type="FINAL_EXIT_FILL",
            timestamp=closed_dt,
            price=rec["avg_exit"],
            quantity=rec["qty"],
            portion_pct=100.0,
            fees=exit_fee + tax_val,
            notes_fa=rec["exit_reason_fa"],
        )
        db.add_all([t1, t2, t3, t4, t5])
        db.flush()

        # Generate Post-Mortem & Structured Lessons
        learning_engine.generate_post_mortem(db, trade)

    db.commit()


# ── Endpoints ───────────────────────────────────────────────────────────


@router.get("/summary", response_model=HistorySummaryResponse)
def get_trade_history_summary(db: Session = Depends(get_sync_db)):
    """Returns top summary metrics for all closed trades."""
    _seed_initial_closed_trades_if_empty(db)

    trades = db.query(ClosedTradeHistory).all()
    if not trades:
        return HistorySummaryResponse(
            total_closed_trades=0, wins=0, losses=0, breakevens=0, win_rate_pct=0.0,
            net_pnl_rials=0.0, net_pnl_tomans=0.0, gross_pnl_rials=0.0, avg_return_pct=0.0,
            avg_R=0.0, median_R=0.0, profit_factor=0.0, expectancy_R=0.0, avg_holding_sessions=0.0,
            best_trade_return_pct=0.0, best_trade_symbol="", worst_trade_return_pct=0.0, worst_trade_symbol="",
            total_fees_paid_tomans=0.0, total_slippage_cost_tomans=0.0
        )

    total_count = len(trades)
    wins = [t for t in trades if t.net_pnl > 0]
    losses = [t for t in trades if t.net_pnl < 0]
    breakevens = [t for t in trades if t.net_pnl == 0]

    win_rate = (len(wins) / total_count) * 100.0 if total_count > 0 else 0.0
    net_pnl_sum = sum(t.net_pnl for t in trades)
    gross_pnl_sum = sum(t.gross_pnl for t in trades)
    avg_ret = sum(t.net_return_pct for t in trades) / total_count
    avg_r = sum(t.realized_R for t in trades) / total_count

    r_values = sorted(t.realized_R for t in trades)
    median_r = r_values[len(r_values) // 2] if r_values else 0.0

    total_gross_win = sum(t.net_pnl for t in wins)
    total_gross_loss = abs(sum(t.net_pnl for t in losses))
    profit_factor = (total_gross_win / total_gross_loss) if total_gross_loss > 0 else 9.99

    avg_win_r = sum(t.realized_R for t in wins) / max(len(wins), 1)
    avg_loss_r = sum(t.realized_R for t in losses) / max(len(losses), 1)
    p_win = len(wins) / total_count
    p_loss = len(losses) / total_count
    expectancy = (p_win * avg_win_r) + (p_loss * avg_loss_r)

    avg_holding = sum(t.holding_sessions for t in trades) / total_count
    best_trade = max(trades, key=lambda t: t.net_return_pct)
    worst_trade = min(trades, key=lambda t: t.net_return_pct)

    total_fees = sum(t.total_cost for t in trades)
    total_slip = sum(t.slippage_cost for t in trades)

    return HistorySummaryResponse(
        total_closed_trades=total_count,
        wins=len(wins),
        losses=len(losses),
        breakevens=len(breakevens),
        win_rate_pct=round(win_rate, 1),
        net_pnl_rials=round(net_pnl_sum),
        net_pnl_tomans=round(net_pnl_sum / 10.0),
        gross_pnl_rials=round(gross_pnl_sum),
        avg_return_pct=round(avg_ret, 2),
        avg_R=round(avg_r, 2),
        median_R=round(median_r, 2),
        profit_factor=round(profit_factor, 2),
        expectancy_R=round(expectancy, 2),
        avg_holding_sessions=round(avg_holding, 1),
        best_trade_return_pct=round(best_trade.net_return_pct, 2),
        best_trade_symbol=best_trade.symbol,
        worst_trade_return_pct=round(worst_trade.net_return_pct, 2),
        worst_trade_symbol=worst_trade.symbol,
        total_fees_paid_tomans=round(total_fees / 10.0),
        total_slippage_cost_tomans=round(total_slip / 10.0),
    )


@router.get("/trades", response_model=PaginatedClosedTradesResponse)
def get_closed_trades_paginated(
    symbol: str | None = None,
    strategy_id: str | None = None,
    strategy_version: str | None = None,
    sector: str | None = None,
    outcome: str | None = None,  # WIN, LOSS, BREAKEVEN
    exit_reason: str | None = None,
    market_regime: str | None = None,
    search: str | None = None,
    sort_by: str = Query("closed_at", enum=["opened_at", "closed_at", "net_return_pct", "net_pnl", "realized_R", "holding_sessions", "MFE", "MAE"]),
    sort_order: str = Query("desc", enum=["asc", "desc"]),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=5, le=200),
    db: Session = Depends(get_sync_db),
):
    """Server-side paginated and filtered historical closed trades."""
    _seed_initial_closed_trades_if_empty(db)

    query = db.query(ClosedTradeHistory)

    if symbol:
        query = query.filter(ClosedTradeHistory.symbol == symbol)
    if strategy_id:
        query = query.filter(ClosedTradeHistory.strategy_id == strategy_id)
    if strategy_version:
        query = query.filter(ClosedTradeHistory.strategy_version == strategy_version)
    if sector:
        query = query.filter(ClosedTradeHistory.sector == sector)
    if outcome:
        query = query.filter(ClosedTradeHistory.outcome_status == outcome.upper())
    if exit_reason:
        query = query.filter(ClosedTradeHistory.exit_reason == exit_reason)
    if market_regime:
        query = query.filter(ClosedTradeHistory.market_regime_at_entry == market_regime)

    if search:
        s_pattern = f"%{search}%"
        query = query.filter(
            or_(
                ClosedTradeHistory.symbol.ilike(s_pattern),
                ClosedTradeHistory.company_name.ilike(s_pattern),
                ClosedTradeHistory.strategy_name_fa.ilike(s_pattern),
                ClosedTradeHistory.id.ilike(s_pattern),
            )
        )

    total_count = query.count()

    # Sort
    col = getattr(ClosedTradeHistory, sort_by, ClosedTradeHistory.closed_at)
    if sort_order == "asc":
        query = query.order_by(asc(col))
    else:
        query = query.order_by(desc(col))

    offset = (page - 1) * page_size
    trades = query.offset(offset).limit(page_size).all()

    exit_fa_map = {
        "STOP_LOSS": "حد ضرر",
        "TARGET_1": "تارگت اول",
        "TARGET_2": "تارگت دوم",
        "TRAILING_STOP": "تریلینگ‌استاپ",
        "TIME_STOP": "حد زمانی",
        "SIGNAL_INVALIDATED": "ابطال سیگنال",
        "REGIME_CHANGE": "تغییر رژیم بازار",
        "RISK_REDUCTION": "کاهش ریسک سیستمی",
        "KILL_SWITCH": "مدارشکن کلید قطع",
        "MANUAL_EXIT": "خروج دستی",
        "CORPORATE_ACTION": "رویداد شرکتی",
        "LIQUIDITY_EXIT": "خروج نقدشوندگی",
        "OTHER": "سایر",
    }

    outcome_fa_map = {
        "WIN": "سودده (برد)",
        "LOSS": "زیان‌ده (باخت)",
        "BREAKEVEN": "سر‌به‌سر",
    }

    items = []
    for t in trades:
        item = ClosedTradeResponse(
            id=t.id,
            portfolio_id=t.portfolio_id,
            position_id=t.position_id,
            symbol=t.symbol,
            company_name=t.company_name,
            sector=t.sector,
            strategy_id=t.strategy_id,
            strategy_name_fa=t.strategy_name_fa,
            strategy_version=t.strategy_version,
            model_version=t.model_version,
            risk_policy_version=t.risk_policy_version,
            market_rules_version=t.market_rules_version,
            dataset_version=t.dataset_version,
            signal_id=t.signal_id,
            decision_id=t.decision_id,
            decision_method=t.decision_method,
            opened_at=t.opened_at.isoformat(),
            closed_at=t.closed_at.isoformat(),
            holding_sessions=t.holding_sessions,
            holding_duration_hours=t.holding_duration_hours,
            planned_entry=t.planned_entry,
            avg_entry_price=t.avg_entry_price,
            avg_exit_price=t.avg_exit_price,
            total_quantity=t.total_quantity,
            gross_buy_value=t.gross_buy_value,
            gross_sell_value=t.gross_sell_value,
            entry_fees=t.entry_fees,
            exit_fees=t.exit_fees,
            tax=t.tax,
            slippage_cost=t.slippage_cost,
            total_cost=t.total_cost,
            gross_pnl=t.gross_pnl,
            net_pnl=t.net_pnl,
            net_pnl_tomans=round(t.net_pnl / 10.0),
            net_return_pct=round(t.net_return_pct, 2) if t.net_return_pct is not None else 0.0,
            initial_risk_amount=t.initial_risk_amount,
            initial_risk_pct_nav=t.initial_risk_pct_nav,
            realized_R=round(t.realized_R, 2) if t.realized_R is not None else 0.0,
            MFE=round(t.MFE, 1) if t.MFE is not None else 0.0,
            MAE=round(t.MAE, 1) if t.MAE is not None else 0.0,
            initial_stop=t.initial_stop,
            final_stop=t.final_stop,
            target1=t.target1,
            target2=t.target2,
            exit_reason=t.exit_reason,
            exit_reason_fa=exit_fa_map.get(t.exit_reason, t.exit_reason),
            exit_reason_detail=t.exit_reason_detail,
            market_regime_at_entry=t.market_regime_at_entry,
            market_regime_at_exit=t.market_regime_at_exit,
            portfolio_nav_at_entry=t.portfolio_nav_at_entry,
            portfolio_nav_at_exit=t.portfolio_nav_at_exit,
            position_weight_at_entry=t.position_weight_at_entry,
            outcome_status=t.outcome_status,
            outcome_status_fa=outcome_fa_map.get(t.outcome_status, t.outcome_status),
            reason_fa=t.reason_fa,
            lesson_fa=t.lesson_fa,
        )
        items.append(item)

    total_pages = max(1, (total_count + page_size - 1) // page_size)
    summary = get_trade_history_summary(db)

    return PaginatedClosedTradesResponse(
        items=items,
        total=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        summary=summary,
    )


@router.get("/trade/{trade_id}", response_model=ClosedTradeDetailResponse)
def get_closed_trade_detail(trade_id: str, db: Session = Depends(get_sync_db)):
    """Returns complete trade detail, execution timeline, post-mortem, and chart bars for replay."""
    trade = db.query(ClosedTradeHistory).filter(ClosedTradeHistory.id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail="معامله مورد نظر در تاریخچه یافت نشد.")

    # Timeline events
    timeline_items = []
    for ev in trade.timeline_events:
        timeline_items.append(
            TradeExecutionTimelineItem(
                id=ev.id,
                event_type=ev.event_type,
                timestamp=ev.timestamp.isoformat(),
                price=ev.price,
                quantity=ev.quantity,
                portion_pct=ev.portion_pct,
                fees=ev.fees,
                notes_fa=ev.notes_fa,
            )
        )

    # Post-mortem
    pm_resp = None
    if trade.post_mortem:
        pm_resp = TradePostMortemResponse(
            entry_efficiency=trade.post_mortem.entry_efficiency,
            exit_efficiency=trade.post_mortem.exit_efficiency,
            process_quality_score=trade.post_mortem.process_quality_score,
            outcome_vs_process_type=trade.post_mortem.outcome_vs_process_type,
            what_worked_fa=trade.post_mortem.what_worked_fa,
            what_failed_fa=trade.post_mortem.what_failed_fa,
            entry_quality_fa=trade.post_mortem.entry_quality_fa,
            exit_quality_fa=trade.post_mortem.exit_quality_fa,
            position_sizing_quality_fa=trade.post_mortem.position_sizing_quality_fa,
            execution_quality_fa=trade.post_mortem.execution_quality_fa,
            risk_compliance_fa=trade.post_mortem.risk_compliance_fa,
            unexpected_market_behavior_fa=trade.post_mortem.unexpected_market_behavior_fa,
        )

    # Generate synthetic or real chart bars around entry and exit dates
    inst = db.query(Instrument).filter(Instrument.ticker == trade.symbol).first()
    chart_bars = []
    if inst:
        bars = (
            db.query(EODBar)
            .filter(EODBar.instrument_id == inst.id)
            .order_by(EODBar.trading_date.asc())
            .limit(60)
            .all()
        )
        for b in bars:
            chart_bars.append({
                "date": b.trading_date.isoformat(),
                "open": b.open,
                "high": b.high,
                "low": b.low,
                "close": b.close,
                "volume": b.volume,
            })

    exit_fa_map = {
        "STOP_LOSS": "حد ضرر",
        "TARGET_1": "تارگت اول",
        "TARGET_2": "تارگت دوم",
        "TRAILING_STOP": "تریلینگ‌استاپ",
        "TIME_STOP": "حد زمانی",
        "SIGNAL_INVALIDATED": "ابطال سیگنال",
        "REGIME_CHANGE": "تغییر رژیم بازار",
        "RISK_REDUCTION": "کاهش ریسک سیستمی",
        "KILL_SWITCH": "مدارشکن کلید قطع",
        "MANUAL_EXIT": "خروج دستی",
        "CORPORATE_ACTION": "رویداد شرکتی",
        "LIQUIDITY_EXIT": "خروج نقدشوندگی",
        "OTHER": "سایر",
    }

    outcome_fa_map = {
        "WIN": "سودده (برد)",
        "LOSS": "زیان‌ده (باخت)",
        "BREAKEVEN": "سر‌به‌سر",
    }

    return ClosedTradeDetailResponse(
        id=trade.id,
        portfolio_id=trade.portfolio_id,
        position_id=trade.position_id,
        symbol=trade.symbol,
        company_name=trade.company_name,
        sector=trade.sector,
        strategy_id=trade.strategy_id,
        strategy_name_fa=trade.strategy_name_fa,
        strategy_version=trade.strategy_version,
        model_version=trade.model_version,
        risk_policy_version=trade.risk_policy_version,
        market_rules_version=trade.market_rules_version,
        dataset_version=trade.dataset_version,
        signal_id=trade.signal_id,
        decision_id=trade.decision_id,
        decision_method=trade.decision_method,
        opened_at=trade.opened_at.isoformat(),
        closed_at=trade.closed_at.isoformat(),
        holding_sessions=trade.holding_sessions,
        holding_duration_hours=trade.holding_duration_hours,
        planned_entry=trade.planned_entry,
        avg_entry_price=trade.avg_entry_price,
        avg_exit_price=trade.avg_exit_price,
        total_quantity=trade.total_quantity,
        gross_buy_value=trade.gross_buy_value,
        gross_sell_value=trade.gross_sell_value,
        entry_fees=trade.entry_fees,
        exit_fees=trade.exit_fees,
        tax=trade.tax,
        slippage_cost=trade.slippage_cost,
        total_cost=trade.total_cost,
        gross_pnl=trade.gross_pnl,
        net_pnl=trade.net_pnl,
        net_pnl_tomans=round(trade.net_pnl / 10.0),
        net_return_pct=trade.net_return_pct,
        initial_risk_amount=trade.initial_risk_amount,
        initial_risk_pct_nav=trade.initial_risk_pct_nav,
        realized_R=trade.realized_R,
        MFE=trade.MFE,
        MAE=trade.MAE,
        initial_stop=trade.initial_stop,
        final_stop=trade.final_stop,
        target1=trade.target1,
        target2=trade.target2,
        exit_reason=trade.exit_reason,
        exit_reason_fa=exit_fa_map.get(trade.exit_reason, trade.exit_reason),
        exit_reason_detail=trade.exit_reason_detail,
        market_regime_at_entry=trade.market_regime_at_entry,
        market_regime_at_exit=trade.market_regime_at_exit,
        portfolio_nav_at_entry=trade.portfolio_nav_at_entry,
        portfolio_nav_at_exit=trade.portfolio_nav_at_exit,
        position_weight_at_entry=trade.position_weight_at_entry,
        outcome_status=trade.outcome_status,
        outcome_status_fa=outcome_fa_map.get(trade.outcome_status, trade.outcome_status),
        reason_fa=trade.reason_fa,
        lesson_fa=trade.lesson_fa,
        timeline=timeline_items,
        post_mortem=pm_resp,
        chart_bars=chart_bars,
    )


@router.get("/export/csv")
def export_closed_trades_csv(
    symbol: str | None = None,
    strategy_id: str | None = None,
    sector: str | None = None,
    outcome: str | None = None,
    db: Session = Depends(get_sync_db),
):
    """Exports closed trades to an RFC-4180 compliant CSV file matching applied filters."""
    query = db.query(ClosedTradeHistory)
    if symbol:
        query = query.filter(ClosedTradeHistory.symbol == symbol)
    if strategy_id:
        query = query.filter(ClosedTradeHistory.strategy_id == strategy_id)
    if sector:
        query = query.filter(ClosedTradeHistory.sector == sector)
    if outcome:
        query = query.filter(ClosedTradeHistory.outcome_status == outcome.upper())

    trades = query.order_by(ClosedTradeHistory.closed_at.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "شناسه معامله", "نماد", "نام شرکت", "صنعت", "استراتژی", "نسخه استراتژی",
        "تاریخ ورود", "تاریخ خروج", "جلسات معاملاتی", "قیمت برنامه ورود", "قیمت میانگین ورود",
        "قیمت میانگین خروج", "تعداد سهم", "سود/زیان خالص (تومان)", "بازده خالص (٪)", "R محقق‌شده",
        "MFE (٪)", "MAE (٪)", "دلیل خروج", "رژیم بازار", "کارمزد کل (تومان)", "اسلیپیج (تومان)"
    ])

    for t in trades:
        writer.writerow([
            t.id, t.symbol, t.company_name, t.sector, t.strategy_name_fa, t.strategy_version,
            to_jalali_str(t.opened_at), to_jalali_str(t.closed_at), t.holding_sessions,
            f"{t.planned_entry:,.0f}", f"{t.avg_entry_price:,.0f}", f"{t.avg_exit_price:,.0f}",
            t.total_quantity, f"{t.net_pnl / 10.0:,.0f}", f"{t.net_return_pct:+.2f}", f"{t.realized_R:+.2f}",
            f"{t.MFE:.1f}", f"{t.MAE:.1f}", t.exit_reason, t.market_regime_at_entry,
            f"{t.total_cost / 10.0:,.0f}", f"{t.slippage_cost / 10.0:,.0f}"
        ])

    csv_data = "\ufeff" + output.getvalue()  # UTF-8 BOM for Excel
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=closed_trades_history_{datetime.now().strftime('%Y%m%d')}.csv"},
    )
