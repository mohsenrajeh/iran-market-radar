"""Paper Trading API routes, position management, pre-trade risk tickets, and ledger inspection."""
import copy
import math
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from packages.domain.models import (
    Portfolio,
    Position,
    PublishedSignal,
    Instrument,
    EODBar,
    PaperTradeLog,
    Sector,
    ClosedTradeHistory,
    TradeExecutionTimeline,
    TradeExitReason,
    TradeOutcomeStatus,
    CashLedger,
    PortfolioSnapshot,
    MarketSnapshot,
    BrokerOrder,
    OrderFill,
    DecisionAudit,
    ClientTypeSnapshot,
    PaperCampaign,
)
from packages.domain.schemas import (
    PortfolioResponse,
    PositionResponse,
    PositionDetailResponse,
    OrderCreateFromSignalRequest,
)
from packages.domain.risk_policy import ACTIVE_RISK_POLICY
from services.paper_broker.ledger import paper_broker
from services.paper_broker.accounting import accounting_reconciler
from packages.shared.database import get_sync_db
from packages.shared.config import settings
from packages.shared.datetime_utils import now_utc, to_jalali_str, to_utc_iso
from packages.shared.metrics import compute_r_multiples
from services.collector.quality import evaluate_data_gate
from services.collector.trusted_queries import latest_trusted_market_snapshot
from packages.feature_engine.indicators import compute_symbol_features
from packages.market_rules.trading_hours import is_tse_market_open
from services.paper_broker.campaign import get_active_campaign_portfolio

router = APIRouter(prefix="/paper", tags=["Paper Trading"])


def _require_fresh_trade_data(db: Session) -> None:
    gate = evaluate_data_gate(db, require_market_open=True)
    if not gate.allowed:
        raise HTTPException(status_code=409, detail={"message": "گیت داده اجازه معامله نمی‌دهد.", "trade_gate": gate.to_dict()})


def _require_exit_session() -> None:
    """Risk-reducing exits need an open session; per-symbol price trust is checked separately."""
    if not is_tse_market_open():
        raise HTTPException(status_code=409, detail="خروج کاغذی فقط در جلسه پیوسته بازار ثبت می‌شود.")


def _require_fresh_instrument_snapshot(snapshot: MarketSnapshot | None) -> datetime:
    """Reject a trade action unless this instrument's own snapshot is fresh."""
    if snapshot is None:
        raise HTTPException(status_code=409, detail="snapshot رسمی و تازه برای نماد موجود نیست.")
    snapshot_as_of = snapshot.source_timestamp
    if snapshot_as_of.tzinfo is None:
        snapshot_as_of = snapshot_as_of.replace(tzinfo=timezone.utc)
    age_seconds = (now_utc() - snapshot_as_of.astimezone(timezone.utc)).total_seconds()
    if age_seconds < 0 or age_seconds > settings.quality.critical_market_stale_seconds:
        raise HTTPException(status_code=409, detail="snapshot رسمی همین نماد قدیمی است؛ معامله متوقف شد.")
    return snapshot_as_of


def _fresh_trusted_instrument_snapshot(db: Session, instrument_id: str | None) -> MarketSnapshot:
    snapshot = latest_trusted_market_snapshot(
        db,
        instrument_id or "",
        max_age_seconds=settings.quality.critical_market_stale_seconds,
    )
    _require_fresh_instrument_snapshot(snapshot)
    return snapshot


class KillSwitchRequest(BaseModel):
    active: bool


class CustomRiskTicketRequest(BaseModel):
    signal_id: str
    custom_price: float | None = None
    custom_stop: float | None = None
    custom_target: float | None = None


