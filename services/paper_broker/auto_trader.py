"""Automated Paper Trading Engine — runs periodic simulated market cycles."""
import traceback
from datetime import datetime, timezone
from sqlalchemy import func
from sqlalchemy.orm import Session

from packages.domain.models import (
    Portfolio, Position, Instrument, EODBar, ClientTypeSnapshot,
    PublishedSignal, PaperTradeLog, PortfolioSnapshot, MarketSnapshot, DecisionAudit,
)
from packages.domain.risk_policy import ACTIVE_RISK_POLICY
from packages.feature_engine.indicators import compute_symbol_features
from packages.feature_engine.regime import compute_market_regime_from_db
from packages.ml.calibration import SignalProbabilityCalibrator
from packages.strategies.base import StrategyContext
from packages.strategies.registry import strategy_registry
from services.scorer.ensemble import assemble_published_signal
from services.paper_broker.ledger import paper_broker
from packages.shared.database import SyncSessionLocal
from packages.shared.datetime_utils import now_utc, to_utc_iso
from packages.shared.logger import logger
from packages.shared.config import settings
from services.collector.quality import evaluate_data_gate, instrument_data_quality_score
from services.scorer.fundamental_gate import evaluate_fundamental_gate
from services.scorer.calibration_store import load_active_calibrator
from services.paper_broker.campaign import get_active_campaign_portfolio
from services.collector.service import IngestionCoordinator
from services.collector.trusted_queries import (
    latest_trusted_market_snapshot, trusted_eod_query, trusted_client_type_query,
)
from packages.market_rules.trading_hours import is_tse_market_open


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

    async def run_cycle(
        self,
        *,
        manual: bool = False,
        sync_market: bool = True,
        provided_sync_stats: dict | None = None,
    ):
        """Execute one full trading cycle."""
        db = SyncSessionLocal()
        try:
            logger.info("🔄 Auto-trader cycle starting...")
            self.total_cycles += 1

            if settings.trading_mode != "paper" or settings.live_trading_enabled:
                raise RuntimeError("AutoPaperTrader is strictly paper-only.")
            if not manual and not settings.auto_paper_trading_enabled:
                reason = "AUTO_PAPER_TRADING_ENABLED is false."
                self.last_error = reason
                return {"executed": False, "reason": reason}
            if not is_tse_market_open():
                reason = "بازار تهران خارج از جلسهٔ پیوسته ۰۹:۰۰ تا ۱۲:۳۰ است."
                self.last_error = reason
                return {"executed": False, "reason": reason}
            coordinator = IngestionCoordinator(db)
            if sync_market:
                try:
                    sync_stats = await coordinator.sync_live_cycle()
                except RuntimeError as exc:
                    reason = f"همگام‌سازی دقیقه‌ای رسمی ناموفق بود: {exc}"
                    self.last_error = reason
                    return {"executed": False, "reason": reason}
            else:
                sync_stats = provided_sync_stats or {}
            if not sync_stats.get("trade_eligible"):
                reason = sync_stats.get("message_fa") or "منبع رسمی TSETMC پاسخ معتبر نداد؛ معامله مسدود ماند."
                self.last_error = reason
                return {"executed": False, "reason": reason, "sync": sync_stats}
            market_rows = int(sync_stats.get("market_rows") or 0)
            index_rows = int(sync_stats.get("index_rows") or 0)
            # The campaign must be initialized explicitly so history cannot leak across portfolios.
            portfolio = get_active_campaign_portfolio(db)
            if not portfolio:
                reason = "کمپین paper فعال و یکتا وجود ندارد؛ ابتدا ابزار start_paper_campaign را اجرا کنید."
                self.last_error = reason
                return {"executed": False, "reason": reason}
            self.calibrator = load_active_calibrator(db)
            # Risk-reducing exits may execute before the entry-only data gate.
            # Pending BUY/SCALE_IN orders must never cross that boundary.
            pending_sell_result = paper_broker.process_pending_orders(
                db, portfolio, allowed_sides={"SELL"},
            )

            # Step 2: Get all active instruments and check existing positions for exits
            instruments = db.query(Instrument).filter(Instrument.is_active == True).all()
            exits_executed = self._check_exits(db, portfolio)

            if portfolio.kill_switch_active:
                rejected_buys = paper_broker.process_pending_orders(
                    db, portfolio, allowed_sides={"BUY"},
                )
                db.commit()
                logger.warning("⛔ Kill switch active — exits processed; new buys remain blocked")
                return {
                    "executed": True,
                    "reason": "kill_switch_blocks_new_buys",
                    "exits_submitted": exits_executed,
                    "pending_fills": {
                        "processed": int(pending_sell_result.get("processed") or 0),
                        "filled": int(pending_sell_result.get("filled") or 0),
                        "messages": list(pending_sell_result.get("messages") or [])
                        + list(rejected_buys.get("messages") or []),
                    },
                }

            try:
                get_active_campaign_portfolio(db, require_execution_window=True)
            except RuntimeError as exc:
                rejected_buys = paper_broker.process_pending_orders(
                    db, portfolio, allowed_sides={"BUY"},
                )
                reason = str(exc)
                self.last_error = reason
                db.commit()
                return {
                    "executed": bool(pending_sell_result.get("filled") or exits_executed),
                    "reason": reason,
                    "pending_fills": {
                        "processed": int(pending_sell_result.get("processed") or 0),
                        "filled": int(pending_sell_result.get("filled") or 0),
                        "messages": list(pending_sell_result.get("messages") or [])
                        + list(rejected_buys.get("messages") or []),
                    },
                    "exits_submitted": exits_executed,
                }

            # Entry-only gate: fundamental/calibration readiness must never
            # prevent pending fills or risk-reducing exits above.
            data_gate = evaluate_data_gate(db, require_market_open=True)
            if not data_gate.allowed:
                reason = " | ".join(data_gate.reasons_fa)
                self.last_error = reason
                logger.warning("New paper entries blocked by data gate: %s", reason)
                db.commit()
                return {
                    "executed": bool(pending_sell_result.get("filled") or exits_executed),
                    "reason": reason,
                    "data_gate": data_gate.to_dict(),
                    "market_rows": market_rows,
                    "index_rows": index_rows,
                    "pending_fills": pending_sell_result,
                    "exits_submitted": exits_executed,
                }

            # Queued entries are considered only after the current gate passes.
            # The ledger also revalidates actionable + expiry at fill time.
            pending_buy_result = paper_broker.process_pending_orders(
                db, portfolio, allowed_sides={"BUY"},
            )
            pending_result = {
                "processed": int(pending_sell_result.get("processed") or 0)
                + int(pending_buy_result.get("processed") or 0),
                "filled": int(pending_sell_result.get("filled") or 0)
                + int(pending_buy_result.get("filled") or 0),
                "messages": list(pending_sell_result.get("messages") or [])
                + list(pending_buy_result.get("messages") or []),
            }

            # Step 3: Compute features and evaluate strategies
            pending_candidates = []
            regime_res = compute_market_regime_from_db(db)
            if regime_res is None:
                reason = "Insufficient official PIT evidence for market regime."
                self.last_error = reason
                db.commit()
                return {"executed": False, "reason": reason, "pending_fills": pending_result}

            for inst in instruments:
                bars = (
                    trusted_eod_query(db, inst.id)
                    .order_by(EODBar.trading_date.asc())
                    .all()
                )
                if len(bars) < settings.strategy_engine.min_history_sessions:
                    continue

                ct_snapshots = (
                    trusted_client_type_query(db, inst.id)
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

                latest_snapshot = latest_trusted_market_snapshot(
                    db, inst.id,
                    max_age_seconds=settings.quality.critical_market_stale_seconds,
                )
                if (
                    latest_snapshot is None
                    or latest_snapshot.allowed_min is None
                    or latest_snapshot.allowed_max is None
                    or latest_snapshot.allowed_min <= 0
                    or latest_snapshot.allowed_max <= 0
                ):
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
                    allowed_min=latest_snapshot.allowed_min,
                    allowed_max=latest_snapshot.allowed_max,
                )

                candidates = strategy_registry.evaluate_all(ctx)
                if candidates:
                    quality_score = instrument_data_quality_score(bars, ct_snapshots)
                    sample_support = min(100.0, len(bars) / settings.strategy_engine.min_history_sessions * 100.0)
                    pending_candidates.append((ctx, candidates, features, quality_score, sample_support))

            pending_candidates.sort(key=lambda item: max(candidate.vote for candidate in item[1]), reverse=True)
            all_candidates = []
            for rank_idx, (ctx, candidates, features, quality_score, sample_support) in enumerate(pending_candidates):
                rank_pct = 100.0 - (rank_idx / max(1, len(pending_candidates)) * 100.0)
                sig = assemble_published_signal(
                    ctx=ctx, candidates=candidates,
                    calibrator=self.calibrator,
                    cross_sectional_rank_pct=rank_pct,
                    data_quality_score=quality_score,
                    sample_support_score=sample_support,
                    fundamental_evidence=evaluate_fundamental_gate(db, ctx.instrument_id, ctx.symbol),
                )
                if sig and sig.actionable:
                    all_candidates.append((ctx, candidates, sig, features))

            # Step 4: Rank and execute top entries
            all_candidates.sort(key=lambda x: x[2].opportunity_score, reverse=True)

            # Limit new entries per cycle (max 3, max 10 total)
            open_count = len([p for p in portfolio.positions if p.is_open])
            max_new = max(0, min(3, ACTIVE_RISK_POLICY.portfolio_limits.max_active_positions - open_count))

            entries_executed = 0
            for ctx, candidates, sig, features in all_candidates[:max_new]:
                # Save signal to DB
                existing_sig = db.query(PublishedSignal).filter(PublishedSignal.id == sig.id).first()
                if not existing_sig:
                    db.add(sig)
                    db.flush()

                latest_snapshot = latest_trusted_market_snapshot(
                    db, ctx.instrument_id,
                    max_age_seconds=settings.quality.critical_market_stale_seconds,
                )
                if latest_snapshot is None:
                    continue
                current_price = latest_snapshot.last_price
                order, message = paper_broker.create_order_from_signal(
                    portfolio=portfolio,
                    signal=sig,
                    current_market_price=current_price,
                )

                if order:
                    db.add(order)
                    entries_executed += 1
                    logger.info(
                        "Paper BUY submitted for next official snapshot: %s qty=%s limit=%s score=%s",
                        sig.symbol, order.quantity, current_price, sig.opportunity_score,
                    )

            # Step 5: Take portfolio snapshot
            positions_value = sum(p.quantity * p.current_price for p in portfolio.positions if p.is_open)
            total_equity = portfolio.cash + positions_value
            unrealized = sum(p.unrealized_pnl for p in portfolio.positions if p.is_open)
            recorded_peak = db.query(func.max(PortfolioSnapshot.total_equity)).filter(
                PortfolioSnapshot.portfolio_id == portfolio.id
            ).scalar()
            peak = max(portfolio.initial_cash, total_equity, float(recorded_peak or 0.0))
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
                open_positions_count=open_count,
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
            return {
                "executed": True,
                "entries_submitted": entries_executed,
                "exits": exits_executed,
                "pending_fills": pending_result,
                "equity": total_equity,
            }

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"❌ Auto-trader cycle failed: {e}\n{traceback.format_exc()}")
            db.rollback()
            raise
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
                trusted_eod_query(db, inst.id)
                .order_by(EODBar.trading_date.asc())
                .all()
            )
            if len(bars) < 30:
                continue

            latest_snapshot = latest_trusted_market_snapshot(
                db, inst.id,
                max_age_seconds=settings.quality.critical_market_stale_seconds,
            )
            if latest_snapshot is None:
                continue
            current_price = latest_snapshot.last_price
            pos.current_price = current_price
            pos.unrealized_pnl = (current_price - pos.average_entry_price) * pos.quantity
            # Compute features for advanced decisions
            bars_dicts = [{"trading_date": b.trading_date.isoformat(), "open": b.open, "high": b.high,
                          "low": b.low, "close": b.close, "last": b.last, "yesterday_price": b.yesterday_price,
                          "volume": b.volume, "value": b.value, "trade_count": b.trade_count,
                          "allowed_min": b.allowed_min, "allowed_max": b.allowed_max} for b in bars[-30:]]

            ct_snapshots = (
                trusted_client_type_query(db, inst.id)
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
            rsi = features.get("rsi_14")
            ema = features.get("ema_20")
            buyer_power = features.get("real_buyer_power_ratio") if ct_snapshots else None

            if pos.risk_flags_fa is None:
                pos.risk_flags_fa = []

            trade_log = db.query(PaperTradeLog).filter(
                PaperTradeLog.portfolio_id == portfolio.id,
                PaperTradeLog.symbol == pos.symbol,
                PaperTradeLog.is_closed == False,
            ).first()
            entry_features = dict(trade_log.features_at_entry or {}) if trade_log else {}
            initial_stop = entry_features.get("initial_stop")
            initial_risk_per_share = (
                pos.average_entry_price - float(initial_stop)
                if initial_stop is not None and float(initial_stop) < pos.average_entry_price
                else 0.0
            )
            current_r = (
                (current_price - pos.average_entry_price) / initial_risk_per_share
                if initial_risk_per_share > 0
                else None
            )

            exit_reason = None
            if ema is not None and buyer_power is not None and rsi is not None and current_price < ema and buyer_power < 0.8 and rsi < 48:
                exit_reason = "indicator_deterioration"
                deterioration_msg = f"خروج هوشمند: تضعیف اندیکاتورها (قیمت زیر EMA، قدرت خریدار={buyer_power:.2f}، RSI={rsi:.1f})"
                if trade_log:
                    trade_log.reason_fa = (trade_log.reason_fa or "") + f" | {deterioration_msg}"
            if not exit_reason and pos.target_price is not None and current_price >= pos.target_price:
                exit_reason = "target_hit"
            elif not exit_reason and pos.stop_loss is not None and current_price <= pos.stop_loss:
                exit_reason = "stop_hit"

            # 1. AUTO SCALE-IN (Winning positions only, never averaging down)
            exit_policy = ACTIVE_RISK_POLICY.exit_management
            if (
                not exit_reason
                and current_r is not None
                and "scaled_in" not in pos.risk_flags_fa
                and exit_policy.scale_in_min_r <= current_r <= exit_policy.scale_in_max_r
            ):
                if rsi is not None and ema is not None and buyer_power is not None and rsi < 72 and current_price > ema and buyer_power > 1.2:
                    order, msg = paper_broker.scale_in_position(portfolio, pos.id, current_price)
                    if order:
                        db.add_all([order, DecisionAudit(
                            symbol=pos.symbol,
                            signal_id=entry_features.get("signal_id"),
                            model_version=entry_features.get("model_version") or "UNFITTED",
                            dataset_version=f"market_snapshot:{to_utc_iso(latest_snapshot.source_timestamp)}",
                            risk_policy_version=paper_broker.policy.policy_id,
                            decision="AUTO_SCALE_IN_SUBMITTED",
                            decision_reason_fa=f"افزایش حجم خودکار ثبت شد؛ اجرا فقط روی snapshot رسمی بعدی؛ order={order.id}",
                            opportunity_score=0.0,
                            p_profit=0.0,
                            as_of=latest_snapshot.source_timestamp,
                        )])
                        if trade_log:
                            trade_log.lesson_fa = (trade_log.lesson_fa or "") + f" | {msg}"
                        logger.info(f"🟢 AUTO SCALE-IN: {pos.symbol} - {msg}")

            # 2. AUTO TRIM / PARTIAL PROFIT (+2R / +3R)
            if (
                not exit_reason
                and current_r is not None
                and "trimmed" not in pos.risk_flags_fa
                and current_r >= exit_policy.trim_at_r
            ):
                order, msg = paper_broker.create_exit_order(
                    portfolio, pos.id, current_price, ratio=exit_policy.trim_fraction, reason_code="TARGET_1"
                )
                if order:
                    db.add_all([order, DecisionAudit(
                        symbol=pos.symbol,
                        signal_id=entry_features.get("signal_id"),
                        model_version=entry_features.get("model_version") or "UNFITTED",
                        dataset_version=f"market_snapshot:{to_utc_iso(latest_snapshot.source_timestamp)}",
                        risk_policy_version=paper_broker.policy.policy_id,
                        decision="AUTO_TRIM_SUBMITTED",
                        decision_reason_fa=f"کاهش حجم خودکار ثبت شد؛ اجرا فقط روی snapshot رسمی بعدی؛ order={order.id}",
                        opportunity_score=0.0,
                        p_profit=0.0,
                        as_of=latest_snapshot.source_timestamp,
                    )])
                    if trade_log:
                        trade_log.lesson_fa = (trade_log.lesson_fa or "") + f" | {msg}"
                    logger.info(f"✂️ AUTO TRIM SUBMITTED: {pos.symbol} - {msg}")

            # 4. R-based trailing stop. Every change is persisted as a decision.
            previous_stop = pos.stop_loss
            proposed_stop = previous_stop
            if not exit_reason and current_r is not None and initial_risk_per_share > 0:
                if current_r >= exit_policy.lock_one_r_trigger_r:
                    proposed_stop = max(previous_stop or 0.0, pos.average_entry_price + initial_risk_per_share)
                elif current_r >= exit_policy.lock_half_r_trigger_r:
                    proposed_stop = max(previous_stop or 0.0, pos.average_entry_price + 0.5 * initial_risk_per_share)
                elif current_r >= exit_policy.breakeven_trigger_r:
                    proposed_stop = max(previous_stop or 0.0, pos.average_entry_price)
            if proposed_stop is not None and proposed_stop != previous_stop:
                pos.stop_loss = proposed_stop
                db.add(DecisionAudit(
                    symbol=pos.symbol,
                    signal_id=entry_features.get("signal_id"),
                    model_version=entry_features.get("model_version") or "UNFITTED",
                    dataset_version=f"market_snapshot:{to_utc_iso(latest_snapshot.source_timestamp)}",
                    risk_policy_version=paper_broker.policy.policy_id,
                    decision="TRAILING_STOP_UPDATED",
                    decision_reason_fa=(
                        f"حد ضرر بر اساس {current_r:.2f}R از {previous_stop or 0:,.0f} "
                        f"به {proposed_stop:,.0f} ریال منتقل شد."
                    ),
                    opportunity_score=0.0,
                    p_profit=0.0,
                    as_of=latest_snapshot.source_timestamp,
                ))

            # Time stop counts exchange sessions, not wall-clock hours.
            if not exit_reason and pos.opened_at and pos.expected_days_to_target > 0:
                opened_dt = pos.opened_at if pos.opened_at.tzinfo is not None else pos.opened_at.replace(tzinfo=timezone.utc)
                holding_sessions = len({
                    bar.trading_date for bar in bars
                    if opened_dt.date() < bar.trading_date <= latest_snapshot.source_timestamp.date()
                })
                if holding_sessions >= pos.expected_days_to_target:
                    exit_reason = "time_stop"

            if exit_reason:
                exits += self._submit_exit(
                    db, portfolio, pos, current_price, exit_reason, latest_snapshot.source_timestamp
                )

        return exits

    def _submit_exit(
        self, db: Session, portfolio: Portfolio, pos: Position,
        exit_price: float, reason: str, source_timestamp: datetime,
    ) -> int:
        """Queue an exit; never mutate cash, position, or P&L at decision time."""
        reason_code = {
            "stop_hit": "STOP_LOSS",
            "target_hit": "TARGET_1",
            "time_stop": "TIME_STOP",
            "indicator_deterioration": "SIGNAL_INVALIDATED",
            "manual": "MANUAL_EXIT",
        }.get(reason, "MANUAL_EXIT")
        order, message = paper_broker.create_exit_order(
            portfolio, pos.id, exit_price, ratio=1.0, reason_code=reason_code
        )
        if order is None:
            logger.warning("Exit submission blocked for %s: %s", pos.symbol, message)
            return 0
        trade_log = db.query(PaperTradeLog).filter(
            PaperTradeLog.portfolio_id == portfolio.id,
            PaperTradeLog.symbol == pos.symbol,
            PaperTradeLog.is_closed == False,
        ).first()
        entry_features = dict(trade_log.features_at_entry or {}) if trade_log else {}
        db.add_all([
            order,
            DecisionAudit(
                symbol=pos.symbol, signal_id=None, decision=f"{reason_code}_SUBMITTED",
                model_version=entry_features.get("model_version") or "UNFITTED",
                dataset_version=f"market_snapshot:{to_utc_iso(source_timestamp)}",
                risk_policy_version=paper_broker.policy.policy_id,
                decision_reason_fa=f"{_exit_reason_fa(reason)}؛ اجرا فقط روی snapshot رسمی بعدی؛ order={order.id}",
                opportunity_score=0.0, p_profit=0.0, as_of=source_timestamp,
            ),
        ])
        logger.info("AUTO EXIT SUBMITTED: %s - %s", pos.symbol, message)
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
