from datetime import timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from packages.domain.models import CashLedger, PaperCampaign, Portfolio, PortfolioSnapshot, Position
from packages.shared.database import Base
from packages.shared.datetime_utils import now_utc
from apps.api.routes.auto_trading import get_portfolio_history
from apps.api.routes.paper import get_paper_portfolio
from services.paper_broker.campaign import ensure_initial_campaign_snapshot, get_active_campaign_portfolio


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _campaign_pair(db, suffix="identity", status="READY_BLOCKED_DATA"):
    started = now_utc()
    portfolio = Portfolio(
        id=f"portfolio_campaign_{suffix}",
        name="paper",
        mode="paper",
        cash=100_000_000_000.0,
        initial_cash=100_000_000_000.0,
        realized_pnl=0.0,
        is_active=True,
        kill_switch_active=True,
    )
    campaign = PaperCampaign(
        id=f"campaign_{suffix}",
        portfolio_id=portfolio.id,
        name_fa="کمپین تست",
        status=status,
        starts_at=started,
        ends_at=started + timedelta(days=30),
        initial_capital_rials=100_000_000_000.0,
        config_snapshot={"paper_only": True},
    )
    db.add(portfolio)
    db.flush()
    db.add(campaign)
    db.add(CashLedger(
        portfolio_id=portfolio.id,
        transaction_type="INITIAL",
        amount_rials=100_000_000_000.0,
        settled_cash=100_000_000_000.0,
        available_cash=100_000_000_000.0,
        description_fa="سرمایه اولیه",
    ))
    db.flush()
    return campaign, portfolio


def test_opening_snapshot_is_created_once_without_resetting_portfolio():
    db = _session()
    try:
        campaign, portfolio = _campaign_pair(db)

        assert ensure_initial_campaign_snapshot(db, campaign, portfolio) is True
        db.commit()
        assert ensure_initial_campaign_snapshot(db, campaign, portfolio) is False

        snapshots = db.query(PortfolioSnapshot).filter_by(portfolio_id=portfolio.id).all()
        assert len(snapshots) == 1
        assert snapshots[0].snapshot_at == campaign.starts_at
        assert snapshots[0].total_equity == campaign.initial_capital_rials
        assert portfolio.cash == 100_000_000_000.0
        assert portfolio.initial_cash == 100_000_000_000.0
    finally:
        db.close()


def test_missing_opening_snapshot_fails_closed_after_financial_state_changed():
    db = _session()
    try:
        campaign, portfolio = _campaign_pair(db)
        db.add(Position(
            id="position_changed",
            portfolio_id=portfolio.id,
            symbol="فولاد",
            quantity=10,
            average_entry_price=1_000.0,
            current_price=1_000.0,
            opened_at=now_utc(),
            is_open=False,
        ))
        db.flush()

        with pytest.raises(RuntimeError, match="Cannot reconstruct"):
            ensure_initial_campaign_snapshot(db, campaign, portfolio)
        assert db.query(PortfolioSnapshot).filter_by(portfolio_id=portfolio.id).count() == 0
    finally:
        db.close()


def test_legacy_active_portfolio_without_campaign_never_becomes_the_resolved_campaign():
    db = _session()
    try:
        db.add(Portfolio(
            id="legacy_1b",
            name="legacy",
            mode="paper",
            cash=10_000_000_000.0,
            initial_cash=10_000_000_000.0,
            is_active=True,
        ))
        db.commit()

        assert get_active_campaign_portfolio(db) is None
    finally:
        db.close()


def test_multiple_active_campaigns_fail_closed_instead_of_selecting_newest():
    db = _session()
    try:
        _campaign_pair(db, "one")
        _campaign_pair(db, "two", status="READY")
        db.commit()

        with pytest.raises(RuntimeError, match="exactly one active campaign"):
            get_active_campaign_portfolio(db)
    finally:
        db.close()


