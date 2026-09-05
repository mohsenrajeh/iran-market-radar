"""Archive legacy state and start a versioned 30-day, 10B-toman paper campaign."""
from __future__ import annotations

import argparse
import sys
from datetime import timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from packages.domain.models import CashLedger, PaperCampaign, Portfolio
from packages.shared.config import settings
from packages.shared.database import SyncSessionLocal, init_db_sync
from packages.shared.datetime_utils import now_utc
from services.paper_broker.campaign import ACTIVE_CAMPAIGN_STATUSES, ensure_initial_campaign_snapshot


REQUIRED_BACKUP = ROOT / "backups" / "iran_market_radar_pre_overhaul_20260817.dump"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm-archive-existing", action="store_true")
    args = parser.parse_args()
    if settings.trading_mode != "paper" or settings.live_trading_enabled:
        raise SystemExit("Campaign creation is allowed only in locked paper mode.")

    init_db_sync()
    db = SyncSessionLocal()
    try:
        existing_state = bool(
            db.query(PaperCampaign.id).first()
            or db.query(Portfolio.id).first()
        )
        if existing_state and not args.confirm_archive_existing:
            raise SystemExit("Refusing to change existing campaign state without --confirm-archive-existing")
        if existing_state and (
            not REQUIRED_BACKUP.exists() or REQUIRED_BACKUP.stat().st_size < 1024
        ):
            raise SystemExit(f"Required rollback backup is missing or invalid: {REQUIRED_BACKUP}")

        active_campaigns = (
            db.query(PaperCampaign)
            .filter(PaperCampaign.status.in_(ACTIVE_CAMPAIGN_STATUSES))
            .order_by(PaperCampaign.created_at.desc())
            .all()
        )
        if len(active_campaigns) > 1:
            raise RuntimeError("Multiple active paper campaigns exist; refusing ambiguous repair.")
        existing_campaign = active_campaigns[0] if active_campaigns else None
        if existing_campaign:
            target = db.query(Portfolio).filter(Portfolio.id == existing_campaign.portfolio_id).first()
            if target is None:
                raise RuntimeError(f"Campaign {existing_campaign.id} references a missing portfolio.")
            for portfolio in db.query(Portfolio).all():
                portfolio.is_active = portfolio.id == target.id
                if portfolio.id != target.id:
                    portfolio.kill_switch_active = True
            target.kill_switch_active = True
            opening_snapshot_created = ensure_initial_campaign_snapshot(db, existing_campaign, target)
            db.commit()
            print(
                f"Campaign {existing_campaign.id} retained; repaired single-active-portfolio invariant; "
                f"opening_snapshot_created={opening_snapshot_created}."
            )
            return

        for portfolio in db.query(Portfolio).filter(Portfolio.is_active == True).all():
            portfolio.is_active = False
            portfolio.kill_switch_active = True

        tehran_now = now_utc().astimezone(ZoneInfo("Asia/Tehran"))
        campaign_id = f"campaign_{tehran_now.strftime('%Y%m%d')}"
        portfolio_id = f"portfolio_{tehran_now.strftime('%Y%m%d')}_10b"
        if db.query(PaperCampaign).filter(PaperCampaign.id == campaign_id).first():
            raise RuntimeError(f"Campaign ID {campaign_id} already exists; refusing reuse.")
        if db.query(Portfolio).filter(Portfolio.id == portfolio_id).first():
            raise RuntimeError(f"Portfolio ID {portfolio_id} already exists; refusing reuse.")
        capital = float(settings.initial_portfolio_cash_rials)
        portfolio = Portfolio(
            id=portfolio_id,
            name="پورتفوی کمپین ۳۰روزه ۱۰ میلیارد تومانی",
            mode="paper",
            cash=capital,
            initial_cash=capital,
            realized_pnl=0.0,
            is_active=True,
            kill_switch_active=True,
        )
        campaign = PaperCampaign(
            id=campaign_id,
            portfolio_id=portfolio_id,
            name_fa="آزمون ۳۰روزه استراتژی همگرایی مستقل",
            status="READY_BLOCKED_DATA",
            starts_at=tehran_now,
            ends_at=tehran_now + timedelta(days=30),
            initial_capital_rials=capital,
            config_snapshot={
                "market_data_mode": settings.market_data_mode,
                "minimum_fundamental_sources": settings.minimum_fundamental_sources,
                "risk_policy": "ACTIVE_RISK_POLICY",
                "paper_only": True,
            },
        )
        ledger = CashLedger(
            portfolio_id=portfolio_id,
            transaction_type="INITIAL",
            amount_rials=capital,
            settled_cash=capital,
            available_cash=capital,
            description_fa="سرمایه اولیه کمپین ۳۰روزه: ۱۰ میلیارد تومان",
        )
        db.add(portfolio)
        db.flush()
        db.add_all([campaign, ledger])
        # The invariant checker intentionally reads the persisted ledger rows.
        # Flush the pristine opening state before asking it to create the
        # immutable opening NAV point; the transaction is still atomic.
        db.flush()
        ensure_initial_campaign_snapshot(db, campaign, portfolio)
        db.commit()
        print(f"Created {campaign_id} with 100,000,000,000 IRR; legacy portfolios were archived, not deleted.")
        print("Kill switch remains active until official market and fundamental data gates pass.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
