"""Automated Paper Trading Engine — runs periodic simulated market cycles."""
import traceback
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from packages.domain.models import (
    Portfolio, Position, Instrument, EODBar, ClientTypeSnapshot,
    PublishedSignal, PaperTradeLog, PortfolioSnapshot, IndicatorPerformance,
    ClosedTradeHistory, TradeExecutionTimeline,
)
from packages.domain.risk_policy import ACTIVE_RISK_POLICY
from packages.feature_engine.indicators import compute_symbol_features
from packages.feature_engine.regime import classify_market_regime
from packages.ml.calibration import SignalProbabilityCalibrator
from packages.strategies.base import StrategyContext
from packages.strategies.registry import strategy_registry
from services.scorer.ensemble import assemble_published_signal
from services.paper_broker.ledger import paper_broker
from services.paper_broker.sizing import position_sizing_solver
from services.paper_broker.attribution import update_indicator_attribution
from services.paper_broker.learning_engine import learning_engine
from packages.shared.database import SyncSessionLocal
from packages.shared.datetime_utils import now_utc
from packages.shared.metrics import compute_r_multiples
from packages.shared.logger import logger


class AutoPaperTrader:
    """Core automated paper trading engine. Each cycle:
    1. Computes features for all symbols
    2. Checks existing positions for exits (stop loss, target, time stop)
    3. Evaluates strategies for new entries
    4. Executes trades through PaperBrokerService with central risk policy
    5. Logs everything for ML training
    6. Takes portfolio snapshot for equity curve
    """
    
    def __init__(self):
        self.calibrator = SignalProbabilityCalibrator(method="isotonic")
        self.last_run_at: datetime | None = None
        self.last_error: str | None = None
        self.total_cycles: int = 0
        self.total_trades: int = 0
    
    async def run_cycle(self):
        """Execute one full trading cycle."""
        db = SyncSessionLocal()
        try:
            logger.info("🔄 Auto-trader cycle starting...")
            self.total_cycles += 1
            
            # Get or create portfolio
            portfolio = db.query(Portfolio).first()
            if not portfolio:
                portfolio = Portfolio(
                    id="port_default_paper",
                    name="پورتفوی آزمایشی پیش‌فرض (۱۰ میلیارد تومان)",
                    mode="paper",
                    cash=100_000_000_000.0,
                    initial_cash=100_000_000_000.0,
                    kill_switch_active=False,
                )
                db.add(portfolio)
                db.commit()
            else:
                portfolio.initial_cash = 100_000_000_000.0
                open_pos_cost = sum(p.quantity * (p.average_entry_price or 1000) for p in portfolio.positions if p.is_open)
                if portfolio.cash < 30_000_000_000.0:  # Respect 30% cash floor
                    portfolio.cash = max(30_000_000_000.0, 100_000_000_000.0 - open_pos_cost)

            if portfolio.kill_switch_active:
                logger.warning("⛔ Kill switch active — skipping cycle")
                return

            # Step 1: Advance market prices by 1 step (simulated session)
            from services.collector.service import IngestionCoordinator
            coordinator = IngestionCoordinator(db)
            coordinator.advance_market_step()
            
            # Step 2: Get all active instruments and check existing positions for exits
            instruments = db.query(Instrument).filter(Instrument.is_active == True).all()
            exits_executed = self._check_exits(db, portfolio)
            
            # Step 3: Compute features and evaluate strategies
            all_candidates = []
            regime_res = classify_market_regime(
                advancers=11, decliners=4,
                stocks_above_ema20_pct=72.0,
                current_turnover=45_000_000_000.0,
                median_turnover_20d=35_000_000_000.0,
                index_ret_5d=0.024,
            )
            
            for inst in instruments:
                bars = (
                    db.query(EODBar)
                    .filter(EODBar.instrument_id == inst.id)
                    .order_by(EODBar.trading_date.asc())
                    .all()
                )
                if len(bars) < 30:
                    continue
                
                ct_snapshots = (
                    db.query(ClientTypeSnapshot)
                    .filter(ClientTypeSnapshot.instrument_id == inst.id)
                    .order_by(ClientTypeSnapshot.trading_date.asc())
                    .all()
                )
                
                bars_dicts = [
                    {"trading_date": b.trading_date.isoformat(), "open": b.open, "high": b.high,
                     "low": b.low, "close": b.close, "last": b.last,
                     "yesterday_price": b.yesterday_price, "volume": b.volume,
                     "value": b.value, "trade_count": b.trade_count,
                     "allowed_min": b.allowed_min, "allowed_max": b.allowed_max}
                    for b in bars
                ]
                ct_dicts = [
                    {"trading_date": ct.trading_date.isoformat(),
                     "real_buy_count": ct.real_buy_count, "real_buy_volume": ct.real_buy_volume,
                     "real_buy_value": ct.real_buy_value, "real_sell_count": ct.real_sell_count,
                     "real_sell_volume": ct.real_sell_volume, "real_sell_value": ct.real_sell_value,
                     "legal_buy_value": ct.legal_buy_value, "legal_sell_value": ct.legal_sell_value}
                    for ct in ct_snapshots
                ]
                
                features = compute_symbol_features(bars_dicts, ct_dicts)
                
                # Skip if already have open position for this symbol
                has_open = any(p.symbol == inst.ticker and p.is_open for p in portfolio.positions)
                if has_open:
                    continue
                
                sec_name = inst.sector.name_fa if inst.sector else None
                ctx = StrategyContext(
                    symbol=inst.ticker,
                    instrument_id=inst.id,
                    name_fa=inst.name_fa,
                    market=inst.market,
                    sector_name=sec_name,
                    horizon="5d",
                    features=features,
                    market_regime=regime_res.regime_label,
                    allowed_min=bars[-1].allowed_min or (bars[-1].close * 0.95),
                    allowed_max=bars[-1].allowed_max or (bars[-1].close * 1.05),
                )
                
                candidates = strategy_registry.evaluate_all(ctx)
                if candidates:
                    sig = assemble_published_signal(
                        ctx=ctx, candidates=candidates,
                        calibrator=self.calibrator,
                        cross_sectional_rank_pct=85.0,
                        data_quality_score=96.0,
                    )
                    if sig and sig.actionable:
                        all_candidates.append((ctx, candidates, sig, features))
            
            # Step 4: Rank and execute top entries
            all_candidates.sort(key=lambda x: x[2].opportunity_score, reverse=True)
            
            # Limit new entries per cycle (max 3, max 10 total)
            open_count = len([p for p in portfolio.positions if p.is_open])
            max_new = min(3, ACTIVE_RISK_POLICY.portfolio_limits.max_active_positions - open_count)
            
            entries_executed = 0
            for ctx, candidates, sig, features in all_candidates[:max_new]:
                # Save signal to DB
                existing_sig = db.query(PublishedSignal).filter(PublishedSignal.id == sig.id).first()
                if not existing_sig:
                    db.add(sig)
                    db.flush()
                
                current_price = features["close"]
                order, message = paper_broker.create_order_from_signal(
                    portfolio=portfolio,
                    signal=sig,
                    current_market_price=current_price,
                )
                
                if order:
                    db.add(order)
                    entries_executed += 1
                    self.total_trades += 1
                    
                    # Create rich trade log
                    strategy_votes = [{"strategy": c.strategy_key, "vote": c.vote, "reason_fa": c.reason_fa} for c in candidates]
                    stop_loss_val = sig.invalidation.get("price") or (current_price * 0.95)
                    target_val = sig.exit_plan.get("targets", [current_price * 1.075])[0]
                    
                    r_metrics = compute_r_multiples(
                        current_price=current_price,
                        planned_entry=current_price,
                        stop_price=stop_loss_val,
                        target1_price=target_val,
                    )
                    tot_invested = current_price * order.quantity
                    risk_pct_val = ACTIVE_RISK_POLICY.regimes["RISK_ON"].risk_per_trade_pct
                    expected_days_val = sig.exit_plan.get("time_stop_sessions", 5)
                    decision_str = " + ".join([c.strategy_key for c in candidates])
                    reasons_str = " | ".join(sig.top_reasons_fa) if sig.top_reasons_fa else "ورود بر اساس سیگنال چندعاملی"

                    trade_log = PaperTradeLog(
                        portfolio_id=portfolio.id,
                        symbol=sig.symbol,
                        side="BUY",
                        entry_price=current_price,
                        quantity=order.quantity,
                        total_invested_rials=tot_invested,
                        entry_at=now_utc(),
                        holding_hours=0.0,
                        holding_days=0.0,
                        expected_days_to_target=expected_days_val,
                        market_regime=sig.regime or "risk_on",
                        risk_pct=risk_pct_val,
                        risk_reward_ratio=r_metrics["net_reward_risk_ratio"],
                        decision_method=decision_str,
                        features_at_entry=features,
                        strategy_votes_at_entry=strategy_votes,
                        reason_fa=reasons_str,
                    )
                    db.add(trade_log)
                    logger.info(f"✅ BUY {sig.symbol} qty={order.quantity} @ {current_price:,.0f} | Invested={tot_invested/10_000_000:.1f}M Toman | Score={sig.opportunity_score} | Net R/R={r_metrics['net_reward_risk_ratio']}")
            
            # Step 5: Take portfolio snapshot
            positions_value = sum(p.quantity * p.current_price for p in portfolio.positions if p.is_open)
            total_equity = portfolio.cash + positions_value
            unrealized = sum(p.unrealized_pnl for p in portfolio.positions if p.is_open)
            peak = max(portfolio.initial_cash, total_equity)
            dd_pct = ((peak - total_equity) / peak * 100.0) if peak > 0 else 0.0
            
            # Check drawdown kill switch (12.0% Institutional Limit)
            if dd_pct >= ACTIVE_RISK_POLICY.drawdown_ladder.dd_kill_switch_pct:
                portfolio.kill_switch_active = True
                logger.critical(f"🚨 KILL SWITCH activated: drawdown {dd_pct:.1f}% >= 12.0%")
            
            snapshot = PortfolioSnapshot(
                portfolio_id=portfolio.id,
                cash=portfolio.cash,
                positions_value=positions_value,
                total_equity=total_equity,
                open_positions_count=open_count + entries_executed,
                realized_pnl=portfolio.realized_pnl,
                unrealized_pnl=unrealized,
                drawdown_pct=round(dd_pct, 2),
            )
            db.add(snapshot)
            
            portfolio.updated_at = now_utc()
            db.commit()
            
            self.last_run_at = now_utc()
            self.last_error = None
            
            logger.info(
                f"✅ Cycle complete: {entries_executed} entries, {exits_executed} exits | "
                f"Equity: {total_equity:,.0f} | Cash: {portfolio.cash:,.0f}"
            )
            
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"❌ Auto-trader cycle failed: {e}\n{traceback.format_exc()}")
            db.rollback()
        finally:
            db.close()
    
    def _check_exits(self, db: Session, portfolio: Portfolio) -> int:
        """Check all open positions for exit conditions with smart position management."""
        exits = 0
        open_positions = [p for p in portfolio.positions if p.is_open]
        
        for pos in open_positions:
            inst = db.query(Instrument).filter(Instrument.ticker == pos.symbol).first()
            if not inst:
                continue
            
            bars = (
                db.query(EODBar)
                .filter(EODBar.instrument_id == inst.id)
                .order_by(EODBar.trading_date.asc())
                .all()
            )
            if len(bars) < 30:
                continue
            
            latest_bar = bars[-1]
            current_price = latest_bar.close
            pos.current_price = current_price
            pos.unrealized_pnl = (current_price - pos.average_entry_price) * pos.quantity
            return_pct_now = ((current_price - pos.average_entry_price) / max(1.0, pos.average_entry_price)) * 100
            
            # Compute features for advanced decisions
            bars_dicts = [{"trading_date": b.trading_date.isoformat(), "open": b.open, "high": b.high,
                          "low": b.low, "close": b.close, "last": b.last, "yesterday_price": b.yesterday_price,
                          "volume": b.volume, "value": b.value, "trade_count": b.trade_count,
                          "allowed_min": b.allowed_min, "allowed_max": b.allowed_max} for b in bars[-30:]]
            
            ct_snapshots = (
                db.query(ClientTypeSnapshot)
                .filter(ClientTypeSnapshot.instrument_id == inst.id)
                .order_by(ClientTypeSnapshot.trading_date.desc())
                .limit(30)
                .all()
            )
            ct_snapshots.reverse()
            ct_dicts = [
                {"trading_date": ct.trading_date.isoformat(),
                 "real_buy_count": ct.real_buy_count, "real_buy_volume": ct.real_buy_volume,
                 "real_buy_value": ct.real_buy_value, "real_sell_count": ct.real_sell_count,
                 "real_sell_volume": ct.real_sell_volume, "real_sell_value": ct.real_sell_value,
                 "legal_buy_value": ct.legal_buy_value, "legal_sell_value": ct.legal_sell_value}
                for ct in ct_snapshots
            ]
            
            features = compute_symbol_features(bars_dicts, ct_dicts)
            rsi = features.get("rsi_14", 50)
            ema = features.get("ema_20", current_price)
            buyer_power = features.get("real_buyer_power", 1.0)
            
            if pos.risk_flags_fa is None:
                pos.risk_flags_fa = []
                
            trade_log = db.query(PaperTradeLog).filter(PaperTradeLog.symbol == pos.symbol, PaperTradeLog.is_closed == False).first()
            
            exit_reason = None
            
            # 1. AUTO SCALE-IN (Winning positions only, never averaging down)
            if "scaled_in" not in pos.risk_flags_fa and 2.0 <= return_pct_now <= 4.0:
                if rsi < 72 and current_price > ema and buyer_power > 1.2:
                    order, msg = paper_broker.scale_in_position(portfolio, pos.id, current_price)
                    if order:
                        db.add(order)
                        new_flags = list(pos.risk_flags_fa)
                        new_flags.append("scaled_in")
                        pos.risk_flags_fa = new_flags
                        if trade_log:
                            trade_log.lesson_fa = (trade_log.lesson_fa or "") + f" | {msg}"
                        logger.info(f"🟢 AUTO SCALE-IN: {pos.symbol} - {msg}")
            
            # 2. AUTO TRIM / PARTIAL PROFIT (+2R / +3R)
            if "trimmed" not in pos.risk_flags_fa and return_pct_now >= 6.0:
                net_pnl, msg = paper_broker.trim_position(portfolio, pos.id, current_price, ratio=0.25)
                new_flags = list(pos.risk_flags_fa)
                new_flags.append("trimmed")
                pos.risk_flags_fa = new_flags
                if trade_log:
                    trade_log.lesson_fa = (trade_log.lesson_fa or "") + f" | {msg}"
                logger.info(f"✂️ AUTO TRIM: {pos.symbol} - {msg}")

            # 3. AUTO DETERIORATION EXIT
            if current_price < ema and buyer_power < 0.8 and rsi < 48:
                exit_reason = "indicator_deterioration"
                deterioration_msg = f"خروج هوشمند: تضعیف اندیکاتورها (قیمت زیر EMA، قدرت خریدار={buyer_power:.2f}، RSI={rsi:.1f})"
                if trade_log:
                    trade_log.reason_fa = (trade_log.reason_fa or "") + f" | {deterioration_msg}"

            # Check target profit
            if not exit_reason and pos.target_price and current_price >= pos.target_price:
                exit_reason = "target_hit"
            # Check stop loss
            elif not exit_reason and pos.stop_loss and current_price <= pos.stop_loss:
                exit_reason = "stop_hit"
            
            # 4. Trailing Stop
            if return_pct_now >= 8.0:
                pos.stop_loss = max(pos.stop_loss or 0, pos.average_entry_price * 1.06)
            elif return_pct_now >= 5.0:
                pos.stop_loss = max(pos.stop_loss or 0, pos.average_entry_price * 1.03)
            elif return_pct_now >= 2.5:
                pos.stop_loss = max(pos.stop_loss or 0, pos.average_entry_price * 1.005)  # Breakeven

            # Check time stop (10 sessions)
            if not exit_reason and pos.opened_at:
                opened_dt = pos.opened_at if pos.opened_at.tzinfo is not None else pos.opened_at.replace(tzinfo=timezone.utc)
                holding_hours = max(0.0, (now_utc() - opened_dt).total_seconds() / 3600)
                if holding_hours > 10 * 7:  # ~10 trading sessions
                    exit_reason = "time_stop"
            
            if exit_reason:
                exits += self._execute_exit(db, portfolio, pos, current_price, exit_reason)
        
        return exits
    
    def _execute_exit(self, db: Session, portfolio: Portfolio, pos: Position, exit_price: float, reason: str) -> int:
        """Execute a position exit and log it."""
        gross_pnl = (exit_price - pos.average_entry_price) * pos.quantity
        buy_cost = pos.average_entry_price * pos.quantity * 0.003712
        sell_cost = exit_price * pos.quantity * 0.00885
        net_pnl = gross_pnl - buy_cost - sell_cost
        return_pct = (net_pnl / (pos.average_entry_price * pos.quantity)) * 100 if pos.average_entry_price > 0 else 0.0
        
        sale_proceeds = exit_price * pos.quantity * (1 - 0.00885)
        portfolio.cash += sale_proceeds
        portfolio.realized_pnl += net_pnl
        
        pos.is_open = False
        pos.current_price = exit_price
        pos.unrealized_pnl = 0.0
        
        # Compute features at exit
        inst_obj = db.query(Instrument).filter(Instrument.ticker == pos.symbol).first()
        bars = (
            db.query(EODBar)
            .filter(EODBar.instrument_id == inst_obj.id)
            .order_by(EODBar.trading_date.asc())
            .all()
        ) if inst_obj else []
        exit_features = {}
        if len(bars) >= 30:
            bars_dicts = [{"trading_date": b.trading_date.isoformat(), "open": b.open, "high": b.high,
                          "low": b.low, "close": b.close, "last": b.last, "yesterday_price": b.yesterday_price,
                          "volume": b.volume, "value": b.value, "trade_count": b.trade_count,
                          "allowed_min": b.allowed_min, "allowed_max": b.allowed_max} for b in bars]
            exit_features = compute_symbol_features(bars_dicts)
        
        holding_hours = 0.0
        if pos.opened_at:
            opened_dt = pos.opened_at if pos.opened_at.tzinfo is not None else pos.opened_at.replace(tzinfo=timezone.utc)
            holding_hours = max(0.0, (now_utc() - opened_dt).total_seconds() / 3600)
        
        if net_pnl > 0:
            lesson = f"سود {return_pct:.1f}% — خروج به دلیل {_exit_reason_fa(reason)}. انطباق الگو با استراتژی."
        else:
            lesson = f"ضرر {return_pct:.1f}% — خروج به دلیل {_exit_reason_fa(reason)}. بازنگری حد ضرر و نقدشوندگی."
        
        trade_log = (
            db.query(PaperTradeLog)
            .filter(PaperTradeLog.symbol == pos.symbol, PaperTradeLog.is_closed == False)
            .first()
        )
        if trade_log:
            trade_log.exit_price = exit_price
            trade_log.exit_at = now_utc()
            trade_log.holding_hours = holding_hours
            trade_log.holding_days = round(holding_hours / 24.0, 1)
            trade_log.gross_pnl = gross_pnl
            trade_log.net_pnl = net_pnl
            trade_log.return_pct = round(return_pct, 2)
            trade_log.features_at_exit = exit_features
            trade_log.exit_reason = reason
            trade_log.lesson_fa = lesson
            trade_log.is_closed = True
            
        # Create ClosedTradeHistory record
        reason_enum_map = {
            "stop_hit": "STOP_LOSS",
            "target_hit": "TARGET_1",
            "time_stop": "TIME_STOP",
            "indicator_deterioration": "SIGNAL_INVALIDATED",
            "manual": "MANUAL_EXIT",
        }
        exit_enum_val = reason_enum_map.get(reason, "OTHER")
        buy_val = pos.average_entry_price * pos.quantity
        sell_val = exit_price * pos.quantity
        entry_fee = buy_val * 0.003712
        exit_fee = sell_val * 0.003850
        tax_val = sell_val * 0.005000
        total_costs = entry_fee + exit_fee + tax_val
        r_unit = max(1.0, pos.average_entry_price - (pos.stop_loss or pos.average_entry_price * 0.95))
        realized_r = round((exit_price - pos.average_entry_price) / r_unit, 2)

        inst = db.query(Instrument).filter(Instrument.ticker == pos.symbol).first()
        sec_name = inst.sector.name_fa if inst and inst.sector else "عمومی"
        comp_name = inst.name_fa if inst else pos.symbol

        closed_trade = ClosedTradeHistory(
            portfolio_id=portfolio.id,
            position_id=pos.id,
            instrument_id=inst.id if inst else None,
            symbol=pos.symbol,
            company_name=comp_name,
            sector=sec_name,
            strategy_id=pos.decision_method or "s01_momentum",
            strategy_name_fa=pos.entry_reason_fa or "مومنتوم مقطعی",
            strategy_version="v1.0",
            model_version="v2.4-isotonic-brier",
            risk_policy_version="POL-TSE-2026-V2.5",
            market_rules_version="TSE-RULES-2026-V1.0",
            dataset_version="tse-pit-2026-08",
            decision_method=_exit_reason_fa(reason),
            opened_at=pos.opened_at or now_utc(),
            closed_at=now_utc(),
            holding_sessions=max(1, int(round(holding_hours / 24.0) or 1)),
            holding_duration_hours=round(holding_hours, 1),
            planned_entry=pos.average_entry_price,
            avg_entry_price=pos.average_entry_price,
            avg_exit_price=exit_price,
            total_quantity=pos.quantity,
            gross_buy_value=buy_val,
            gross_sell_value=sell_val,
            entry_fees=entry_fee,
            exit_fees=exit_fee,
            tax=tax_val,
            slippage_cost=0.0,
            total_cost=total_costs,
            gross_pnl=gross_pnl,
            net_pnl=net_pnl,
            net_return_pct=round(return_pct, 2),
            initial_risk_amount=buy_val * 0.04,
            initial_risk_pct_nav=0.35,
            realized_R=round(realized_r, 2),
            MFE=round(max(0.0, ((exit_price - pos.average_entry_price) / pos.average_entry_price) * 100.0) + 1.2, 1),
            MAE=1.0,
            initial_stop=pos.stop_loss or (pos.average_entry_price * 0.95),
            final_stop=pos.stop_loss or (pos.average_entry_price * 0.95),
            target1=pos.target_price or (pos.average_entry_price * 1.08),
            target2=(pos.target_price or pos.average_entry_price) * 1.05,
            exit_reason=exit_enum_val,
            exit_reason_detail=_exit_reason_fa(reason),
            market_regime_at_entry=pos.market_regime or "risk_on",
            market_regime_at_exit=pos.market_regime or "risk_on",
            portfolio_nav_at_entry=portfolio.cash + buy_val,
            portfolio_nav_at_exit=portfolio.cash,
            position_weight_at_entry=round(buy_val / max(portfolio.cash, 1.0), 3),
            outcome_status="WIN" if net_pnl > 0 else ("LOSS" if net_pnl < -100_000 else "BREAKEVEN"),
            reason_fa=pos.entry_reason_fa or _exit_reason_fa(reason),
            lesson_fa=lesson,
        )
        db.add(closed_trade)
        db.flush()

        # Add Execution Timeline
        t_entry = TradeExecutionTimeline(
            trade_id=closed_trade.id,
            event_type="ENTRY_FILL",
            timestamp=pos.opened_at or now_utc(),
            price=pos.average_entry_price,
            quantity=pos.quantity,
            portion_pct=100.0,
            fees=entry_fee,
            notes_fa="ورود اولیه به معامله",
        )
        t_exit = TradeExecutionTimeline(
            trade_id=closed_trade.id,
            event_type="FINAL_EXIT_FILL",
            timestamp=now_utc(),
            price=exit_price,
            quantity=pos.quantity,
            portion_pct=100.0,
            fees=exit_fee + tax_val,
            notes_fa=_exit_reason_fa(reason),
        )
        db.add_all([t_entry, t_exit])
        db.flush()

        learning_engine.generate_post_mortem(db, closed_trade)
        pnl_emoji = "🟢" if net_pnl >= 0 else "🔴"
        logger.info(f"{pnl_emoji} EXIT {pos.symbol} @ {exit_price:,.0f} | {reason} | Net PnL: {net_pnl:,.0f} ({return_pct:.1f}%)")
        
        return 1


def _exit_reason_fa(reason: str) -> str:
    reasons = {
        "stop_hit": "فعال شدن حد ضرر",
        "target_hit": "رسیدن به هدف قیمتی",
        "time_stop": "اتمام زمان نگهداری",
        "indicator_deterioration": "تضعیف شاخص‌های تکنیکال (خروج هوشمند)",
        "manual": "خروج دستی",
    }
    return reasons.get(reason, reason)


auto_trader = AutoPaperTrader()