@router.get("/portfolio", response_model=PortfolioResponse)
def get_paper_portfolio(db: Session = Depends(get_sync_db)):
    """Return the persisted ledger state without creating, seeding, repricing, or committing."""
    port = get_active_campaign_portfolio(db)
    if not port:
        raise HTTPException(status_code=404, detail="پورتفوی کاغذی هنوز در startup مقداردهی نشده است.")
    campaign = (
        db.query(PaperCampaign)
        .filter(PaperCampaign.portfolio_id == port.id)
        .order_by(PaperCampaign.created_at.desc())
        .first()
    )
    open_positions = [p for p in port.positions if p.is_open]
    display_prices: dict[str, float] = {}
    for position in open_positions:
        instrument = db.query(Instrument).filter(Instrument.ticker == position.symbol).first()
        latest_market = (
            db.query(MarketSnapshot).filter(MarketSnapshot.instrument_id == instrument.id)
            .order_by(MarketSnapshot.source_timestamp.desc()).first()
        ) if instrument else None
        display_prices[position.id] = latest_market.last_price if latest_market else position.current_price
    unrealized_total = sum((display_prices[p.id] - p.average_entry_price) * p.quantity for p in open_positions)
    total_positions_val = sum(p.quantity * display_prices[p.id] for p in open_positions)
    total_equity = port.cash + total_positions_val

    pos_responses = []
    regime_fa_map = {
        "risk_on": "صعودی پرقدرت",
        "neutral": "خنثی / تعادلی",
        "risk_off": "اصلاحی / نزولی",
        "halted": "متوقف / بحرانی",
    }

    for p in open_positions:
        display_price = display_prices[p.id]
        cost = p.quantity * p.average_entry_price
        pnl_pct = ((display_price - p.average_entry_price) / max(1.0, p.average_entry_price)) * 100.0 if p.average_entry_price > 0 else 0.0
        invested_r = p.total_invested_rials or cost
        invested_t = invested_r / 10.0

        if p.opened_at:
            o_dt = p.opened_at if p.opened_at.tzinfo is not None else p.opened_at.replace(tzinfo=timezone.utc)
            days_open_val = round(max(0.0, (now_utc() - o_dt).total_seconds() / 86400.0), 1)
        else:
            days_open_val = 0.0

        # Dynamic R/R calculation derived at runtime from Entry, Target and Stop
        tgt = p.target_price
        stp = p.stop_loss
        if tgt is not None and stp is not None and p.average_entry_price > stp:
            reward = max(0.0, tgt - p.average_entry_price)
            risk = p.average_entry_price - stp
            raw_rr = reward / risk
            net_rr = max(0.0, raw_rr - (0.012562 / max(0.01, risk / p.average_entry_price)))
            rr_display = f"1:{net_rr:.2f}"
        else:
            rr_display = "UNKNOWN"

        dist_target = round(((tgt - display_price) / max(1.0, display_price)) * 100, 2) if tgt is not None else 0.0
        dist_stop = round(((stp - display_price) / max(1.0, display_price)) * 100, 2) if stp is not None else 0.0
        m_regime = getattr(p, "market_regime", "unknown") or "unknown"
        pos_responses.append(
            PositionResponse(
                id=p.id,
                symbol=p.symbol,
                quantity=p.quantity,
                average_entry_price=round(p.average_entry_price),
                current_price=round(display_price),
                unrealized_pnl=round((display_price - p.average_entry_price) * p.quantity),
                unrealized_pnl_pct=round(pnl_pct, 2),
                stop_loss=round(stp) if stp is not None else None,
                target_price=round(tgt) if tgt is not None else None,
                total_invested_rials=round(invested_r),
                total_invested_tomans=round(invested_t),
                risk_pct=p.risk_pct,
                risk_reward_ratio=rr_display,
                expected_days_to_target=p.expected_days_to_target,
                days_open=days_open_val,
                market_regime=m_regime,
                market_regime_fa=regime_fa_map.get(m_regime.lower(), "نامشخص"),
                decision_method=getattr(p, "decision_method", "") or "ثبت نشده",
                entry_reason_fa=getattr(p, "entry_reason_fa", "") or "دلیل ورود در داده قدیمی ثبت نشده است",
                distance_to_target_pct=dist_target,
                distance_to_stop_pct=dist_stop,
                client_power_ratio=getattr(p, "client_power_ratio", None),
                risk_flags_fa=getattr(p, "risk_flags_fa", []) or [],
                opened_at=p.opened_at,
                is_open=p.is_open,
            )
        )

    latest_snapshot = db.query(PortfolioSnapshot).filter(PortfolioSnapshot.portfolio_id == port.id).order_by(PortfolioSnapshot.snapshot_at.desc()).first()
    snap_id = latest_snapshot.id if latest_snapshot else "NO_SNAPSHOT"
    ledger_sequence = db.query(CashLedger).filter(CashLedger.portfolio_id == port.id).count()
    as_of_jalali = to_jalali_str(now_utc(), include_time=True)

    return PortfolioResponse(
        id=port.id,
        name=port.name,
        campaign_id=campaign.id if campaign else None,
        campaign_status=campaign.status if campaign else None,
        campaign_started_at=campaign.starts_at if campaign else None,
        campaign_ends_at=campaign.ends_at if campaign else None,
        initial_cash=round(port.initial_cash),
        cash=round(port.cash),
        total_equity=round(total_equity),
        realized_pnl=round(port.realized_pnl),
        unrealized_pnl=round(unrealized_total),
        open_positions_count=len(open_positions),
        kill_switch_active=port.kill_switch_active,
        portfolio_snapshot_id=snap_id,
        ledger_sequence=ledger_sequence,
        risk_policy_version=ACTIVE_RISK_POLICY.version,
        as_of=as_of_jalali,
        positions=pos_responses,
    )


