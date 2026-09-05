from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from packages.domain.models import Base, ClosedTradeHistory, DecisionAudit, Portfolio
from services.scorer.calibration_store import activate_candidate, load_active_calibrator, train_candidate


def test_walk_forward_candidate_is_persisted_and_reloaded_without_pickle():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    try:
        portfolio = Portfolio(id="cal_port", name="calibration", cash=100_000, initial_cash=100_000)
        db.add(portfolio)
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        for index in range(70):
            high_group = index % 2 == 0
            block_position = index // 2
            if index < 50:
                win = block_position % 25 < (18 if high_group else 7)
            else:
                oos_position = (index - 50) // 2
                win = oos_position < (7 if high_group else 3)
            decision = DecisionAudit(
                symbol=f"SYM{index}", decision="APPROVED_SUBMITTED",
                opportunity_score=90.0 if high_group else 10.0,
                p_profit=0.0, as_of=start + timedelta(days=index),
            )
            db.add(decision)
            db.flush()
            db.add(ClosedTradeHistory(
                portfolio_id=portfolio.id,
                symbol=f"SYM{index}",
                strategy_id="multi_family_confluence",
                decision_id=decision.id,
                opened_at=start + timedelta(days=index),
                closed_at=start + timedelta(days=index + 1),
                planned_entry=100.0,
                avg_entry_price=100.0,
                avg_exit_price=110.0 if win else 90.0,
                total_quantity=10,
                net_pnl=100.0 if win else -100.0,
                market_regime_at_entry="risk_on" if index % 3 else "risk_off",
                outcome_status="WIN" if win else "LOSS",
            ))
        db.commit()

        result = train_candidate(db, portfolio.id)
        assert result.allowed is True
        assert result.artifact is not None
        assert result.artifact.train_sample_size == 50
        assert result.artifact.oos_sample_size == 20
        assert result.artifact.brier_after < result.artifact.brier_before

        activate_candidate(db, result.artifact, "owner")
        db.commit()
        loaded = load_active_calibrator(db)
        assert loaded.is_fitted is True
        assert loaded.model_version == result.artifact.version
        assert loaded.predict_p_profit(0.9) > loaded.predict_p_profit(0.1)
    finally:
        db.close()
