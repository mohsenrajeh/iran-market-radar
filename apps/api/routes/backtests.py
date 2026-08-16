"""Backtest lab execution and reporting routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from packages.domain.models import BacktestRun, BacktestTrade, Instrument, EODBar
from packages.domain.schemas import BacktestLaunchRequest, BacktestSummaryResponse, BacktestTradeItem
from services.backtester.engine import run_backtest_simulation
from packages.shared.database import get_sync_db

router = APIRouter(prefix="/backtests", tags=["Backtest Lab"])


@router.get("", response_model=list[BacktestSummaryResponse])
def list_backtests(db: Session = Depends(get_sync_db)):
    """Lists past backtest runs."""
    runs = db.query(BacktestRun).order_by(BacktestRun.created_at.desc()).all()
    return runs


@router.post("", response_model=BacktestSummaryResponse)
def launch_backtest(req: BacktestLaunchRequest, db: Session = Depends(get_sync_db)):
    """Launches a new event-driven backtest simulation across all active universe symbols."""
    # Gather historical bars for all universe instruments
    instruments = db.query(Instrument).filter(Instrument.is_active == True).all()
    symbol_bars_map = {}

    for inst in instruments:
        bars = (
            db.query(EODBar)
            .filter(EODBar.instrument_id == inst.id)
            .order_by(EODBar.trading_date.asc())
            .all()
        )
        if len(bars) >= 40:
            symbol_bars_map[inst.ticker] = [
                {
                    "trading_date": b.trading_date.isoformat(),
                    "open": b.open,
                    "high": b.high,
                    "low": b.low,
                    "close": b.close,
                    "last": b.last,
                    "yesterday_price": b.yesterday_price,
                    "volume": b.volume,
                    "value": b.value,
                    "trade_count": b.trade_count,
                    "allowed_min": b.allowed_min,
                    "allowed_max": b.allowed_max,
                }
                for b in bars
            ]

    if not symbol_bars_map:
        raise HTTPException(status_code=400, detail="داده کافی برای اجرای بک‌تست در پایگاه داده موجود نیست.")

    horizon_val = 5
    if "3" in req.horizon: horizon_val = 3
    elif "10" in req.horizon: horizon_val = 10

    run_obj, trades, eq_curve = run_backtest_simulation(
        name=req.name,
        strategy_key=req.strategy_key,
        symbol_bars_map=symbol_bars_map,
        initial_capital=req.initial_capital,
        horizon_sessions=horizon_val,
    )

    db.add(run_obj)
    for tr in trades:
        db.add(tr)
    db.commit()
    db.refresh(run_obj)

    return run_obj


@router.get("/{backtest_id}", response_model=BacktestSummaryResponse)
def get_backtest_detail(backtest_id: str, db: Session = Depends(get_sync_db)):
    """Returns backtest summary statistics."""
    run = db.query(BacktestRun).filter(BacktestRun.id == backtest_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="بک‌تست مورد نظر یافت نشد.")
    return run


@router.get("/{backtest_id}/trades", response_model=list[BacktestTradeItem])
def get_backtest_trades(backtest_id: str, db: Session = Depends(get_sync_db)):
    """Returns detailed auditable trade log of a backtest."""
    trades = db.query(BacktestTrade).filter(BacktestTrade.backtest_id == backtest_id).all()
    return trades