@router.get("/pre-trade-ticket/{signal_id}")
def get_pre_trade_risk_ticket(signal_id: str, db: Session = Depends(get_sync_db)):
    """Generates complete pre-trade risk ticket with position sizing analysis and stage breakdown."""
    port = get_active_campaign_portfolio(db)
    if not port:
        raise HTTPException(status_code=404, detail="پورتفوی یافت نشد.")

    sig = db.query(PublishedSignal).filter(PublishedSignal.id == signal_id).first()
    if not sig:
        raise HTTPException(status_code=404, detail="سیگنال یافت نشد.")

    inst = db.query(Instrument).filter(Instrument.id == sig.instrument_id).first()
    curr_bar = (
        db.query(MarketSnapshot)
        .filter(MarketSnapshot.instrument_id == inst.id)
        .order_by(MarketSnapshot.source_timestamp.desc())
        .first()
    ) if inst else None
    if curr_bar is None:
        raise HTTPException(status_code=409, detail="snapshot رسمی برای محاسبه ریسک موجود نیست.")
    curr_price = curr_bar.last_price
    ticket = paper_broker.generate_pre_trade_ticket(port, sig, curr_price)
    return ticket


@router.post("/evaluate-risk-ticket")
def evaluate_custom_risk_ticket(req: CustomRiskTicketRequest, db: Session = Depends(get_sync_db)):
    """Evaluates custom price and stop levels against portfolio constraints."""
    port = get_active_campaign_portfolio(db)
    if not port:
        raise HTTPException(status_code=404, detail="پورتفوی یافت نشد.")

    sig = db.query(PublishedSignal).filter(PublishedSignal.id == req.signal_id).first()
    if not sig:
        raise HTTPException(status_code=404, detail="سیگنال یافت نشد.")

    if req.custom_price is not None:
        curr_price = req.custom_price
    else:
        inst = db.query(Instrument).filter(Instrument.id == sig.instrument_id).first()
        snapshot = (
            db.query(MarketSnapshot).filter(MarketSnapshot.instrument_id == inst.id)
            .order_by(MarketSnapshot.source_timestamp.desc()).first()
        ) if inst else None
        if snapshot is None:
            raise HTTPException(status_code=409, detail="snapshot رسمی برای محاسبه ریسک موجود نیست.")
        curr_price = snapshot.last_price
    evaluated_signal = copy.copy(sig)
    evaluated_signal.invalidation = dict(sig.invalidation or {})
    evaluated_signal.exit_plan = dict(sig.exit_plan or {})
    if req.custom_stop is not None:
        evaluated_signal.invalidation["price"] = req.custom_stop
    if req.custom_target is not None:
        targets = list(evaluated_signal.exit_plan.get("targets") or [])
        evaluated_signal.exit_plan["targets"] = [req.custom_target, *targets[1:]]
    ticket = paper_broker.generate_pre_trade_ticket(port, evaluated_signal, curr_price)
    return ticket


