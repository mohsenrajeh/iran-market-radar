"""Auto-trading management, trade logs, and indicator attribution API routes."""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from packages.domain.models import (
    PaperTradeLog, IndicatorPerformance, PortfolioSnapshot, Portfolio,
)
from packages.shared.database import get_sync_db
from packages.shared.datetime_utils import now_utc
from services.paper_broker.scheduler import is_scheduler_running

router = APIRouter(prefix="/auto-trading", tags=["Automated Paper Trading"])


# ── Response schemas ────────────────────────────────────────────────────


class AutoTradingStatusResponse(BaseModel):
    is_running: bool
    total_cycles: int
    total_trades: int
    last_run_at: str | None
    last_error: str | None


class TradeLogItem(BaseModel):
    id: str
    symbol: str
    side: str
    entry_price: float
    exit_price: float | None
    quantity: int
    total_invested_rials: float
    total_invested_tomans: float
    entry_at: str
    exit_at: str | None
    holding_hours: float
    holding_days: float
    expected_days_to_target: int
    market_regime: str
    market_regime_fa: str
    gross_pnl: float
    net_pnl: float
    return_pct: float
    risk_pct: float
    risk_reward_ratio: str | float = "1:2.0"
    decision_method: str
    exit_reason: str
    reason_fa: str
    lesson_fa: str
    is_closed: bool
    strategy_votes_at_entry: list[dict]
    indicator_scores: dict


class IndicatorPerfItem(BaseModel):
    indicator_name: str
    display_name_fa: str
    total_signals: int
    profitable_signals: int
    loss_signals: int
    precision: float
    avg_return_when_bullish: float
    avg_return_when_bearish: float
    cumulative_pnl: float


class PortfolioHistoryItem(BaseModel):
    snapshot_at: str
    cash: float
    positions_value: float
    total_equity: float
    open_positions_count: int
    realized_pnl: float
    unrealized_pnl: float
    drawdown_pct: float


# ── Endpoints ───────────────────────────────────────────────────────────


@router.get("/status", response_model=AutoTradingStatusResponse)
def get_auto_trading_status():
    """Returns current auto-trading scheduler status and stats."""
    from services.paper_broker.auto_trader import auto_trader

    return AutoTradingStatusResponse(
        is_running=is_scheduler_running(),
        total_cycles=auto_trader.total_cycles,
        total_trades=auto_trader.total_trades,
        last_run_at=auto_trader.last_run_at.isoformat() if auto_trader.last_run_at else None,
        last_error=auto_trader.last_error,
    )


@router.post("/trigger")
async def trigger_manual_cycle(db: Session = Depends(get_sync_db)):
    """Manually triggers one complete trading cycle (data sync → evaluate → trade → log)."""
    from services.paper_broker.auto_trader import auto_trader

    try:
        await auto_trader.run_cycle()
        return {
            "success": True,
            "message": "یک چرخه معاملاتی با موفقیت اجرا شد.",
            "total_cycles": auto_trader.total_cycles,
            "total_trades": auto_trader.total_trades,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطا در اجرای چرخه: {str(e)}")


@router.get("/trade-log", response_model=list[TradeLogItem])
def get_trade_log(
    symbol: str | None = None,
    closed_only: bool = False,
    limit: int = Query(50, le=500),
    db: Session = Depends(get_sync_db),
):
    """Returns paper trade logs for ML training and review."""
    query = db.query(PaperTradeLog).order_by(PaperTradeLog.entry_at.desc())

    if symbol:
        query = query.filter(PaperTradeLog.symbol == symbol)
    if closed_only:
        query = query.filter(PaperTradeLog.is_closed == True)

    logs = query.limit(limit).all()
    regime_fa_map = {
        "risk_on": "صعودی پرقدرت",
        "neutral": "خنثی / تعادلی",
        "risk_off": "اصلاحی / نزولی",
        "distribution": "مشکوک به توزیع / پرریسک",
    }

    result = []
    for log in logs:
        invested_r = getattr(log, "total_invested_rials", None) or (log.entry_price * log.quantity)
        h_days = getattr(log, "holding_days", None) or round(log.holding_hours / 24.0, 1)
        m_regime = getattr(log, "market_regime", "risk_on") or "risk_on"
        result.append(
            TradeLogItem(
                id=log.id,
                symbol=log.symbol,
                side=log.side,
                entry_price=log.entry_price,
                exit_price=log.exit_price,
                quantity=log.quantity,
                total_invested_rials=round(invested_r),
                total_invested_tomans=round(invested_r / 10.0),
                entry_at=log.entry_at.isoformat() if log.entry_at else "",
                exit_at=log.exit_at.isoformat() if log.exit_at else None,
                holding_hours=round(log.holding_hours, 1),
                holding_days=h_days,
                expected_days_to_target=getattr(log, "expected_days_to_target", 5) or 5,
                market_regime=m_regime,
                market_regime_fa=regime_fa_map.get(m_regime, m_regime),
                gross_pnl=round(log.gross_pnl),
                net_pnl=round(log.net_pnl),
                return_pct=round(log.return_pct, 2),
                risk_pct=getattr(log, "risk_pct", 0.5) or 0.5,
                risk_reward_ratio=getattr(log, "risk_reward_ratio", 2.0) or 2.0,
                decision_method=getattr(log, "decision_method", "") or "تأیید چند استراتژی",
                exit_reason=log.exit_reason,
                reason_fa=log.reason_fa,
                lesson_fa=log.lesson_fa,
                is_closed=log.is_closed,
                strategy_votes_at_entry=log.strategy_votes_at_entry or [],
                indicator_scores=log.indicator_scores or {},
            )
        )
    return result


@router.get("/attribution", response_model=list[IndicatorPerfItem])
@router.get("/indicator-performance", response_model=list[IndicatorPerfItem])
def get_indicator_attribution(db: Session = Depends(get_sync_db)):
    """Returns performance attribution for each indicator."""
    perfs = (
        db.query(IndicatorPerformance)
        .order_by(IndicatorPerformance.cumulative_pnl.desc())
        .all()
    )

    return [
        IndicatorPerfItem(
            indicator_name=p.indicator_name,
            display_name_fa=p.display_name_fa,
            total_signals=p.total_signals,
            profitable_signals=p.profitable_signals,
            loss_signals=p.loss_signals,
            precision=round(p.precision, 3),
            avg_return_when_bullish=round(p.avg_return_when_bullish, 2),
            avg_return_when_bearish=round(p.avg_return_when_bearish, 2),
            cumulative_pnl=round(p.cumulative_pnl),
        )
        for p in perfs
    ]


@router.get("/portfolio-history", response_model=list[PortfolioHistoryItem])
def get_portfolio_history(
    limit: int = Query(200, le=1000),
    db: Session = Depends(get_sync_db),
):
    """Returns portfolio equity snapshots for equity curve chart."""
    snapshots = (
        db.query(PortfolioSnapshot)
        .order_by(PortfolioSnapshot.snapshot_at.asc())
        .limit(limit)
        .all()
    )

    return [
        PortfolioHistoryItem(
            snapshot_at=s.snapshot_at.isoformat(),
            cash=round(s.cash),
            positions_value=round(s.positions_value),
            total_equity=round(s.total_equity),
            open_positions_count=s.open_positions_count,
            realized_pnl=round(s.realized_pnl),
            unrealized_pnl=round(s.unrealized_pnl),
            drawdown_pct=round(s.drawdown_pct, 2),
        )
        for s in snapshots
    ]
