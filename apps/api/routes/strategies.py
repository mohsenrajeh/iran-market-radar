"""Strategy catalog and lab diagnostics routes."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from packages.domain.models import BacktestRun
from packages.domain.schemas import StrategySummary
from packages.strategies.registry import strategy_registry
from packages.shared.database import get_sync_db

router = APIRouter(prefix="/strategies", tags=["Strategy Lab"])


@router.get("", response_model=list[StrategySummary])
def list_strategies(db: Session = Depends(get_sync_db)):
    """List registered engines and only actually persisted validation evidence."""
    summaries = []
    for strat in strategy_registry.list_strategies():
        run = db.query(BacktestRun).filter(
            BacktestRun.strategy_key == strat.key,
            BacktestRun.status == "COMPLETED",
        ).order_by(BacktestRun.created_at.desc()).first()
        metrics = (run.metrics_json or {}) if run else {}
        summaries.append(
            StrategySummary(
                key=strat.key,
                name_fa=strat.name_fa,
                enabled=True,
                version=strat.version,
                description_fa=f"استراتژی کمی {strat.name_fa} مبتنی بر فرضیات آزموده‌شده در بازار سرمایه ایران.",
                supported_horizons=list(strat.supported_horizons),
                historical_win_rate_pct=run.win_rate_pct if run else None,
                historical_brier_score=metrics.get("brier_score"),
                historical_trades=run.trade_count if run else 0,
                validation_status="COMPLETED" if run else "NOT_RUN",
                latest_backtest_id=run.id if run else None,
            )
        )
    return summaries