@router.get("/position-detail/{position_id}", response_model=PositionDetailResponse)
def get_paper_position_detail(position_id: str, db: Session = Depends(get_sync_db)):
    """Returns deep trade inspection, target trajectory visualizer, candlestick history, and AI diagnosis."""
    pos = db.query(Position).filter(Position.id == position_id).first()
    if not pos:
        raise HTTPException(status_code=404, detail="موقعیت معاملاتی یافت نشد.")

    sym = pos.symbol
    inst = db.query(Instrument).options(joinedload(Instrument.sector)).filter(Instrument.ticker == sym).first()
    sec_name = inst.sector.name_fa if inst and inst.sector else "نامشخص"
    name_fa = inst.name_fa if inst else sym
    latest_market = (
        db.query(MarketSnapshot).filter(MarketSnapshot.instrument_id == inst.id)
        .order_by(MarketSnapshot.source_timestamp.desc()).first()
    ) if inst else None
    cur_price = latest_market.last_price if latest_market else (pos.current_price or pos.average_entry_price)
    stop_loss = pos.stop_loss
    target_1 = pos.target_price
    entry_order = db.query(BrokerOrder).filter(
        BrokerOrder.portfolio_id == pos.portfolio_id,
        BrokerOrder.symbol == pos.symbol,
        BrokerOrder.side == "BUY",
        BrokerOrder.signal_id.isnot(None),
        ~BrokerOrder.signal_id.like("position:%"),
    ).order_by(BrokerOrder.created_at.asc()).first()
    signal = db.query(PublishedSignal).filter(PublishedSignal.id == entry_order.signal_id).first() if entry_order else None
    signal_targets = (signal.exit_plan or {}).get("targets", []) if signal else []
    target_2 = signal_targets[1] if len(signal_targets) > 1 else None

    r_metrics = None
    if stop_loss is not None and target_1 is not None and stop_loss < pos.average_entry_price:
        r_metrics = compute_r_multiples(
            current_price=cur_price,
            planned_entry=pos.average_entry_price,
            stop_price=stop_loss,
            target1_price=target_1,
            target2_price=target_2 or target_1,
        )

    if target_1 is not None and target_1 > pos.average_entry_price:
        target_gain_range = target_1 - pos.average_entry_price
        progress_to_target = round(((cur_price - pos.average_entry_price) / target_gain_range) * 100, 1)
        dist_target_pct = round(((target_1 - cur_price) / max(1.0, cur_price)) * 100, 2)
        dist_target_rials = round(target_1 - cur_price)
    else:
        progress_to_target = None
        dist_target_pct = None
        dist_target_rials = None
    if stop_loss is not None:
        dist_stop_pct = round(((stop_loss - cur_price) / max(1.0, cur_price)) * 100, 2)
        dist_stop_rials = round(stop_loss - cur_price)
    else:
        dist_stop_pct = None
        dist_stop_rials = None

    # Fetch only persisted bars; an empty chart is more honest than fabricated candles.
    bars_query = []
    bars = []
    if inst:
        bars = (
            db.query(EODBar)
            .filter(EODBar.instrument_id == inst.id)
            .order_by(EODBar.trading_date.desc())
            .limit(15)
            .all()
        )
        for b in reversed(bars):
            bars_query.append({
                "date": to_jalali_str(b.trading_date),
                "open": b.open,
                "high": b.high,
                "low": b.low,
                "close": b.close,
                "volume": b.volume,
            })

    pnl_pct = ((cur_price - pos.average_entry_price) / max(1.0, pos.average_entry_price)) * 100.0
    cost = pos.quantity * pos.average_entry_price
    opened = pos.opened_at or now_utc()
    opened_aware = opened if opened.tzinfo is not None else opened.replace(tzinfo=timezone.utc)
    days_open = max(0.0, (now_utc() - opened_aware).total_seconds() / 86400.0)
    regime_fa = {
        "risk_on": "رونق و تقاضای پرقدرت",
        "neutral": "متعادل و نوسانی",
        "risk_off": "ریسک‌گریز",
        "halted": "متوقف",
    }.get((pos.market_regime or "neutral").lower(), "نامشخص")

    features: dict = {}
    if len(bars) >= 15:
        bars_dict = [{
            "trading_date": bar.trading_date.isoformat(), "open": bar.open, "high": bar.high,
            "low": bar.low, "close": bar.close, "last": bar.last,
            "yesterday_price": bar.yesterday_price, "volume": bar.volume,
            "value": bar.value, "trade_count": bar.trade_count,
            "allowed_min": bar.allowed_min, "allowed_max": bar.allowed_max,
        } for bar in reversed(bars)]
        client_rows = db.query(ClientTypeSnapshot).filter(
            ClientTypeSnapshot.instrument_id == inst.id
        ).order_by(ClientTypeSnapshot.trading_date.desc()).limit(30).all() if inst else []
        client_dict = [{
            "trading_date": row.trading_date.isoformat(),
            "real_buy_count": row.real_buy_count, "real_buy_volume": row.real_buy_volume,
            "real_buy_value": row.real_buy_value, "real_sell_count": row.real_sell_count,
            "real_sell_volume": row.real_sell_volume, "real_sell_value": row.real_sell_value,
            "legal_buy_value": row.legal_buy_value, "legal_sell_value": row.legal_sell_value,
        } for row in reversed(client_rows)]
        features = compute_symbol_features(bars_dict, client_dict)

    pos_resp = PositionResponse(
        id=pos.id,
        symbol=pos.symbol,
        quantity=pos.quantity,
        average_entry_price=round(pos.average_entry_price),
        current_price=round(cur_price),
        unrealized_pnl=round((cur_price - pos.average_entry_price) * pos.quantity),
        unrealized_pnl_pct=round(pnl_pct, 2),
        stop_loss=round(stop_loss) if stop_loss is not None else None,
        target_price=round(target_1) if target_1 is not None else None,
        total_invested_rials=round(cost),
        total_invested_tomans=round(cost / 10.0),
        risk_pct=pos.risk_pct,
        risk_reward_ratio=f"1:{r_metrics['net_reward_risk_ratio']:.1f}" if r_metrics else "UNKNOWN",
        expected_days_to_target=pos.expected_days_to_target,
        days_open=round(days_open, 1),
        market_regime=pos.market_regime or "unknown",
        market_regime_fa=regime_fa,
        decision_method=pos.decision_method or "ثبت نشده",
        entry_reason_fa=pos.entry_reason_fa or "در داده قدیمی ثبت نشده است",
        distance_to_target_pct=dist_target_pct,
        distance_to_stop_pct=dist_stop_pct,
        client_power_ratio=features.get("real_buyer_power") if features.get("real_buyer_power") is not None else pos.client_power_ratio,
        risk_flags_fa=pos.risk_flags_fa or [],
        opened_at=opened,
        is_open=pos.is_open,
    )

    strategy_votes = signal.strategy_votes if signal else []
    active_indicators = {
        key: features[key]
        for key in ("rsi_14", "mfi_14", "adx_14", "real_buyer_power", "volume_z_score")
        if key in features
    }

    if pnl_pct >= 4.0:
        recommendation = "بررسی شرط خروج ثبت‌شده و مدیریت پله‌ای"
        summary_fa = f"بازده ثبت‌شده {pnl_pct:+.1f}٪ است؛ تصمیم فقط با گیت داده و سفارش snapshot بعدی اجرا می‌شود."
    elif pnl_pct > 0:
        recommendation = "حفظ یا خروج فقط طبق قواعد ثبت‌شده"
        summary_fa = (
            f"بازده ثبت‌شده {pnl_pct:+.1f}٪ و فاصله تا هدف ثبت‌شده {dist_target_pct:+.1f}٪ است."
            if dist_target_pct is not None else
            f"بازده ثبت‌شده {pnl_pct:+.1f}٪ است؛ هدف معتبر ثبت نشده است."
        )
    else:
        recommendation = "رصد حد ضرر ثبت‌شده"
        summary_fa = (
            f"بازده ثبت‌شده {pnl_pct:+.1f}٪ و فاصله تا حد ضرر {dist_stop_pct:+.1f}٪ است؛ ادعای روند بدون داده کافی ساخته نمی‌شود."
            if dist_stop_pct is not None else
            f"بازده ثبت‌شده {pnl_pct:+.1f}٪ است؛ حد ضرر معتبر ثبت نشده و معامله باید برای بازبینی مسدود شود."
        )

    return PositionDetailResponse(
        position=pos_resp,
        name_fa=name_fa,
        sector_name=sec_name,
        target_price_2=target_2,
        progress_to_target_pct=progress_to_target,
        distance_to_target_rials=dist_target_rials,
        distance_to_stop_rials=dist_stop_rials,
        candles=bars_query,
        strategy_votes=strategy_votes,
        active_indicators=active_indicators,
        ai_recommendation_fa=recommendation,
        ai_summary_fa=summary_fa,
    )