def test_expired_campaign_remains_readable_but_cannot_open_new_exposure():
    db = _session()
    try:
        campaign, portfolio = _campaign_pair(db, "expired")
        campaign.starts_at = now_utc() - timedelta(days=31)
        campaign.ends_at = now_utc() - timedelta(days=1)
        ensure_initial_campaign_snapshot(db, campaign, portfolio)
        db.commit()

        assert get_active_campaign_portfolio(db).id == portfolio.id
        assert get_paper_portfolio(db).campaign_id == campaign.id
        assert get_portfolio_history(limit=30, db=db)[0].total_equity == portfolio.initial_cash
        with pytest.raises(RuntimeError, match="outside its configured 30-day"):
            get_active_campaign_portfolio(db, require_execution_window=True)
    finally:
        db.close()


def test_corrupted_opening_snapshot_is_rejected_even_when_expected_id_exists():
    db = _session()
    try:
        campaign, portfolio = _campaign_pair(db)
        db.add(PortfolioSnapshot(
            id=f"snapshot_{campaign.id}_opening",
            portfolio_id=portfolio.id,
            snapshot_at=campaign.starts_at,
            cash=10_000_000_000.0,
            positions_value=0.0,
            total_equity=10_000_000_000.0,
            open_positions_count=0,
        ))
        db.flush()

        with pytest.raises(RuntimeError, match="inconsistent or corrupted"):
            ensure_initial_campaign_snapshot(db, campaign, portfolio)
        with pytest.raises(RuntimeError, match="inconsistent or corrupted"):
            get_paper_portfolio(db)
        with pytest.raises(RuntimeError, match="inconsistent or corrupted"):
            get_portfolio_history(limit=30, db=db)
    finally:
        db.close()


def test_later_snapshot_cannot_hide_a_missing_opening_snapshot():
    db = _session()
    try:
        campaign, portfolio = _campaign_pair(db)
        db.add(PortfolioSnapshot(
            id="snapshot_later_only",
            portfolio_id=portfolio.id,
            snapshot_at=campaign.starts_at + timedelta(minutes=1),
            cash=portfolio.cash,
            positions_value=0.0,
            total_equity=portfolio.cash,
            open_positions_count=0,
        ))
        db.flush()

        with pytest.raises(RuntimeError, match="required opening snapshot is missing"):
            ensure_initial_campaign_snapshot(db, campaign, portfolio)
        with pytest.raises(RuntimeError, match="required opening snapshot"):
            get_paper_portfolio(db)
        with pytest.raises(RuntimeError, match="required opening snapshot"):
            get_portfolio_history(limit=30, db=db)
    finally:
        db.close()


def test_non_initial_ledger_activity_blocks_opening_snapshot_reconstruction():
    db = _session()
    try:
        campaign, portfolio = _campaign_pair(db)
        db.add(CashLedger(
            portfolio_id=portfolio.id,
            transaction_type="FEE",
            amount_rials=-1_000.0,
            settled_cash=portfolio.cash - 1_000.0,
            available_cash=portfolio.cash - 1_000.0,
            fees_due=1_000.0,
            description_fa="کارمزد",
        ))
        db.flush()

        with pytest.raises(RuntimeError, match="financial state changed"):
            ensure_initial_campaign_snapshot(db, campaign, portfolio)
    finally:
        db.close()


def test_portfolio_contract_exposes_persisted_campaign_identity_and_opening_snapshot():
    db = _session()
    try:
        campaign, portfolio = _campaign_pair(db)
        ensure_initial_campaign_snapshot(db, campaign, portfolio)
        db.commit()

        response = get_paper_portfolio(db)

        assert response.id == portfolio.id
        assert response.campaign_id == campaign.id
        assert response.campaign_status == "READY_BLOCKED_DATA"
        assert response.campaign_started_at == campaign.starts_at
        assert response.campaign_ends_at == campaign.ends_at
        assert response.initial_cash == campaign.initial_capital_rials
        assert response.total_equity == campaign.initial_capital_rials
        assert response.portfolio_snapshot_id == f"snapshot_{campaign.id}_opening"
    finally:
        db.close()
