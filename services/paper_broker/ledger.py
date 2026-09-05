"""Paper Trading Ledger, Institutional Risk Gatekeeper, and Execution Simulator."""
from decimal import Decimal
from datetime import datetime, date, timezone
import uuid
from typing import Tuple, Optional, Dict, Any

from packages.domain.models import (
    Portfolio, Position, BrokerOrder, PublishedSignal, PaperCampaign,
    CashLedger, OrderFill, DecisionAudit, Instrument, MarketSnapshot, PaperTradeLog,
    ClosedTradeHistory, TradeExecutionTimeline, EODBar,
)
from packages.domain.risk_policy import ACTIVE_RISK_POLICY, RiskPolicy
from packages.market_rules.fees import (
    calculate_net_return, calculate_trade_fees, TSE_EQUITY_FEES,
)
from packages.shared.money import MoneyIRR, tomans_to_irr
from packages.shared.metrics import compute_r_multiples
from packages.shared.datetime_utils import now_utc, to_utc_iso
from packages.shared.logger import logger
from packages.shared.config import settings
from services.collector.trusted_queries import (
    latest_trusted_market_snapshot, trusted_market_snapshot_query, trusted_eod_query,
)
from services.paper_broker.sizing import position_sizing_solver, PreTradeRiskTicket
from services.paper_broker.execution import execution_simulator, ExecutionBar
from services.paper_broker.accounting import accounting_reconciler

# Hard Security Guard: Live trading is strictly disabled in Backend
LIVE_TRADING_ENABLED = False