@router.post("/close-position/{position_id}")
def close_paper_position_manually(position_id: str, db: Session = Depends(get_sync_db)):
    """Submit a full exit for execution on the first later official snapshot."""
    _require_exit_session()
    port = get_active_campaign_portfolio(db)
    if not port:
        raise HTTPException(status_code=404, detail="پورتفوی فعال یافت نشد.")
    pos = db.query(Position).filter(
        Position.id == position_id,
        Position.portfolio_id == port.id,
        Position.is_open == True,
    ).first()
    if not pos or not pos.is_open:
        raise HTTPException(status_code=404, detail="موقعیت باز فعالی با این شناسه یافت نشد.")
    inst = db.query(Instrument).filter(Instrument.ticker == pos.symbol).first()
    snapshot = _fresh_trusted_instrument_snapshot(db, inst.id if inst else None)
    order, message = paper_broker.create_exit_order(port, position_id, snapshot.last_price, ratio=1.0)
    if order is None:
        raise HTTPException(status_code=400, detail=message)
    db.add_all([
        order,
        DecisionAudit(
            symbol=pos.symbol, signal_id=None, decision="MANUAL_EXIT_SUBMITTED",
            model_version="UNFITTED",
            dataset_version=f"market_snapshot:{to_utc_iso(snapshot.source_timestamp)}",
            risk_policy_version=paper_broker.policy.policy_id,
            decision_reason_fa=f"درخواست خروج کامل ثبت شد؛ اجرا فقط روی snapshot رسمی بعدی؛ order={order.id}",
            opportunity_score=0.0, p_profit=0.0, as_of=now_utc(),
        ),
    ])
    db.commit()
    return {"success": True, "message": message, "order_id": order.id, "status": order.status}



