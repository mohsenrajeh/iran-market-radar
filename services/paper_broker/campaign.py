"""Resolve the single versioned paper-campaign portfolio without ambiguous `.first()` queries."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from packages.domain.models import (
    BrokerOrder,
    CashLedger,
    ClosedTradeHistory,
    PaperCampaign,
    PaperTradeLog,
    Portfolio,
    PortfolioSnapshot,
    Position,
)


ACTIVE_CAMPAIGN_STATUSES = ("READY_BLOCKED_DATA", "READY", "RUNNING")


def _same_money(left: float, right: float) -> bool:
    return abs(float(left) - float(right)) < 0.5


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _validate_campaign_portfolio_identity(
    campaign: PaperCampaign,
    portfolio: Portfolio,
) -> None:
    if campaign.portfolio_id != portfolio.id:
        raise RuntimeError("Campaign and portfolio identity do not match.")
    if not _same_money(portfolio.initial_cash, campaign.initial_capital_rials):
        raise RuntimeError("Campaign and portfolio opening capital do not match.")


def _opening_snapshot_is_valid(
    snapshot: PortfolioSnapshot,
    campaign: PaperCampaign,
    portfolio: Portfolio,
) -> bool:
    return (
        snapshot.portfolio_id == portfolio.id
        and abs((_as_utc(snapshot.snapshot_at) - _as_utc(campaign.starts_at)).total_seconds()) < 0.001
        and _same_money(snapshot.cash, campaign.initial_capital_rials)
        and _same_money(snapshot.total_equity, campaign.initial_capital_rials)
        and _same_money(snapshot.positions_value, 0.0)
        and snapshot.open_positions_count == 0
        and _same_money(snapshot.realized_pnl, 0.0)
        and _same_money(snapshot.unrealized_pnl, 0.0)
        and _same_money(snapshot.drawdown_pct, 0.0)
    )


def validate_campaign_opening_snapshot(
    db: Session,
    campaign: PaperCampaign,
    portfolio: Portfolio,
) -> PortfolioSnapshot:
    """Validate the immutable opening point without creating or repairing data."""
    _validate_campaign_portfolio_identity(campaign, portfolio)
    expected_id = f"snapshot_{campaign.id}_opening"
    opening = db.query(PortfolioSnapshot).filter(PortfolioSnapshot.id == expected_id).first()
    if opening is None:
        raise RuntimeError("Active paper campaign is missing its required opening snapshot.")
    if not _opening_snapshot_is_valid(opening, campaign, portfolio):
        raise RuntimeError("Persisted campaign opening snapshot is inconsistent or corrupted.")
    return opening


def ensure_initial_campaign_snapshot(
    db: Session,
    campaign: PaperCampaign,
    portfolio: Portfolio,
) -> bool:
    """Create the auditable opening NAV point once, without rewriting campaign state."""
    _validate_campaign_portfolio_identity(campaign, portfolio)

    expected_id = f"snapshot_{campaign.id}_opening"
    existing = db.query(PortfolioSnapshot).filter(PortfolioSnapshot.id == expected_id).first()
    if existing is not None:
        if not _opening_snapshot_is_valid(existing, campaign, portfolio):
            raise RuntimeError("Persisted campaign opening snapshot is inconsistent or corrupted.")
        return False

    if db.query(PortfolioSnapshot).filter(PortfolioSnapshot.portfolio_id == portfolio.id).count() > 0:
        raise RuntimeError("Campaign has later snapshots but its required opening snapshot is missing.")

    position_count = db.query(Position).filter(Position.portfolio_id == portfolio.id).count()
    order_count = db.query(BrokerOrder).filter(BrokerOrder.portfolio_id == portfolio.id).count()
    trade_log_count = db.query(PaperTradeLog).filter(PaperTradeLog.portfolio_id == portfolio.id).count()
    closed_trade_count = db.query(ClosedTradeHistory).filter(ClosedTradeHistory.portfolio_id == portfolio.id).count()
    ledger_rows = db.query(CashLedger).filter(CashLedger.portfolio_id == portfolio.id).all()
    valid_initial_ledger = (
        len(ledger_rows) == 1
        and ledger_rows[0].transaction_type == "INITIAL"
        and _same_money(ledger_rows[0].amount_rials, campaign.initial_capital_rials)
        and _same_money(ledger_rows[0].settled_cash, campaign.initial_capital_rials)
        and _same_money(ledger_rows[0].available_cash, campaign.initial_capital_rials)
        and _same_money(ledger_rows[0].unsettled_cash, 0.0)
        and _same_money(ledger_rows[0].reserved_cash, 0.0)
        and _same_money(ledger_rows[0].fees_due, 0.0)
    )
    pristine = (
        position_count == 0
        and order_count == 0
        and trade_log_count == 0
        and closed_trade_count == 0
        and valid_initial_ledger
        and _same_money(portfolio.cash, campaign.initial_capital_rials)
        and _same_money(portfolio.realized_pnl, 0.0)
    )
    if not pristine:
        raise RuntimeError(
            "Cannot reconstruct a missing opening snapshot after campaign financial state changed."
        )

    db.add(PortfolioSnapshot(
        id=expected_id,
        portfolio_id=portfolio.id,
        snapshot_at=campaign.starts_at,
        cash=portfolio.cash,
        positions_value=0.0,
        total_equity=portfolio.cash,
        open_positions_count=0,
        realized_pnl=0.0,
        unrealized_pnl=0.0,
        drawdown_pct=0.0,
    ))
    return True


def get_active_campaign_portfolio(
    db: Session,
    *,
    require_execution_window: bool = False,
) -> Portfolio | None:
    """Resolve the campaign for reads; optionally enforce its trading window."""
    campaigns = (
        db.query(PaperCampaign)
        .filter(PaperCampaign.status.in_(ACTIVE_CAMPAIGN_STATUSES))
        .order_by(PaperCampaign.created_at.desc())
        .all()
    )
    if not campaigns:
        return None
    if len(campaigns) != 1:
        raise RuntimeError("Paper trading requires exactly one active campaign; multiple were found.")

    campaign = campaigns[0]
    now = datetime.now(timezone.utc)
    if require_execution_window and not (
        _as_utc(campaign.starts_at) <= now <= _as_utc(campaign.ends_at)
    ):
        raise RuntimeError("Paper campaign is outside its configured 30-day execution window.")
    portfolio = db.query(Portfolio).filter(Portfolio.id == campaign.portfolio_id).first()
    if portfolio is None:
        raise RuntimeError(f"Active paper campaign {campaign.id} references a missing portfolio.")
    active_paper_portfolios = db.query(Portfolio).filter(
        Portfolio.is_active == True,
        Portfolio.mode == "paper",
    ).all()
    if len(active_paper_portfolios) != 1 or active_paper_portfolios[0].id != portfolio.id:
        raise RuntimeError("Active paper portfolio identity is ambiguous or does not match the campaign.")
    validate_campaign_opening_snapshot(db, campaign, portfolio)
    return portfolio
