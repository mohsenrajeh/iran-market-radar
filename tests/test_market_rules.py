"""Unit tests for Iranian market fees, price limits, and queue feasibility."""
from packages.market_rules.fees import calculate_net_return, TSE_EQUITY_FEES, EQUITY_ETF_FEES
from packages.market_rules.price_limits import calculate_static_limits, apply_base_volume_rule
from packages.market_rules.queue_model import evaluate_execution_feasibility


def test_tse_equity_fee_deduction():
    entry_p = 1000.0
    exit_p = 1000.0
    # At flat price, net return must be strictly negative due to round-trip fees + tax + slippage
    net_ret = calculate_net_return(entry_p, exit_p, instrument_class="equity")
    assert net_ret < -0.012  # More than 1.2% total cost
    assert round(TSE_EQUITY_FEES.round_trip_rate * 100, 2) > 1.20


def test_static_price_limits():
    yesterday = 10000.0
    min_p, max_p = calculate_static_limits(yesterday, limit_pct=0.05)
    assert min_p == 9500.0
    assert max_p == 10500.0


def test_base_volume_dampening():
    yesterday = 1000.0
    avg_price = 1050.0  # +5%
    base_vol = 1_000_000
    traded_vol = 500_000  # Only half of base volume traded

    # Price rise must be dampened by 50%
    closing_p = apply_base_volume_rule(yesterday, avg_price, traded_vol, base_vol)
    assert closing_p == 1025.0


def test_queue_feasibility_limit_up():
    feasibility = evaluate_execution_feasibility(
        last_price=10500.0,
        allowed_min=9500.0,
        allowed_max=10500.0,
        bid_queue_volume=2_000_000,
        avg_daily_volume=1_000_000,
    )
    assert feasibility.is_locked_limit_up is True
    assert feasibility.fill_probability_score < 40.0
    assert len(feasibility.risk_flags_fa) > 0