@router.post("/orders/from-signal")
def submit_paper_order_from_signal(req: OrderCreateFromSignalRequest, db: Session = Depends(get_sync_db)):
    """Creates and fills a new paper position from an approved opportunity."""
    _require_fresh_trade_data(db)
    try:
        port = get_active_campaign_portfolio(db, require_execution_window=True)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not port:
        raise HTTPException(status_code=404, detail="پورتفوی آزمایشی یافت نشد.")

    sig = db.query(PublishedSignal).filter(PublishedSignal.id == req.signal_id).first()
    if not sig:
        raise HTTPException(status_code=404, detail="سیگنال مورد نظر یافت نشد.")
    if not sig.actionable or sig.expires_at is None:
        raise HTTPException(status_code=409, detail="سیگنال قابل اقدام و دارای انقضای معتبر نیست.")
    signal_expiry = sig.expires_at if sig.expires_at.tzinfo else sig.expires_at.replace(tzinfo=timezone.utc)
    if signal_expiry <= now_utc():
        raise HTTPException(status_code=409, detail="اعتبار سیگنال منقضی شده است.")

    inst = db.query(Instrument).filter(Instrument.id == sig.instrument_id).first()
    curr_snapshot = _fresh_trusted_instrument_snapshot(db, inst.id if inst else None)
    snapshot_as_of = curr_snapshot.source_timestamp
    if snapshot_as_of.tzinfo is None:
        snapshot_as_of = snapshot_as_of.replace(tzinfo=timezone.utc)
    signal_as_of = sig.as_of if sig.as_of.tzinfo else sig.as_of.replace(tzinfo=timezone.utc)
    if signal_as_of < snapshot_as_of or signal_as_of > now_utc():
        raise HTTPException(status_code=409, detail="سیگنال به snapshot رسمی جاری تعلق ندارد؛ اسکن دوباره لازم است.")
    curr_price = curr_snapshot.last_price

    order, message = paper_broker.create_order_from_signal(
        portfolio=port,
        signal=sig,
        current_market_price=curr_price,
        quantity=req.quantity,
    )

    if not order:
        raise HTTPException(status_code=400, detail=message)

    db.add(order)
    db.add(DecisionAudit(
        symbol=sig.symbol,
        signal_id=sig.id,
        model_version=sig.model_version or sig.calibration_version or "UNFITTED",
        dataset_version=f"market_snapshot:{to_utc_iso(curr_snapshot.source_timestamp)}",
        risk_policy_version=paper_broker.policy.policy_id,
        decision="APPROVED_SUBMITTED",
        decision_reason_fa="سفارش تأیید شد و برای اجرای snapshot بعدی در صف قرار گرفت.",
        opportunity_score=sig.opportunity_score,
        p_profit=sig.p_profit,
        as_of=now_utc(),
    ))
    db.commit()

    return {"success": True, "message": message, "order_id": order.id}


