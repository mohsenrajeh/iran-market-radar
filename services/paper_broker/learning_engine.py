"""Learning & Strategy Research Engine — Post-Mortem, Structured Lessons, and Research Queue."""
from datetime import datetime, timezone
import math
from sqlalchemy.orm import Session
from sqlalchemy import func

from packages.domain.models import (
    ClosedTradeHistory,
    TradeExecutionTimeline,
    TradePostMortem,
    StructuredLesson,
    ExperimentProposal,
    Portfolio,
    SampleSufficiency,
    ProposalStatus,
    LessonCategory,
    TradeOutcomeStatus,
    TradeExitReason,
)
from packages.shared.datetime_utils import now_utc
from packages.shared.logger import logger


class StrategyLearningEngine:
    """Core Quantitative Learning & Post-Mortem Engine."""

    def generate_post_mortem(self, db: Session, trade: ClosedTradeHistory) -> TradePostMortem:
        """Generates an evidence-based, outcome-bias-free post mortem analysis for a closed trade."""
        existing = db.query(TradePostMortem).filter(TradePostMortem.trade_id == trade.id).first()
        if existing:
            return existing

        # 1. Entry Efficiency: How close was actual fill to planned entry?
        if trade.planned_entry > 0:
            diff_pct = abs(trade.avg_entry_price - trade.planned_entry) / trade.planned_entry
            entry_eff = max(0.50, min(1.0, 1.0 - diff_pct * 3.0))
        else:
            entry_eff = 0.0

        # 2. Exit Efficiency: How much of favorable move did we capture?
        if trade.MFE > 0 and trade.net_return_pct > 0:
            exit_eff = min(1.0, max(0.50, trade.net_return_pct / max(trade.MFE, 0.01)))
        elif trade.outcome_status == "LOSS":
            # For loss, high efficiency means we cut loss quickly before MAE worsened
            exit_eff = min(1.0, max(0.60, 1.0 - abs(trade.net_return_pct) / max(trade.MAE, 0.01)))
        else:
            exit_eff = 0.0

        # 3. Process Quality Score (0 - 100)
        # Evaluates if the trade strictly adhered to risk budget, stops, and execution rules
        process_score = 100.0
        if trade.initial_risk_pct_nav > 0.40:
            process_score -= 15.0  # Over-risked
        if trade.slippage_cost > (trade.gross_buy_value * 0.005):
            process_score -= 10.0  # Excessive slippage
        if trade.exit_reason == "STOP_LOSS" and trade.realized_R < -1.2:
            process_score -= 15.0  # Stop slipped too far
        elif trade.exit_reason in ["TARGET_1", "TARGET_2", "TRAILING_STOP"]:
            process_score += 5.0

        process_score = max(0.0, min(100.0, process_score))

        # 4. Process vs Outcome Type (Eliminating Outcome Bias)
        is_win = trade.outcome_status == "WIN"
        if process_score >= 80.0:
            outcome_type = "GOOD_PROCESS_WIN" if is_win else "GOOD_PROCESS_LOSS"
        else:
            outcome_type = "BAD_PROCESS_WIN" if is_win else "BAD_PROCESS_LOSS"

        # 5. Descriptive Insights (Persian)
        if outcome_type == "GOOD_PROCESS_WIN":
            what_worked = f"معامله پس از {trade.holding_sessions} جلسه با {trade.realized_R:+.2f}R بسته شد و کنترل‌های قابل‌اندازه‌گیری امتیاز فرآیند {process_score:.1f} گرفتند."
            what_failed = "برای نسبت‌دادن نتیجه به یک عامل مشخص، نمونه‌های مشابه بیشتری لازم است."
        elif outcome_type == "GOOD_PROCESS_LOSS":
            what_worked = f"زیان در {trade.realized_R:+.2f}R بسته شد؛ دادهٔ ثبت‌شده کنترل ریسک را نشان می‌دهد."
            what_failed = f"سیگنال در رژیم ثبت‌شدهٔ {trade.market_regime_at_entry} به بازده مثبت نرسید؛ علت بازار از این رکورد به‌تنهایی قابل استنتاج نیست."
        elif outcome_type == "BAD_PROCESS_WIN":
            what_worked = f"بازده خالص ثبت‌شده {trade.net_return_pct:+.2f}٪ بود."
            what_failed = "با وجود سود، یکی از کنترل‌های قابل‌اندازه‌گیری ریسک/اجرا نقض شده است؛ علت دقیق باید از timeline بررسی شود."
        else:  # BAD_PROCESS_LOSS
            what_worked = "خروج ثبت و حسابداری معامله نهایی شده است."
            what_failed = "معامله زیان‌ده بوده و حداقل یک کنترل قابل‌اندازه‌گیری ریسک/اجرا نقض شده است؛ علت بدون شواهد بیشتر حدس زده نمی‌شود."

        post_mortem = TradePostMortem(
            trade_id=trade.id,
            entry_efficiency=round(entry_eff, 3),
            exit_efficiency=round(exit_eff, 3),
            process_quality_score=round(process_score, 1),
            outcome_vs_process_type=outcome_type,
            what_worked_fa=what_worked,
            what_failed_fa=what_failed,
            entry_quality_fa=f"راندمان ورود {entry_eff * 100:.1f}٪ — قیمت میانگین {trade.avg_entry_price:,.0f} ریال در برابر برنامه {trade.planned_entry:,.0f} ریال.",
            exit_quality_fa=f"راندمان خروج {exit_eff * 100:.1f}٪ — خروج در قیمت {trade.avg_exit_price:,.0f} ریال با دلیل {trade.exit_reason}.",
            position_sizing_quality_fa=f"تخصیص {trade.position_weight_at_entry * 100:.1f}٪ از کل پورتفو با ریسک اولیه {trade.initial_risk_pct_nav:.2f}٪ ارزش دارایی.",
            execution_quality_fa=f"اسلیپیج کل: {trade.slippage_cost / 10:,.0f} تومان ({((trade.slippage_cost / max(trade.gross_buy_value, 1.0)) * 100):.2f}٪ از کل معامله).",
            risk_compliance_fa=(
                f"ریسک اولیه ثبت‌شده {trade.initial_risk_pct_nav:.2f}٪ از NAV است؛ "
                "انطباق سقف صنعت و نقدینگی فقط با DecisionAudit همان لحظه قابل اثبات است."
            ),
            unexpected_market_behavior_fa="از رکورد معامله به‌تنهایی نمی‌توان رفتار غیرمنتظره بازار یا وضعیت صف را اثبات کرد.",
        )
        db.add(post_mortem)
        db.flush()

        # Extract structured lessons & potential proposals
        self._extract_lessons_and_proposals(db, trade, post_mortem)
        return post_mortem

    def _extract_lessons_and_proposals(self, db: Session, trade: ClosedTradeHistory, post_mortem: TradePostMortem):
        """Extracts structured machine-readable lessons and registers research queue proposals if needed."""
        # Lesson 1: Entry & Volume confirmation
        if trade.outcome_status == "LOSS" and trade.exit_reason == "STOP_LOSS":
            lesson1 = StructuredLesson(
                trade_id=trade.id,
                category="ENTRY",
                finding_fa=f"معامله {trade.symbol} با استراتژی {trade.strategy_name_fa} در حد ضرر و با {trade.realized_R:+.2f}R بسته شد.",
                evidence_data={
                    "strategy_id": trade.strategy_id,
                    "symbol": trade.symbol,
                    "realized_R": trade.realized_R,
                    "holding_sessions": trade.holding_sessions,
                    "mae_pct": trade.MAE,
                },
                confidence_pct=20.0,
                action_candidate_fa="این الگوی ورود را در حداقل ۲۰ معامله و دو رژیم بازار خوشه‌بندی و سپس فیلتر کاندید را تعریف کنید.",
                requires_validation=True,
            )
            db.add(lesson1)
            db.flush()

            # Create an Experiment Proposal for Research Queue
            prop = ExperimentProposal(
                source_lesson_id=lesson1.id,
                strategy_key=trade.strategy_id,
                strategy_name_fa=trade.strategy_name_fa,
                champion_version=trade.strategy_version,
                challenger_version=f"{trade.strategy_version}.1-research",
                status="PROPOSED",
                hypothesis_fa=f"بررسی شود آیا یک فیلتر ورودی قابل‌اندازه‌گیری برای {trade.strategy_name_fa} می‌تواند زیان‌های حد ضرر را بدون کاهش بیش‌ازحد فرصت‌ها کم کند.",
                parameter_changes={},
                backtest_metrics={},
                oos_metrics={},
                sample_sufficiency="INSUFFICIENT_SAMPLE",
            )
            db.add(prop)

        elif trade.outcome_status == "WIN" and trade.realized_R >= 2.0:
            lesson2 = StructuredLesson(
                trade_id=trade.id,
                category="EXIT",
                finding_fa=f"معامله {trade.symbol} با استراتژی {trade.strategy_name_fa} با {trade.realized_R:+.2f}R بسته شد.",
                evidence_data={
                    "strategy_id": trade.strategy_id,
                    "symbol": trade.symbol,
                    "net_return_pct": trade.net_return_pct,
                    "realized_R": trade.realized_R,
                    "mfe_pct": trade.MFE,
                },
                confidence_pct=20.0,
                action_candidate_fa="اثر قواعد خروج را فقط با بازپخش همان مسیر قیمت و مقایسهٔ counterfactual روی نمونه کافی ارزیابی کنید.",
                requires_validation=True,
            )
            db.add(lesson2)

    def evaluate_sample_sufficiency(self, n_samples: int, n_regimes: int = 0) -> tuple[SampleSufficiency, str]:
        """Calculates statistical sample sufficiency."""
        if n_samples < 20 or n_regimes < 2:
            return SampleSufficiency.INSUFFICIENT_SAMPLE, "نمونه ناکافی (حداقل ۲۰ معامله در ۲ رژیم بازار لازم است)"
        elif n_samples < 50:
            return SampleSufficiency.EARLY_EVIDENCE, "شواهد اولیه (۲۰ تا ۵۰ نمونه — در حال تجمیع داده)"
        elif n_samples < 100:
            return SampleSufficiency.EVALUATING, "در حال ارزیابی کمّی (۵۰ تا ۱۰۰ نمونه)"
        else:
            return SampleSufficiency.STATISTICALLY_STABLE, "از نظر آماری پایدار و همگرا (بیش از ۱۰۰ نمونه)"


learning_engine = StrategyLearningEngine()
