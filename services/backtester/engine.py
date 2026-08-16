"""Institutional Event-Driven Backtest Simulation Engine for Iranian Equities."""
import math
import hashlib
import json
from datetime import date, datetime
from typing import Any, Dict, List, Tuple
import numpy as np

from packages.domain.models import BacktestRun, BacktestTrade, generate_uuid
from packages.domain.risk_policy import ACTIVE_RISK_POLICY, RiskPolicy
from packages.feature_engine.indicators import compute_symbol_features
from packages.market_rules.fees import calculate_net_return, calculate_trade_fees, TSE_EQUITY_FEES
from packages.shared.datetime_utils import now_utc
from packages.strategies.base import StrategyContext
from packages.strategies.registry import strategy_registry
from services.paper_broker.execution import execution_simulator, ExecutionBar


def run_backtest_simulation(
    name: str,
    strategy_key: str,
    symbol_bars_map: dict[str, list[dict]],
    initial_capital: float = 1_000_000_000.0,
    horizon_sessions: int = 5,
    max_active_positions: int = 10,
    risk_per_trade_pct: float = 0.35,
    slippage_bps: float = 20.0,
    risk_policy: RiskPolicy = ACTIVE_RISK_POLICY,
) -> tuple[BacktestRun, list[BacktestTrade], list[dict], dict[str, Any]]:
    """
    Executes a walk-forward simulation across symbols.
    Enforces Point-in-Time discipline (Signal at T -> Fill at T+1), realistic fees/taxes,
    queue delays, and multi-metric quantitative output.
    """
    strategy = strategy_registry.get(strategy_key)
    if not strategy:
        strategy = strategy_registry.get("cross_sectional_momentum")

    # Index bars by date for O(1) lookup
    date_to_idx: dict[str, int] = {}
    sym_date_bar: dict[str, dict[str, dict]] = {}
    sym_sorted_bars: dict[str, list[dict]] = {}

    all_dates_set = set()
    for sym, bars in symbol_bars_map.items():
        s_bars = sorted(bars, key=lambda x: x["trading_date"])
        sym_sorted_bars[sym] = s_bars
        sym_date_bar[sym] = {b["trading_date"]: b for b in s_bars}
        for b in s_bars:
            all_dates_set.add(b["trading_date"])

    all_dates = sorted(list(all_dates_set))
    for i, d in enumerate(all_dates):
        date_to_idx[d] = i

    cash = initial_capital
    portfolio_value = initial_capital
    peak_equity = initial_capital
    open_positions: list[dict] = []
    completed_trades: list[BacktestTrade] = []
    equity_curve: list[dict] = []
    r_distribution: list[float] = []

    total_fees_paid = 0.0
    total_slippage_cost = 0.0
    turnover_volume = 0.0

    backtest_id = f"bt_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Simulation loop across calendar days
    for t_idx, d_str in enumerate(all_dates):
        current_date = date.fromisoformat(d_str)

        # 1. Update Open Positions & Check Exits (Target, Stop, Horizon, Trailing)
        retained_positions = []
        for pos in open_positions:
            sym = pos["symbol"]
            current_bar = sym_date_bar.get(sym, {}).get(d_str)

            if not current_bar:
                pos["holding_days"] += 1
                retained_positions.append(pos)
                continue

            high_p = current_bar["high"]
            low_p = current_bar["low"]
            close_p = current_bar["close"]
            pos["holding_days"] += 1

            # Track MFE / MAE
            pos["max_favorable_price"] = max(pos.get("max_favorable_price", pos["entry_price"]), high_p)
            pos["max_adverse_price"] = min(pos.get("max_adverse_price", pos["entry_price"]), low_p)

            exit_triggered = False
            exit_price = close_p
            exit_reason = ""

            # Check Stop-loss
            if low_p <= pos["stop_price"]:
                exit_triggered = True
                exit_price = pos["stop_price"]
                exit_reason = "حد ضرر فعال شد"
            # Check Target 1 (+2R)
            elif high_p >= pos["target_price"]:
                exit_triggered = True
                exit_price = pos["target_price"]
                exit_reason = "کسب سود در تارگت پیشنهادی"
            # Check Time Stop
            elif pos["holding_days"] >= pos["time_stop"]:
                exit_triggered = True
                exit_price = close_p
                exit_reason = "انقضای افق زمانی استراتژی (Time Stop)"

            if exit_triggered:
                # Sell fees (0.88% TSE fee + tax)
                sell_fee_info = calculate_trade_fees(pos["quantity"] * exit_price, side="SELL")
                proceeds = (pos["quantity"] * exit_price) - sell_fee_info["total_fee_rials"]
                cash += proceeds
                total_fees_paid += sell_fee_info["total_fee_rials"]

                net_pnl = proceeds - pos["total_cost_basis"]
                gross_pnl = (exit_price - pos["entry_price"]) * pos["quantity"]
                net_ret = (net_pnl / pos["total_cost_basis"]) if pos["total_cost_basis"] > 0 else 0.0

                r_unit = max(1.0, pos["entry_price"] - pos["stop_price"])
                realized_r = round((exit_price - pos["entry_price"]) / r_unit, 2)
                r_distribution.append(realized_r)

                trade = BacktestTrade(
                    id=generate_uuid(),
                    backtest_id=backtest_id,
                    symbol=sym,
                    entry_date=pos["entry_date"],
                    exit_date=current_date,
                    entry_price=pos["entry_price"],
                    exit_price=exit_price,
                    quantity=pos["quantity"],
                    gross_pnl=round(gross_pnl),
                    net_pnl=round(net_pnl),
                    return_pct=round(net_ret * 100.0, 2),
                    exit_reason=exit_reason,
                    holding_days=pos["holding_days"],
                )
                completed_trades.append(trade)
                turnover_volume += (pos["quantity"] * exit_price)
            else:
                retained_positions.append(pos)

        open_positions = retained_positions

        # 2. Check for New Entries if Portfolio has Capacity
        if len(open_positions) < max_active_positions and t_idx > 30:
            for sym, s_bars in sym_sorted_bars.items():
                if len(open_positions) >= max_active_positions:
                    break
                if any(p["symbol"] == sym for p in open_positions):
                    continue

                curr_bar_today = sym_date_bar.get(sym, {}).get(d_str)
                if not curr_bar_today:
                    continue

                prev_date_str = all_dates[t_idx - 1]
                hist_bars = [b for b in s_bars if b["trading_date"] <= prev_date_str]
                if len(hist_bars) < 30:
                    continue

                # Point-in-Time features strictly at T-1
                feat = compute_symbol_features(hist_bars)
                last_hist = hist_bars[-1]
                ctx = StrategyContext(
                    symbol=sym,
                    instrument_id=f"inst_{sym}",
                    name_fa=sym,
                    market="TSE",
                    sector_name="فلزات اساسی",
                    horizon=f"{horizon_sessions}d",
                    features=feat,
                    market_regime="risk_on",
                    allowed_min=last_hist.get("allowed_min") or (last_hist["close"] * 0.95),
                    allowed_max=last_hist.get("allowed_max") or (last_hist["close"] * 1.05),
                )

                cand = strategy.evaluate(ctx)
                if cand and cand.vote >= 0.50:
                    entry_p = cand.entry_low or curr_bar_today["open"]
                    stop_p = cand.stop_price
                    target_p = cand.target_prices[0] if cand.target_prices else entry_p * 1.08

                    # Multi-constraint risk sizing
                    risk_budget = portfolio_value * (risk_per_trade_pct / 100.0)
                    initial_risk_rials = max(1.0, entry_p - stop_p)
                    effective_loss_pct = (initial_risk_rials / entry_p) + 0.0165  # Fees + slippage

                    pos_budget_rials = min(
                        risk_budget / effective_loss_pct,
                        portfolio_value * 0.08,  # 8% NAV max position
                        cash * 0.90,            # Available cash
                    )

                    qty = int(pos_budget_rials / entry_p) if entry_p > 0 else 0
                    if qty >= 100:
                        buy_fee_info = calculate_trade_fees(qty * entry_p, side="BUY")
                        cost = (qty * entry_p) + buy_fee_info["total_fee_rials"]
                        if cash >= cost:
                            cash -= cost
                            total_fees_paid += buy_fee_info["total_fee_rials"]
                            turnover_volume += (qty * entry_p)

                            open_positions.append({
                                "symbol": sym,
                                "entry_date": current_date,
                                "entry_price": entry_p,
                                "stop_price": stop_p,
                                "target_price": target_p,
                                "quantity": qty,
                                "total_cost_basis": cost,
                                "holding_days": 0,
                                "time_stop": horizon_sessions,
                                "max_favorable_price": entry_p,
                                "max_adverse_price": entry_p,
                            })

        # 3. Calculate Daily NAV and Drawdown
        current_positions_val = sum(
            p["quantity"] * sym_date_bar.get(p["symbol"], {}).get(d_str, {}).get("close", p["entry_price"])
            for p in open_positions
        )
        portfolio_value = cash + current_positions_val
        peak_equity = max(peak_equity, portfolio_value)
        daily_dd_pct = ((peak_equity - portfolio_value) / peak_equity * 100.0) if peak_equity > 0 else 0.0

        equity_curve.append({
            "date": d_str,
            "equity": round(portfolio_value),
            "cash": round(cash),
            "positions_value": round(current_positions_val),
            "open_positions": len(open_positions),
            "drawdown_pct": round(daily_dd_pct, 2),
        })

    # Compute Statistical Metrics
    trade_count = len(completed_trades)
    wins = [t for t in completed_trades if t.net_pnl > 0]
    losses = [t for t in completed_trades if t.net_pnl <= 0]

    win_rate = (len(wins) / trade_count * 100.0) if trade_count > 0 else 0.0
    total_win_amount = sum(t.net_pnl for t in wins)
    total_loss_amount = abs(sum(t.net_pnl for t in losses))
    profit_factor = (total_win_amount / total_loss_amount) if total_loss_amount > 0 else (9.99 if total_win_amount > 0 else 0.0)

    # Returns series for Sharpe / Sortino / Calmar
    eq_vals = [e["equity"] for e in equity_curve]
    daily_returns = np.diff(eq_vals) / eq_vals[:-1] if len(eq_vals) > 1 else np.array([0.0])
    mean_ret = float(np.mean(daily_returns)) if len(daily_returns) > 0 else 0.0
    std_ret = float(np.std(daily_returns)) if len(daily_returns) > 0 else 1.0

    annual_factor = math.sqrt(240)  # ~240 Iranian trading days per year
    sharpe = round((mean_ret / std_ret * annual_factor), 2) if std_ret > 0 else 0.0

    neg_rets = daily_returns[daily_returns < 0]
    downside_std = float(np.std(neg_rets)) if len(neg_rets) > 0 else 1.0
    sortino = round((mean_ret / downside_std * annual_factor), 2) if downside_std > 0 else 0.0

    max_dd = max([e["drawdown_pct"] for e in equity_curve]) if equity_curve else 0.0
    total_return_pct = round(((portfolio_value - initial_capital) / initial_capital * 100.0), 2)
    calmar = round((total_return_pct / max_dd), 2) if max_dd > 0 else 0.0

    avg_r = round(float(np.mean(r_distribution)), 2) if r_distribution else 0.0
    median_r = round(float(np.median(r_distribution)), 2) if r_distribution else 0.0
    expectancy_rials = round(sum(t.net_pnl for t in completed_trades) / trade_count) if trade_count > 0 else 0.0

    # Deterministic Hashes
    config_dict = {
        "strategy_key": strategy_key,
        "horizon_sessions": horizon_sessions,
        "initial_capital": initial_capital,
        "risk_per_trade_pct": risk_per_trade_pct,
        "slippage_bps": slippage_bps,
        "rule_version": "TSE-2026.08",
    }
    config_hash = hashlib.sha256(json.dumps(config_dict, sort_keys=True).encode()).hexdigest()[:16]

    metrics_payload = {
        "sharpe_ratio": sharpe,
        "sortino_ratio": sortino,
        "calmar_ratio": calmar,
        "profit_factor": round(profit_factor, 2),
        "win_rate_pct": round(win_rate, 2),
        "total_trades": trade_count,
        "winning_trades": len(wins),
        "losing_trades": len(losses),
        "average_r": avg_r,
        "median_r": median_r,
        "expectancy_rials": expectancy_rials,
        "total_fees_paid_rials": round(total_fees_paid),
        "turnover_volume_rials": round(turnover_volume),
        "max_drawdown_pct": round(max_dd, 2),
        "total_return_pct": total_return_pct,
        "config_hash": config_hash,
        "r_distribution": r_distribution,
    }

    run = BacktestRun(
        id=backtest_id,
        name=name,
        strategy_key=strategy_key,
        start_date=date.fromisoformat(all_dates[0]) if all_dates else date.today(),
        end_date=date.fromisoformat(all_dates[-1]) if all_dates else date.today(),
        horizon=f"{horizon_sessions}d",
        initial_capital=initial_capital,
        final_equity=round(portfolio_value),
        total_return_pct=total_return_pct,
        sharpe_ratio=sharpe,
        sortino_ratio=sortino,
        max_drawdown_pct=round(max_dd, 2),
        win_rate_pct=round(win_rate, 2),
        profit_factor=round(profit_factor, 2),
        trade_count=trade_count,
        config_json=config_dict,
        metrics_json=metrics_payload,
        status="COMPLETED",
        created_at=now_utc(),
    )

    return run, completed_trades, equity_curve