@router.post("/scale-in/{position_id}")
def scale_in_position_endpoint(position_id: str, db: Session = Depends(get_sync_db)):
    """افزایش پله‌ای حجم سهم برنده بر اساس ارتقای تحلیل و رعایت سقف ۱۰٪ مدیریت سرمایه."""
    _require_fresh_trade_data(db)
    try:
        port = get_active_campaign_portfolio(db, require_execution_window=True)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not port:
        raise HTTPException(status_code=404, detail="پورتفوی یافت نشد.")

    pos = db.query(Position).filter(
        Position.id == position_id,
        Position.portfolio_id == port.id,
        Position.is_open == True,
    ).first()
    if not pos:
        raise HTTPException(status_code=404, detail="موقعیت باز فعالی یافت نشد.")

    inst = db.query(Instrument).filter(Instrument.ticker == pos.symbol).first()
    snapshot = _fresh_trusted_instrument_snapshot(db, inst.id if inst else None)
    curr_price = snapshot.last_price
    order, message = paper_broker.scale_in_position(port, position_id, curr_price)
    if not order:
        raise HTTPException(status_code=400, detail=message)

    db.add_all([
        order,
        DecisionAudit(
            symbol=pos.symbol, signal_id=None, decision="SCALE_IN_SUBMITTED",
            model_version="UNFITTED",
            dataset_version=f"market_snapshot:{to_utc_iso(snapshot.source_timestamp)}",
            risk_policy_version=paper_broker.policy.policy_id,
            decision_reason_fa=f"افزایش حجم ثبت شد؛ اجرا فقط روی snapshot رسمی بعدی؛ order={order.id}",
            opportunity_score=0.0, p_profit=0.0, as_of=now_utc(),
        ),
    ])
    db.commit()

    return {
        "success": True,
        "message": message,
        "order_id": order.id,
        "status": order.status,
        "current_quantity_unchanged": pos.quantity,
    }