class PaperBrokerService:
    """
    Simulated Paper Broker Ledger & Institutional Risk Gatekeeper.
    Enforces Point-in-Time discipline, Next-Bar Execution, queue delays, and strict double-entry cash accounting.
    """

    def __init__(self, policy: RiskPolicy = ACTIVE_RISK_POLICY):
        self.policy = policy
        self.solver = position_sizing_solver
        self.simulator = execution_simulator
        self.reconciler = accounting_reconciler

    @staticmethod
    def _campaign_allows_entry(db, portfolio: Portfolio) -> bool:
        campaigns = db.query(PaperCampaign).filter(
            PaperCampaign.portfolio_id == portfolio.id,
            PaperCampaign.status.in_(["READY_BLOCKED_DATA", "READY", "RUNNING"]),
        ).all()
        if len(campaigns) != 1:
            return False
        campaign = campaigns[0]
        starts_at = campaign.starts_at
        ends_at = campaign.ends_at
        if starts_at.tzinfo is None:
            starts_at = starts_at.replace(tzinfo=timezone.utc)
        if ends_at.tzinfo is None:
            ends_at = ends_at.replace(tzinfo=timezone.utc)
        return starts_at <= now_utc() <= ends_at

    def generate_pre_trade_ticket(
        self,
        portfolio: Portfolio,
        signal: PublishedSignal,
        current_market_price: float,
        adtv_20d_rials: float = 50_000_000_000.0,
    ) -> PreTradeRiskTicket:
        """Generates pre-trade risk ticket with complete position sizing analysis."""
        return self.solver.solve(
            portfolio=portfolio,
            signal=signal,
            current_market_price=current_market_price,
            adtv_20d_rials=adtv_20d_rials,
            sector_name=getattr(signal, "sector", None),
        )

    def calculate_position_size(
        self,
        portfolio: Portfolio,
        entry_price: float,
        stop_price: float,
        opportunity_score: float = 75.0,
        adtv_20d_rials: float = 50_000_000_000.0,
        sector_current_exposure_rials: float = 0.0,
    ) -> int:
        """Helper to calculate position quantity using central multi-constraint solver."""
        sig = PublishedSignal(
            id="temp_sig",
            instrument_id="temp_inst",
            symbol="TEMP",
            name_fa="موقت",
            as_of=now_utc(),
            opportunity_score=opportunity_score,
            p_profit=0.70,
            confidence=80.0,
            signal_strength=80.0,
            entry_zone={"low": entry_price, "high": entry_price * 1.01},
            invalidation={"price": stop_price},
            exit_plan={"targets": [entry_price * 1.08]},
            strategy_votes=[],
            top_reasons_fa=[],
            risk_flags_fa=[],
        )
        ticket = self.solver.solve(portfolio, sig, entry_price, adtv_20d_rials)
        return ticket["recommended_quantity"]

    def create_order_from_signal(
        self,
        portfolio: Portfolio,
        signal: PublishedSignal,
        current_market_price: float,
        quantity: int | None = None,
    ) -> Tuple[Optional[BrokerOrder], str]:
        """Creates and validates a paper order from an approved opportunity."""
        if LIVE_TRADING_ENABLED:
            return None, "خطای امنیتی: اتصال به معاملات زنده مسدود است (Paper Only)."

        if portfolio.kill_switch_active:
            return None, "کلید قطع اضطراری (Kill-Switch) فعال است؛ ثبت سفارش مجاز نیست."

        ticket = self.generate_pre_trade_ticket(portfolio, signal, current_market_price)
        if ticket["decision"] not in ["APPROVED"]:
            return None, f"سفارش توسط گیت مدیریت ریسک رد شد: {ticket['decision_reason_fa']}"

        recommended_quantity = int(ticket["recommended_quantity"])
        if quantity is not None and quantity > recommended_quantity:
            return None, (
                f"حجم درخواستی {quantity:,} از سقف محاسبه‌شده مدیریت ریسک "
                f"({recommended_quantity:,}) بیشتر است."
            )
        exec_quantity = recommended_quantity if quantity is None else quantity
        if exec_quantity <= 0:
            return None, "حجم محاسبه شده کمتر از حداقل مجاز است."

        order_cost = exec_quantity * current_market_price * (1.0 + float(TSE_EQUITY_FEES.buy_fee_rate))
        reserved_cost = sum(
            o.quantity * o.price * (1.0 + float(TSE_EQUITY_FEES.buy_fee_rate))
            for o in portfolio.orders
            if o.side == "BUY" and o.status in {"CREATED", "VALIDATED", "SUBMITTED", "ACKNOWLEDGED"}
        )
        if order_cost > max(0.0, portfolio.cash - reserved_cost):
            return None, "موجودی نقد برای پوشش هزینه سفارش و کارمزد کافی نیست."

        now = now_utc()
        order_id = f"ord_{uuid.uuid4().hex}"

        order = BrokerOrder(
            id=order_id,
            portfolio_id=portfolio.id,
            signal_id=signal.id,
            symbol=signal.symbol,
            side="BUY",
            order_type="LIMIT",
            price=current_market_price,
            quantity=exec_quantity,
            filled_quantity=0,
            status="SUBMITTED",
            created_at=now,
            updated_at=now,
        )

        return order, (
            f"سفارش کاغذی {exec_quantity:,} سهم {signal.symbol} ثبت شد؛ "
            "تا نخستین snapshot معتبر بعدی هیچ سهم یا وجهی جابه‌جا نمی‌شود."
        )

    def process_pending_orders(
        self,
        db,
        portfolio: Portfolio,
        *,
        allowed_sides: set[str] | None = None,
    ) -> dict:
        """Fill pending orders once per later official snapshot under a row lock."""
        processed = 0
        filled = 0
        messages: list[str] = []
        order_query = db.query(BrokerOrder).filter(
                BrokerOrder.portfolio_id == portfolio.id,
                BrokerOrder.status.in_(["SUBMITTED", "PARTIALLY_FILLED"]),
            )
        if allowed_sides is not None:
            normalized_sides = {side.upper() for side in allowed_sides}
            if not normalized_sides:
                return {"processed": 0, "filled": 0, "messages": []}
            order_query = order_query.filter(BrokerOrder.side.in_(sorted(normalized_sides)))
        orders = (
            order_query
            .order_by(BrokerOrder.created_at.asc())
            .with_for_update(skip_locked=True)
            .all()
        )
        for order in orders:
            if order.filled_quantity >= order.quantity:
                order.status = "FILLED"
                continue
            approved_signal = None
            if order.side == "BUY" and not self._campaign_allows_entry(db, portfolio):
                order.status = "REJECTED"
                order.updated_at = now_utc()
                messages.append(f"{order.symbol}: پنجره اجرای کمپین کاغذی بسته یا نامعتبر است")
                continue
            if order.side == "BUY" and portfolio.kill_switch_active:
                order.status = "REJECTED"
                order.updated_at = now_utc()
                messages.append(f"{order.symbol}: کلید قطع ریسک، ورود یا افزایش حجم را مسدود کرده است")
                continue
            if order.side == "BUY" and not (
                order.signal_id and order.signal_id.startswith("position:")
            ):
                approved_signal = (
                    db.query(PublishedSignal)
                    .filter(PublishedSignal.id == order.signal_id)
                    .first()
                )
                expires_at = approved_signal.expires_at if approved_signal else None
                if expires_at is not None and expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                if (
                    approved_signal is None
                    or approved_signal.actionable is not True
                    or expires_at is None
                    or expires_at <= now_utc()
                ):
                    order.status = "REJECTED"
                    order.updated_at = now_utc()
                    messages.append(
                        f"{order.symbol}: سیگنال ورود دیگر معتبر، قابل اقدام یا منقضی‌نشده نیست"
                    )
                    continue
            inst = db.query(Instrument).filter(Instrument.ticker == order.symbol).first()
            if not inst:
                order.status = "REJECTED"
                messages.append(f"{order.symbol}: نماد رسمی یافت نشد")
                continue
            last_fill = (
                db.query(OrderFill)
                .filter(OrderFill.order_id == order.id)
                .order_by(OrderFill.executed_at.desc())
                .first()
            )
            after_timestamp = max(
                value for value in (
                    order.created_at,
                    last_fill.executed_at if last_fill else None,
                    order.last_evaluated_snapshot_at,
                ) if value is not None
            )
            snapshot = latest_trusted_market_snapshot(
                db, inst.id, after=after_timestamp,
                max_age_seconds=settings.quality.critical_market_stale_seconds,
            )
            if snapshot is None:
                continue
            # Advance the observation cursor even when this snapshot does not
            # cross or has no incremental volume. Later valid snapshots must
            # remain reachable without re-evaluating this one forever.
            order.last_evaluated_snapshot_at = snapshot.source_timestamp
            previous_snapshot = (
                trusted_market_snapshot_query(db, inst.id)
                .filter(MarketSnapshot.source_timestamp <= after_timestamp)
                .order_by(MarketSnapshot.source_timestamp.desc())
                .first()
            )
            # Session high/low and volume are cumulative and may include events
            # before the order.  A fill requires a later observed last price and
            # strictly incremental volume from a prior trusted snapshot.
            if (
                previous_snapshot is None
                or previous_snapshot.source_timestamp.date() != snapshot.source_timestamp.date()
            ):
                continue
            incremental_volume = max(0, snapshot.volume - previous_snapshot.volume)
            if incremental_volume <= 0:
                continue
            processed += 1
            bar: ExecutionBar = {
                "trading_date": snapshot.source_timestamp.date().isoformat(),
                "open": snapshot.last_price,
                "high": snapshot.last_price,
                "low": snapshot.last_price,
                "close": snapshot.last_price,
                "volume": incremental_volume,
                "value": incremental_volume * snapshot.last_price,
                "allowed_min": snapshot.allowed_min,
                "allowed_max": snapshot.allowed_max,
            }
            fill, message = self.simulator.simulate_order_fill(order, bar)
            messages.append(f"{order.symbol}: {message}")
            if fill is None:
                continue
            # The execution clock is the provider snapshot time, not local processing time.
            fill.executed_at = snapshot.source_timestamp
            db.add(fill)

            if order.side == "BUY":
                if fill.net_value_rials > portfolio.cash:
                    order.status = "REJECTED"
                    db.delete(fill)
                    messages.append(f"{order.symbol}: نقدینگی در زمان اجرا کافی نبود")
                    continue
                signal = None
                position = None
                if order.signal_id and order.signal_id.startswith("position:"):
                    position = db.query(Position).filter(Position.id == order.signal_id.split(":", 1)[1], Position.is_open == True).first()
                else:
                    signal = approved_signal
                    position = db.query(Position).filter(
                        Position.portfolio_id == portfolio.id,
                        Position.symbol == order.symbol,
                        Position.is_open == True,
                    ).first()
                if signal is None and position is None:
                    order.status = "REJECTED"
                    db.delete(fill)
                    messages.append(f"{order.symbol}: سیگنال یا موقعیت مرجع یافت نشد")
                    continue

                entry_nav = portfolio.cash + sum(
                    item.quantity * item.current_price for item in portfolio.positions if item.is_open
                )
                rr_ratio = 0.0
                portfolio.cash -= fill.net_value_rials
                portfolio.updated_at = snapshot.source_timestamp
                if position is None:
                    stop_price = signal.invalidation.get("price")
                    targets = signal.exit_plan.get("targets") or []
                    target_price = targets[0] if targets else None
                    risk_per_share = max(0.0, fill.fill_price - stop_price) if stop_price is not None else 0.0
                    reward_per_share = max(0.0, target_price - fill.fill_price) if target_price is not None else 0.0
                    risk_pct = (risk_per_share * fill.quantity / max(1.0, entry_nav)) * 100.0
                    rr_ratio = reward_per_share / risk_per_share if risk_per_share > 0 else 0.0
                    position = Position(
                        id=f"pos_{uuid.uuid4().hex}", portfolio_id=portfolio.id, symbol=order.symbol,
                        quantity=fill.quantity, average_entry_price=fill.fill_price, current_price=fill.fill_price,
                        unrealized_pnl=-fill.fees_rials - fill.tax_rials,
                        stop_loss=stop_price,
                        target_price=target_price,
                        total_invested_rials=fill.net_value_rials,
                        risk_pct=risk_pct,
                        risk_reward_ratio=f"1:{rr_ratio:.2f}" if rr_ratio > 0 else "UNKNOWN",
                        expected_days_to_target=int(signal.exit_plan.get("time_stop_sessions") or 0),
                        market_regime=signal.regime or "unknown",
                        decision_method="Independent-family confluence + fundamental gate",
                        entry_reason_fa=" | ".join(signal.top_reasons_fa),
                        risk_flags_fa=signal.risk_flags_fa or [], is_open=True,
                        opened_at=fill.executed_at,
                    )
                    db.add(position)
                else:
                    old_quantity = position.quantity
                    new_quantity = old_quantity + fill.quantity
                    position.average_entry_price = (
                        (position.average_entry_price * old_quantity) + (fill.fill_price * fill.quantity)
                    ) / new_quantity
                    position.quantity = new_quantity
                    position.current_price = fill.fill_price
                    position.total_invested_rials += fill.net_value_rials
                    position.unrealized_pnl = (fill.fill_price - position.average_entry_price) * new_quantity
                    if order.order_type == "SCALE_IN":
                        flags = list(position.risk_flags_fa or [])
                        if "scaled_in" not in flags:
                            flags.append("scaled_in")
                        position.risk_flags_fa = flags

                trade_log = db.query(PaperTradeLog).filter(
                    PaperTradeLog.portfolio_id == portfolio.id,
                    PaperTradeLog.symbol == order.symbol,
                    PaperTradeLog.is_closed == False,
                ).first()
                if trade_log is None:
                    trade_log = PaperTradeLog(
                        portfolio_id=portfolio.id, symbol=order.symbol, side="BUY",
                        entry_price=position.average_entry_price, quantity=position.quantity,
                        total_invested_rials=position.total_invested_rials, entry_at=fill.executed_at,
                        decision_method=position.decision_method,
                        expected_days_to_target=position.expected_days_to_target,
                        market_regime=position.market_regime,
                        risk_pct=position.risk_pct,
                        risk_reward_ratio=rr_ratio if signal else 0.0,
                        features_at_entry={
                            "entry_order_id": order.id,
                            "entry_snapshot_at": to_utc_iso(snapshot.source_timestamp),
                            "signal_id": signal.id if signal else None,
                            "model_version": (signal.model_version or signal.calibration_version or "UNFITTED") if signal else "UNFITTED",
                            "strategy_version": signal.strategy_version if signal else "UNVERSIONED",
                            "calibration_version": signal.calibration_version if signal else None,
                            "decision_components": signal.decision_components if signal else {},
                            "initial_stop": position.stop_loss,
                            "targets": (signal.exit_plan.get("targets") or []) if signal else [],
                            "portfolio_nav_at_entry": entry_nav,
                            "position_weight_at_entry": fill.net_value_rials / max(1.0, entry_nav),
                        },
                        strategy_votes_at_entry=[
                            vote if isinstance(vote, dict) else {"strategy": str(vote)}
                            for vote in ((signal.strategy_votes if signal else []) or [])
                        ],
                        reason_fa=position.entry_reason_fa, is_closed=False,
                    )
                    db.add(trade_log)
                else:
                    trade_log.entry_price = position.average_entry_price
                    trade_log.quantity = position.quantity
                    trade_log.total_invested_rials = position.total_invested_rials
                    entry_features = dict(trade_log.features_at_entry or {})
                    scale_orders = list(entry_features.get("scale_in_order_ids") or [])
                    if order.order_type == "SCALE_IN" and order.id not in scale_orders:
                        scale_orders.append(order.id)
                    entry_features["scale_in_order_ids"] = scale_orders
                    trade_log.features_at_entry = entry_features

                audit_features = dict(trade_log.features_at_entry or {})
                audit_signal_id = signal.id if signal else audit_features.get("signal_id")
                audit_model_version = (
                    (signal.model_version or signal.calibration_version) if signal else audit_features.get("model_version")
                ) or "UNFITTED"
                decision = "SCALE_IN_FILLED_NEXT_SNAPSHOT" if order.order_type == "SCALE_IN" else "ENTRY_FILLED_NEXT_SNAPSHOT"
                reason = "افزایش حجم" if order.order_type == "SCALE_IN" else "ورود"
                db.add_all([
                    CashLedger(
                        portfolio_id=portfolio.id, transaction_type="BUY_FILL",
                        amount_rials=-fill.net_value_rials, settled_cash=portfolio.cash,
                        available_cash=portfolio.cash, fees_due=fill.fees_rials + fill.tax_rials,
                        reference_id=order.id, description_fa=f"اجرای {reason} کاغذی {order.symbol} روی snapshot رسمی بعدی",
                    ),
                    DecisionAudit(
                        symbol=order.symbol, signal_id=audit_signal_id,
                        model_version=audit_model_version,
                        dataset_version=f"market_snapshot:{to_utc_iso(snapshot.source_timestamp)}",
                        risk_policy_version=self.policy.policy_id,
                        decision=decision,
                        decision_reason_fa=f"{reason} فقط روی snapshot رسمی بعد از زمان ثبت سفارش اجرا شد؛ order={order.id}",
                        opportunity_score=signal.opportunity_score if signal else 0.0,
                        p_profit=signal.p_profit if signal else 0.0, as_of=fill.executed_at,
                    ),
                ])
            elif order.side == "SELL":
                position_id = order.signal_id.split(":", 1)[1] if order.signal_id and order.signal_id.startswith("position:") else None
                position = db.query(Position).filter(Position.id == position_id, Position.is_open == True).first() if position_id else None
                if position is None or fill.quantity > position.quantity:
                    order.status = "REJECTED"
                    db.delete(fill)
                    messages.append(f"{order.symbol}: موقعیت یا حجم قابل فروش معتبر نیست")
                    continue
                quantity_before = position.quantity
                allocated_cost = position.total_invested_rials * (fill.quantity / quantity_before)
                realized_pnl = fill.net_value_rials - allocated_cost
                portfolio.cash += fill.net_value_rials
                portfolio.realized_pnl += realized_pnl
                portfolio.updated_at = snapshot.source_timestamp
                position.quantity -= fill.quantity
                position.total_invested_rials = max(0.0, position.total_invested_rials - allocated_cost)
                position.current_price = fill.fill_price
                position.unrealized_pnl = (fill.fill_price - position.average_entry_price) * position.quantity
                if order.order_type == "TRIM":
                    flags = list(position.risk_flags_fa or [])
                    if "trimmed" not in flags:
                        flags.append("trimmed")
                    position.risk_flags_fa = flags
                if position.quantity == 0:
                    position.is_open = False
                    position.unrealized_pnl = 0.0

                trade_log = db.query(PaperTradeLog).filter(
                    PaperTradeLog.portfolio_id == portfolio.id,
                    PaperTradeLog.symbol == order.symbol,
                    PaperTradeLog.is_closed == False,
                ).first()
                if trade_log:
                    sold_before = max(0, trade_log.quantity - quantity_before)
                    sold_after = sold_before + fill.quantity
                    trade_log.exit_price = (
                        ((trade_log.exit_price or 0.0) * sold_before) + (fill.fill_price * fill.quantity)
                    ) / max(1, sold_after)
                    trade_log.gross_pnl += (fill.fill_price - trade_log.entry_price) * fill.quantity
                    trade_log.net_pnl += realized_pnl
                    trade_log.return_pct = (trade_log.net_pnl / max(1.0, trade_log.total_invested_rials)) * 100.0
                    exit_reason_by_order = {
                        "CLOSE": "MANUAL_EXIT", "STOP_EXIT": "STOP_LOSS",
                        "TARGET_EXIT": "TARGET_1", "TIME_EXIT": "TIME_STOP",
                        "SIGNAL_EXIT": "SIGNAL_INVALIDATED", "KILL_EXIT": "KILL_SWITCH",
                        "TRIM": "RISK_REDUCTION",
                    }
                    trade_log.exit_reason = exit_reason_by_order.get(order.order_type, "OTHER")
                    if not position.is_open:
                        trade_log.exit_at = fill.executed_at
                        trade_log.holding_hours = max(0.0, (fill.executed_at - trade_log.entry_at).total_seconds() / 3600.0)
                        trade_log.holding_days = trade_log.holding_hours / 24.0
                        trade_log.lesson_fa = f"خروج با بازده خالص {trade_log.return_pct:+.2f}٪ روی snapshot رسمی انجام شد."
                        trade_log.features_at_exit = {
                            "exit_order_id": order.id,
                            "exit_snapshot_at": to_utc_iso(snapshot.source_timestamp),
                            "exit_fill_price": fill.fill_price,
                            "exit_reason": trade_log.exit_reason,
                        }
                        trade_log.is_closed = True

                entry_features = dict(trade_log.features_at_entry or {}) if trade_log else {}
                db.add_all([
                    CashLedger(
                        portfolio_id=portfolio.id, transaction_type="SELL_FILL",
                        amount_rials=fill.net_value_rials, settled_cash=portfolio.cash,
                        available_cash=portfolio.cash, fees_due=fill.fees_rials + fill.tax_rials,
                        reference_id=order.id, description_fa=f"اجرای فروش کاغذی {order.symbol} روی snapshot رسمی بعدی",
                    ),
                    DecisionAudit(
                        symbol=order.symbol, signal_id=None,
                        model_version=entry_features.get("model_version") or "UNFITTED",
                        dataset_version=f"market_snapshot:{to_utc_iso(snapshot.source_timestamp)}",
                        risk_policy_version=self.policy.policy_id,
                        decision="TRIM_FILLED_NEXT_SNAPSHOT" if order.order_type == "TRIM" else "EXIT_FILLED_NEXT_SNAPSHOT",
                        decision_reason_fa=f"فروش فقط روی snapshot رسمی بعد از ثبت سفارش اجرا شد؛ order={order.id}",
                        opportunity_score=0.0, p_profit=0.0, as_of=fill.executed_at,
                    ),
                ])
                if not position.is_open and trade_log:
                    self._record_closed_trade(db, portfolio, position, trade_log, fill)
            else:
                order.status = "REJECTED"
                db.delete(fill)
                continue
            filled += 1
        return {"processed": processed, "filled": filled, "messages": messages}

    def _record_closed_trade(self, db, portfolio: Portfolio, position: Position, trade_log: PaperTradeLog, final_fill: OrderFill) -> None:
        """Create one immutable close record after the final sell fill."""
        if db.query(ClosedTradeHistory).filter(ClosedTradeHistory.position_id == position.id).first():
            return
        inst = db.query(Instrument).filter(Instrument.ticker == position.symbol).first()
        entry_features = dict(trade_log.features_at_entry or {})
        entry_order_id = entry_features.get("entry_order_id")
        entry_order = db.query(BrokerOrder).filter(BrokerOrder.id == entry_order_id).first() if entry_order_id else None
        signal_id = entry_features.get("signal_id") or (entry_order.signal_id if entry_order else None)
        signal = db.query(PublishedSignal).filter(PublishedSignal.id == signal_id).first() if signal_id else None
        entry_decision = (
            db.query(DecisionAudit)
            .filter(DecisionAudit.signal_id == signal_id, DecisionAudit.as_of <= trade_log.entry_at)
            .order_by(DecisionAudit.as_of.desc())
            .first()
        ) if signal_id else None
        gross_buy = trade_log.entry_price * trade_log.quantity
        gross_sell = gross_buy + trade_log.gross_pnl
        entry_fees = max(0.0, trade_log.total_invested_rials - gross_buy)
        sell_order_ids = [row[0] for row in db.query(BrokerOrder.id).filter(
            BrokerOrder.portfolio_id == portfolio.id, BrokerOrder.symbol == position.symbol,
            BrokerOrder.side == "SELL", BrokerOrder.created_at >= trade_log.entry_at,
        ).all()]
        sell_fills = db.query(OrderFill).filter(OrderFill.order_id.in_(sell_order_ids)).all() if sell_order_ids else []
        exit_fees = sum(item.fees_rials for item in sell_fills)
        tax = sum(item.tax_rials for item in sell_fills)
        slippage = sum(item.slippage_rials for item in sell_fills)
        initial_stop = entry_features.get("initial_stop")
        risk_unit = max(0.0, trade_log.entry_price - initial_stop) if initial_stop is not None else 0.0
        realized_r = (
            (trade_log.exit_price - trade_log.entry_price) / risk_unit
            if trade_log.exit_price is not None and risk_unit > 0
            else 0.0
        )
        excursion_rows = (
            trusted_market_snapshot_query(db, inst.id)
            .filter(
                MarketSnapshot.source_timestamp >= trade_log.entry_at,
                MarketSnapshot.source_timestamp <= final_fill.executed_at,
            )
            .all()
        ) if inst else []
        # On the entry date session extrema include pre-entry prints; only the
        # observed last price is valid for excursion accounting that day.
        max_high = max((
            row.last_price if row.source_timestamp.date() == trade_log.entry_at.date() else row.high_price
            for row in excursion_rows
        ), default=trade_log.entry_price)
        min_low = min((
            row.last_price if row.source_timestamp.date() == trade_log.entry_at.date() else row.low_price
            for row in excursion_rows
        ), default=trade_log.entry_price)
        mfe_pct = max(0.0, (max_high - trade_log.entry_price) / max(1.0, trade_log.entry_price) * 100.0)
        mae_pct = max(0.0, (trade_log.entry_price - min_low) / max(1.0, trade_log.entry_price) * 100.0)
        portfolio_nav_at_exit = portfolio.cash + sum(
            item.quantity * item.current_price for item in portfolio.positions if item.is_open
        )
        targets = list(entry_features.get("targets") or [])
        qualifying_families = (
            entry_features.get("decision_components", {})
            .get("technical_gate", {})
            .get("qualifying_families", [])
        )
        holding_sessions = 0
        if inst:
            holding_sessions = trusted_eod_query(db, inst.id).with_entities(EODBar.trading_date).filter(
                EODBar.trading_date >= trade_log.entry_at.date(),
                EODBar.trading_date <= final_fill.executed_at.date(),
            ).distinct().count()
        closed = ClosedTradeHistory(
            portfolio_id=portfolio.id, position_id=position.id, instrument_id=inst.id if inst else None,
            symbol=position.symbol, company_name=inst.name_fa if inst else position.symbol,
            sector=inst.sector.name_fa if inst and inst.sector else "نامشخص",
            strategy_id="+".join(qualifying_families) if qualifying_families else "multi_family_confluence",
            strategy_name_fa=position.entry_reason_fa or "همگرایی چندخانواده‌ای",
            strategy_version=entry_features.get("strategy_version") or (signal.strategy_version if signal else "UNVERSIONED"),
            model_version=entry_features.get("model_version") or "UNFITTED",
            risk_policy_version=self.policy.policy_id,
            market_rules_version="TSE-RULES-CONFIGURED",
            dataset_version=f"market_snapshot:{entry_features.get('entry_snapshot_at') or to_utc_iso(trade_log.entry_at)}",
            signal_id=signal_id, decision_id=entry_decision.id if entry_decision else None,
            decision_method=position.decision_method,
            opened_at=trade_log.entry_at, closed_at=final_fill.executed_at,
            holding_sessions=holding_sessions, holding_duration_hours=trade_log.holding_hours,
            planned_entry=trade_log.entry_price, avg_entry_price=trade_log.entry_price,
            avg_exit_price=trade_log.exit_price or final_fill.fill_price, total_quantity=trade_log.quantity,
            gross_buy_value=gross_buy, gross_sell_value=gross_sell, entry_fees=entry_fees,
            exit_fees=exit_fees, tax=tax, slippage_cost=slippage,
            total_cost=entry_fees + exit_fees + tax, gross_pnl=trade_log.gross_pnl,
            net_pnl=trade_log.net_pnl, net_return_pct=trade_log.return_pct,
            initial_risk_amount=risk_unit * trade_log.quantity,
            initial_risk_pct_nav=(risk_unit * trade_log.quantity / max(1.0, float(entry_features.get("portfolio_nav_at_entry") or 0.0))) * 100.0,
            realized_R=realized_r, MFE=mfe_pct, MAE=mae_pct,
            initial_stop=float(initial_stop or 0.0),
            final_stop=float(position.stop_loss or 0.0),
            target1=float(targets[0]) if len(targets) > 0 else 0.0,
            target2=float(targets[1]) if len(targets) > 1 else 0.0,
            exit_reason=trade_log.exit_reason, exit_reason_detail="تکمیل فروش روی snapshot رسمی بعدی",
            market_regime_at_entry=position.market_regime, market_regime_at_exit=position.market_regime,
            portfolio_nav_at_entry=float(entry_features.get("portfolio_nav_at_entry") or 0.0),
            portfolio_nav_at_exit=portfolio_nav_at_exit,
            position_weight_at_entry=float(entry_features.get("position_weight_at_entry") or 0.0),
            outcome_status="WIN" if trade_log.net_pnl > 0 else ("LOSS" if trade_log.net_pnl < 0 else "BREAKEVEN"),
            reason_fa=position.entry_reason_fa,
            lesson_fa=f"بازده خالص معامله {trade_log.return_pct:+.2f}٪؛ خروج با قیمت ساختگی انجام نشد.",
        )
        db.add(closed)
        db.flush()
        timeline = [TradeExecutionTimeline(
            trade_id=closed.id, event_type="ENTRY_FILL", timestamp=trade_log.entry_at,
            price=trade_log.entry_price, quantity=trade_log.quantity, portion_pct=100.0,
            fees=entry_fees, notes_fa=f"میانگین اجرای ورود؛ order={entry_order_id or 'unlinked'}",
        )]
        order_window_start = entry_order.created_at if entry_order else trade_log.entry_at
        lifecycle_orders = db.query(BrokerOrder).filter(
            BrokerOrder.portfolio_id == portfolio.id,
            BrokerOrder.symbol == position.symbol,
            BrokerOrder.created_at >= order_window_start,
            BrokerOrder.created_at <= final_fill.executed_at,
        ).all()
        for lifecycle_order in lifecycle_orders:
            lifecycle_fills = db.query(OrderFill).filter(
                OrderFill.order_id == lifecycle_order.id,
                OrderFill.executed_at >= trade_log.entry_at,
                OrderFill.executed_at <= final_fill.executed_at,
            ).order_by(OrderFill.executed_at.asc()).all()
            for lifecycle_fill in lifecycle_fills:
                if lifecycle_order.id == entry_order_id:
                    continue
                if lifecycle_order.side == "BUY":
                    event_type = "SCALE_IN_FILL"
                    note = "افزایش حجم اجراشده روی snapshot رسمی"
                elif lifecycle_fill.id == final_fill.id:
                    event_type = "FINAL_EXIT_FILL"
                    note = "تکمیل خروج روی snapshot رسمی"
                else:
                    event_type = "TRIM_FILL"
                    note = "کاهش حجم اجراشده روی snapshot رسمی"
                timeline.append(TradeExecutionTimeline(
                    trade_id=closed.id,
                    event_type=event_type,
                    timestamp=lifecycle_fill.executed_at,
                    price=lifecycle_fill.fill_price,
                    quantity=lifecycle_fill.quantity,
                    portion_pct=(lifecycle_fill.quantity / max(1, trade_log.quantity)) * 100.0,
                    fees=lifecycle_fill.fees_rials + lifecycle_fill.tax_rials,
                    notes_fa=f"{note}؛ order={lifecycle_order.id}",
                ))
        if not any(item.event_type == "FINAL_EXIT_FILL" for item in timeline):
            timeline.append(TradeExecutionTimeline(
                trade_id=closed.id, event_type="FINAL_EXIT_FILL", timestamp=final_fill.executed_at,
                price=trade_log.exit_price or final_fill.fill_price, quantity=final_fill.quantity,
                portion_pct=(final_fill.quantity / max(1, trade_log.quantity)) * 100.0,
                fees=final_fill.fees_rials + final_fill.tax_rials,
                notes_fa="تکمیل خروج روی snapshot رسمی؛ order linkage در رکورد قدیمی موجود نبود",
            ))
        db.add_all(timeline)

    def scale_in_position(self, portfolio: Portfolio, position_id: str, current_price: float) -> Tuple[Optional[BrokerOrder], str]:
        """
        افزایش پله‌ای حجم سهم برنده (Stage 2/3).
        قاعده سخت: میانگین کم کردن در ضرر (Averaging Down) اکیداً ممنوع است.
        """
        if portfolio.kill_switch_active:
            return None, "کلید قطع اضطراری فعال است؛ افزایش حجم مجاز نیست."
        pos = next((p for p in portfolio.positions if p.id == position_id and p.is_open), None)
        if not pos:
            return None, "موقعیت باز یافت نشد."

        # Hard Rule: No averaging down if losing
        if current_price < pos.average_entry_price:
            return None, "افزایش حجم در موقعیت‌های زیان‌ده (Averaging Down) طبق سیاست مدیریت ریسک ممنوع است."

        nav = portfolio.cash + sum(p.quantity * p.current_price for p in portfolio.positions if p.is_open)
        max_position_value = nav * (self.policy.portfolio_limits.normal_max_position_weight_pct / 100.0)
        remaining_cap = max(0.0, max_position_value - (pos.quantity * current_price))
        add_qty = min(max(1, int(pos.quantity * 0.35)), int(remaining_cap / current_price))
        if add_qty <= 0:
            return None, "موقعیت به سقف وزن مجاز مدیریت ریسک رسیده است."
        cost = add_qty * current_price * (1.0 + float(TSE_EQUITY_FEES.buy_fee_rate))
        reserved_cost = sum(
            max(0, o.quantity - int(o.filled_quantity or 0)) * o.price * (1.0 + float(TSE_EQUITY_FEES.buy_fee_rate))
            for o in portfolio.orders
            if o.side == "BUY" and o.status in {"SUBMITTED", "PARTIALLY_FILLED"}
        )
        if cost > max(0.0, portfolio.cash - reserved_cost):
            return None, "نقدینگی در دسترس برای افزایش پله‌ای کافی نیست."

        now = now_utc()
        order = BrokerOrder(
            id=f"ord_{uuid.uuid4().hex}",
            portfolio_id=portfolio.id,
            signal_id=f"position:{pos.id}",
            symbol=pos.symbol,
            side="BUY",
            order_type="SCALE_IN",
            price=current_price,
            quantity=add_qty,
            filled_quantity=0,
            status="SUBMITTED",
            created_at=now,
            updated_at=now,
        )

        return order, f"سفارش افزایش {add_qty:,} سهم {pos.symbol} ثبت شد؛ حجم و نقدینگی فقط پس از snapshot رسمی بعدی تغییر می‌کند."

    def create_exit_order(
        self,
        portfolio: Portfolio,
        position_id: str,
        current_price: float,
        ratio: float = 1.0,
        reason_code: str = "MANUAL_EXIT",
    ) -> Tuple[Optional[BrokerOrder], str]:
        """Submit a partial/full exit; do not realize P&L until a later official snapshot."""
        pos = next((p for p in portfolio.positions if p.id == position_id and p.is_open), None)
        if not pos:
            return None, "موقعیت باز یافت نشد."
        pending_quantity = sum(
            max(0, order.quantity - int(order.filled_quantity or 0))
            for order in portfolio.orders
            if order.side == "SELL" and order.signal_id == f"position:{position_id}"
            and order.status in {"SUBMITTED", "PARTIALLY_FILLED"}
        )
        available_quantity = max(0, pos.quantity - pending_quantity)
        exit_quantity = available_quantity if ratio >= 1.0 else min(available_quantity, max(1, int(pos.quantity * ratio)))
        if exit_quantity <= 0:
            return None, "تمام حجم قابل فروش قبلاً در سفارش خروج رزرو شده است."
        now = now_utc()
        order_type_by_reason = {
            "MANUAL_EXIT": "CLOSE", "STOP_LOSS": "STOP_EXIT", "TARGET_1": "TARGET_EXIT",
            "TIME_STOP": "TIME_EXIT", "SIGNAL_INVALIDATED": "SIGNAL_EXIT", "KILL_SWITCH": "KILL_EXIT",
        }
        order = BrokerOrder(
            id=f"ord_{uuid.uuid4().hex}", portfolio_id=portfolio.id,
            signal_id=f"position:{position_id}", symbol=pos.symbol, side="SELL",
            order_type=order_type_by_reason.get(reason_code, "CLOSE") if ratio >= 1.0 else "TRIM",
            price=current_price, quantity=exit_quantity, filled_quantity=0, status="SUBMITTED",
            created_at=now, updated_at=now,
        )
        action = "خروج کامل" if ratio >= 1.0 else f"کاهش {int(ratio * 100)}٪"
        return order, f"سفارش {action} {pos.symbol} ثبت شد؛ سود/زیان فقط روی snapshot رسمی بعدی محقق می‌شود."

    def toggle_kill_switch(self, portfolio: Portfolio, active: bool) -> str:
        """فعال یا غیرفعال‌سازی کلید قطع اضطراری معامله."""
        portfolio.kill_switch_active = active
        return "کلید قطع اضطراری معامله فعال شد (خرید جدید و افزایش حجم مسدود گردید)." if active else "کلید قطع اضطراری غیرفعال شد."


paper_broker = PaperBrokerService()
