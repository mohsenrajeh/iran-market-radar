"""Unit tests for Strategy Learning Engine, Sample Sufficiency, and Research Queue."""
import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from packages.shared.database import Base
from packages.domain.models import (
    Portfolio,
    ClosedTradeHistory,
    TradePostMortem,
    StructuredLesson,
    ExperimentProposal,
    SampleSufficiency,
    ProposalStatus,
)
from packages.shared.datetime_utils import now_utc
from services.paper_broker.learning_engine import learning_engine


@pytest.fixture
def db_session():
    """Provides an isolated in-memory SQLite database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_outcome_bias_protection_good_process_loss(db_session):
    """Verifies that a trade with controlled loss and strict risk adherence is classified as GOOD_PROCESS_LOSS."""
    port = Portfolio(id="port_test_03", name="تست", cash=100_000_000_000.0)
    trade = ClosedTradeHistory(
        portfolio_id=port.id,
        symbol="شپنا",
        company_name="پالایش نفت اصفهان",
        sector="فرآورده‌های نفتی",
        strategy_id="s05_reversion",
        strategy_name_fa="بازگشت به میانگین",
        opened_at=now_utc() - timedelta(days=4),
        closed_at=now_utc(),
        holding_sessions=4,
        planned_entry=4700.0,
        avg_entry_price=4700.0,
        avg_exit_price=4465.0,
        total_quantity=50_000,
        gross_buy_value=235_000_000.0,
        gross_sell_value=223_250_000.0,
        entry_fees=872_320.0,
        exit_fees=859_512.0,
        tax=1_116_250.0,
        total_cost=2_848_082.0,
        gross_pnl=-11_750_000.0,
        net_pnl=-14_598_082.0,
        net_return_pct=-6.21,
        initial_risk_amount=15_000_000.0,
        initial_risk_pct_nav=0.35,
        realized_R=-0.95,
        MFE=1.5,
        MAE=5.2,
        initial_stop=4450.0,
        final_stop=4450.0,
        target1=5100.0,
        target2=5350.0,
        exit_reason="STOP_LOSS",
        market_regime_at_entry="neutral",
        market_regime_at_exit="risk_off",
        outcome_status="LOSS",
    )
    db_session.add_all([port, trade])
    db_session.flush()

    pm = learning_engine.generate_post_mortem(db_session, trade)
    db_session.commit()

    assert pm is not None
    # Must protect against Outcome Bias
    assert pm.outcome_vs_process_type == "GOOD_PROCESS_LOSS"
    assert pm.process_quality_score >= 80.0
    assert "کنترل ریسک" in pm.what_worked_fa


def test_sample_sufficiency_classification():
    """Tests sample sufficiency evaluation logic."""
    suff_1, fa_1 = learning_engine.evaluate_sample_sufficiency(n_samples=12, n_regimes=1)
    assert suff_1 == SampleSufficiency.INSUFFICIENT_SAMPLE

    suff_2, fa_2 = learning_engine.evaluate_sample_sufficiency(n_samples=35, n_regimes=2)
    assert suff_2 == SampleSufficiency.EARLY_EVIDENCE

    suff_3, fa_3 = learning_engine.evaluate_sample_sufficiency(n_samples=75, n_regimes=3)
    assert suff_3 == SampleSufficiency.EVALUATING

    suff_4, fa_4 = learning_engine.evaluate_sample_sufficiency(n_samples=150, n_regimes=3)
    assert suff_4 == SampleSufficiency.STATISTICALLY_STABLE


def test_research_queue_proposal_lifecycle(db_session):
    """Verifies proposal lifecycle without direct production mutation."""
    prop = ExperimentProposal(
        strategy_key="s03_breakout",
        strategy_name_fa="شکست حجم و نوسان",
        champion_version="v1.0",
        challenger_version="v1.1-vol-filter",
        status="PROPOSED",
        hypothesis_fa="افزودن فیلتر حجم ۱.۸ برابری نرخ برد را افزایش می‌دهد.",
        parameter_changes={"min_volume_multiplier": 1.8},
    )
    db_session.add(prop)
    db_session.commit()

    assert prop.status == "PROPOSED"

    # Simulate advance to BACKTESTING
    prop.status = "BACKTESTING"
    prop.backtest_metrics = {"win_rate": 64.2, "profit_factor": 2.05}
    db_session.commit()
    assert prop.status == "BACKTESTING"

    # Simulate advance to PAPER_CHALLENGER
    prop.status = "PAPER_CHALLENGER"
    db_session.commit()
    assert prop.status == "PAPER_CHALLENGER"