@router.post("/trim/{position_id}")
def trim_position_endpoint(
    position_id: str,
    ratio: float = Query(0.25, ge=0.1, le=0.9),
    db: Session = Depends(get_sync_db),
):
    """کاهش پله‌ای ۲۵٪ یا ۵۰٪ حجم سهم جهت سیو سود یا کاهش ریسک در صورت تضعیف تحلیل."""
    _require_exit_session()
    port = get_active_campaign_portfolio(db)
    if not port:
        raise HTTPException(status_code=404, detail="پورتفوی یافت نشد.")

    pos = db.query(Position).filter(
        Position.id == position_id,
        Position.portfolio_id == port.id,
        Position.is_open == True,
    ).first()
    if not pos:
        raise HTTPException(status_code=404, detail="موقعیت باز فعالی یافت نشد.")

    inst = db.query(Instrument).filter(Instrument.ticker == pos.symbol).first()
    snapshot = _fresh_trusted_instrument_snapshot(db, inst.id if inst else None)
    order, message = paper_broker.create_exit_order(port, position_id, snapshot.last_price, ratio=ratio)
    if order is None:
        raise HTTPException(status_code=400, detail=message)
    db.add_all([
        order,
        DecisionAudit(
            symbol=pos.symbol, signal_id=None, decision="TRIM_SUBMITTED",
            model_version="UNFITTED",
            dataset_version=f"market_snapshot:{to_utc_iso(snapshot.source_timestamp)}",
            risk_policy_version=paper_broker.policy.policy_id,
            decision_reason_fa=f"کاهش {int(ratio * 100)}٪ ثبت شد؛ اجرا فقط روی snapshot رسمی بعدی؛ order={order.id}",
            opportunity_score=0.0, p_profit=0.0, as_of=now_utc(),
        ),
    ])
    db.commit()

    return {
        "success": True,
        "message": message,
        "order_id": order.id,
        "status": order.status,
        "current_quantity_unchanged": pos.quantity,
    }


@router.post("/kill-switch")
def toggle_paper_kill_switch(req: KillSwitchRequest, db: Session = Depends(get_sync_db)):
    """Activates or deactivates emergency trading kill switch."""
    port = get_active_campaign_portfolio(db)
    if not port:
        raise HTTPException(status_code=404, detail="پورتفوی یافت نشد.")

    msg = paper_broker.toggle_kill_switch(port, req.active)
    db.commit()
    return {"success": True, "message": msg, "kill_switch_active": port.kill_switch_active}


@router.get("/risk-policy")
def get_institutional_risk_policy():
    """Returns active risk policy configuration with versioning and hard constraints."""
    return ACTIVE_RISK_POLICY.to_dict()


@router.get("/ledger/cash")
def get_cash_ledger(db: Session = Depends(get_sync_db)):
    """Returns detailed cash breakdown (settled, unsettled, reserved) and cash transactions."""
    port = get_active_campaign_portfolio(db)
    is_reconciled, report = accounting_reconciler.reconcile_portfolio(port) if port else (True, {})
    return report


@router.get("/ledger/fills")
def get_order_fills_ledger(db: Session = Depends(get_sync_db)):
    """Return persisted execution fills; never synthesize transactions."""
    port = get_active_campaign_portfolio(db)
    fills = (
        db.query(OrderFill)
        .join(BrokerOrder, OrderFill.order_id == BrokerOrder.id)
        .filter(BrokerOrder.portfolio_id == (port.id if port else "__missing_campaign__"))
        .order_by(OrderFill.executed_at.desc())
        .limit(500)
        .all()
    )
    return {
        "fill_count": len(fills),
        "execution_model": "NEXT_BAR_AUCTION_WITH_SLIPPAGE",
        "fills": [{
            "id": fill.id,
            "order_id": fill.order_id,
            "symbol": fill.symbol,
            "side": fill.side,
            "quantity": fill.quantity,
            "fill_price": fill.fill_price,
            "slippage_rials": fill.slippage_rials,
            "fees_rials": fill.fees_rials,
            "tax_rials": fill.tax_rials,
            "net_value_rials": fill.net_value_rials,
            "executed_at": fill.executed_at.isoformat(),
        } for fill in fills],
    }


@router.get("/ledger/decisions")
def get_decision_audit_log(db: Session = Depends(get_sync_db)):
    """Return persisted decision envelopes; never synthesize approvals."""
    decisions = db.query(DecisionAudit).order_by(DecisionAudit.as_of.desc()).limit(500).all()
    return {
        "risk_policy_version": ACTIVE_RISK_POLICY.version,
        "decisions": [{
            "id": item.id,
            "symbol": item.symbol,
            "signal_id": item.signal_id,
            "action": item.decision,
            "score": item.opportunity_score,
            "p_profit": item.p_profit,
            "reason_fa": item.decision_reason_fa,
            "model_version": item.model_version,
            "dataset_version": item.dataset_version,
            "as_of": item.as_of.isoformat(),
        } for item in decisions],
    }
