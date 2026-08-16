"""Effective fee and tax calculations for Iranian capital markets with Decimal precision."""
from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass


@dataclass(frozen=True)
class TransactionCostSchedule:
    buy_fee_rate: Decimal        # Broker + Exchange + SEO fee on buy (0.3712%)
    sell_fee_rate: Decimal       # Broker + Exchange + SEO fee on sell (0.3850%)
    sell_tax_rate: Decimal       # Tax on sell (0.5000% مالیات نقل و انتقال)
    slippage_bps: Decimal = Decimal("10.0")  # Modeled base slippage in basis points (0.10%)

    @property
    def total_sell_deduction_rate(self) -> Decimal:
        return self.sell_fee_rate + self.sell_tax_rate

    @property
    def round_trip_rate(self) -> Decimal:
        """Exact round-trip fee rate: 0.003712 + 0.003850 + 0.005000 = 0.012562 (1.2562%)."""
        return self.buy_fee_rate + self.total_sell_deduction_rate


# Standard TSE Listed Equity Fee Schedule (Strict Decimal)
TSE_EQUITY_FEES = TransactionCostSchedule(
    buy_fee_rate=Decimal("0.003712"),    # 0.3712%
    sell_fee_rate=Decimal("0.003850"),   # 0.3850%
    sell_tax_rate=Decimal("0.005000"),   # 0.5000% (Standard TSE stock transfer tax)
    slippage_bps=Decimal("15.0"),        # 0.15% base slippage
)

# Standard Equity ETF Fee Schedule
EQUITY_ETF_FEES = TransactionCostSchedule(
    buy_fee_rate=Decimal("0.001160"),    # 0.1160%
    sell_fee_rate=Decimal("0.001160"),   # 0.1160%
    sell_tax_rate=Decimal("0.000000"),   # Tax exempt
    slippage_bps=Decimal("5.0"),
)


def get_cost_schedule(instrument_class: str = "equity") -> TransactionCostSchedule:
    """Returns appropriate fee schedule by instrument class."""
    if instrument_class in ("equity_etf", "etf"):
        return EQUITY_ETF_FEES
    return TSE_EQUITY_FEES


def calculate_net_return(
    entry_price: float,
    exit_price: float,
    instrument_class: str = "equity",
    custom_slippage_bps: float | None = None,
) -> float:
    """
    Computes realistic net return after deducting all buy fees, sell fees, taxes, and slippage.
    Exact Decimal calculation prevents floating-point rounding errors.
    """
    if entry_price <= 0:
        return 0.0

    p_in = Decimal(str(entry_price))
    p_out = Decimal(str(exit_price))
    costs = get_cost_schedule(instrument_class)

    slip_bps = Decimal(str(custom_slippage_bps)) if custom_slippage_bps is not None else costs.slippage_bps
    slippage_rate = slip_bps / Decimal("10000.0")

    # Effective buy cost includes buy fee + slippage
    effective_buy = p_in * (Decimal("1.0") + costs.buy_fee_rate + slippage_rate)

    # Effective sell proceeds after sell fees, tax, and slippage
    effective_sell = p_out * (Decimal("1.0") - costs.total_sell_deduction_rate - slippage_rate)

    net_return = (effective_sell - effective_buy) / effective_buy
    return float(net_return)


def calculate_trade_fees(trade_value_rials: float, side: str = "BUY", instrument_class: str = "equity") -> dict:
    """Calculates breakdown of broker fee, exchange fee, and tax in Rials."""
    val = Decimal(str(trade_value_rials))
    costs = get_cost_schedule(instrument_class)

    if side.upper() == "BUY":
        broker_exchange_fee = (val * costs.buy_fee_rate).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        tax = Decimal("0")
    else:
        broker_exchange_fee = (val * costs.sell_fee_rate).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        tax = (val * costs.sell_tax_rate).quantize(Decimal("1"), rounding=ROUND_HALF_UP)

    total_deduction = broker_exchange_fee + tax
    return {
        "broker_exchange_fee_rials": float(broker_exchange_fee),
        "tax_rials": float(tax),
        "total_fee_rials": float(total_deduction),
        "round_trip_pct": float(costs.round_trip_rate * Decimal("100")),  # 1.2562%
    }
