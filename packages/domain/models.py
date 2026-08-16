"""Canonical database ORM models for Iran Market Radar."""
import uuid
import enum
from datetime import datetime, date
from sqlalchemy import (
    String, Float, Integer, Boolean, DateTime, Date, Text,
    ForeignKey, Index, UniqueConstraint, JSON
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from packages.shared.database import Base
from packages.shared.datetime_utils import now_utc


def generate_uuid() -> str:
    return str(uuid.uuid4())


# ==========================================
# 1. Reference Models
# ==========================================

class Sector(Base):
    __tablename__ = "sector"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name_fa: Mapped[str] = mapped_column(String(128), index=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    instruments: Mapped[list["Instrument"]] = relationship("Instrument", back_populates="sector")


class Instrument(Base):
    __tablename__ = "instrument"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    source_instrument_code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    isin: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    ticker: Mapped[str] = mapped_column(String(64), index=True)
    ticker_normalized: Mapped[str] = mapped_column(String(64), index=True)
    name_fa: Mapped[str] = mapped_column(String(255))
    instrument_class: Mapped[str] = mapped_column(String(32), default="equity")  # equity, equity_etf, bond, right
    market: Mapped[str] = mapped_column(String(32), default="TSE")  # TSE, IFB
    board: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sector_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("sector.id"), nullable=True)
    company_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    listed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delisted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    base_volume: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    sector: Mapped[Sector | None] = relationship("Sector", back_populates="instruments")
    eod_bars: Mapped[list["EODBar"]] = relationship("EODBar", back_populates="instrument", cascade="all, delete-orphan")
    snapshots: Mapped[list["MarketSnapshot"]] = relationship("MarketSnapshot", back_populates="instrument", cascade="all, delete-orphan")
    signals: Mapped[list["PublishedSignal"]] = relationship("PublishedSignal", back_populates="instrument", cascade="all, delete-orphan")


class TradingSession(Base):
    __tablename__ = "trading_session"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    market: Mapped[str] = mapped_column(String(32), default="TSE")
    session_date: Mapped[date] = mapped_column(Date, index=True)
    open_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    close_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_open: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(32), default="CLOSED")

    __table_args__ = (UniqueConstraint("market", "session_date", name="uq_market_session_date"),)


# ==========================================
# 2. Market Data Models
# ==========================================

class EODBar(Base):
    __tablename__ = "eod_bar"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    instrument_id: Mapped[str] = mapped_column(String(36), ForeignKey("instrument.id"), index=True)
    trading_date: Mapped[date] = mapped_column(Date, index=True)
    
    # Raw Prices (Rials)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)  # Closing price (قیمت پایانی)
    last: Mapped[float] = mapped_column(Float)   # Last trade price (آخرین معامله)
    yesterday_price: Mapped[float] = mapped_column(Float)
    
    # Volume & Trades
    volume: Mapped[int] = mapped_column(Integer)
    value: Mapped[float] = mapped_column(Float)
    trade_count: Mapped[int] = mapped_column(Integer)
    
    # Range Limits
    allowed_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    allowed_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    # Adjusted Price & Factor
    adj_close: Mapped[float | None] = mapped_column(Float, nullable=True)
    adjustment_factor: Mapped[float] = mapped_column(Float, default=1.0)
    
    # Timestamps
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    instrument: Mapped[Instrument] = relationship("Instrument", back_populates="eod_bars")

    __table_args__ = (
        UniqueConstraint("instrument_id", "trading_date", name="uq_eod_instrument_date"),
        Index("ix_eod_inst_date", "instrument_id", "trading_date"),
    )


class MarketSnapshot(Base):
    __tablename__ = "market_snapshot"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    instrument_id: Mapped[str] = mapped_column(String(36), ForeignKey("instrument.id"), index=True)
    source_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    
    last_price: Mapped[float] = mapped_column(Float)
    close_price: Mapped[float] = mapped_column(Float)
    high_price: Mapped[float] = mapped_column(Float)
    low_price: Mapped[float] = mapped_column(Float)
    yesterday_price: Mapped[float] = mapped_column(Float)
    
    volume: Mapped[int] = mapped_column(Integer)
    value: Mapped[float] = mapped_column(Float)
    trade_count: Mapped[int] = mapped_column(Integer)
    
    allowed_min: Mapped[float] = mapped_column(Float)
    allowed_max: Mapped[float] = mapped_column(Float)
    state: Mapped[str] = mapped_column(String(32), default="A")  # A = Allowed, I = Suspended, etc.

    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    instrument: Mapped[Instrument] = relationship("Instrument", back_populates="snapshots")


class OrderBookSnapshot(Base):
    __tablename__ = "orderbook_snapshot"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    instrument_id: Mapped[str] = mapped_column(String(36), ForeignKey("instrument.id"), index=True)
    source_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    
    # 5 levels of best bids and asks stored as structured JSON array
    # [{"level": 1, "bid_price": 7800, "bid_volume": 100000, "bid_count": 42, "ask_price": 7850, "ask_volume": 50000, "ask_count": 18}, ...]
    depth_levels: Mapped[list[dict]] = mapped_column(JSON)
    spread: Mapped[float | None] = mapped_column(Float, nullable=True)
    bid_total_volume: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ask_total_volume: Mapped[int | None] = mapped_column(Integer, nullable=True)

    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class ClientTypeSnapshot(Base):
    """حقیقی و حقوقی data."""
    __tablename__ = "client_type_snapshot"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    instrument_id: Mapped[str] = mapped_column(String(36), ForeignKey("instrument.id"), index=True)
    trading_date: Mapped[date] = mapped_column(Date, index=True)
    
    # Individual / Real (حقیقی)
    real_buy_count: Mapped[int] = mapped_column(Integer)
    real_buy_volume: Mapped[int] = mapped_column(Integer)
    real_buy_value: Mapped[float] = mapped_column(Float)
    real_sell_count: Mapped[int] = mapped_column(Integer)
    real_sell_volume: Mapped[int] = mapped_column(Integer)
    real_sell_value: Mapped[float] = mapped_column(Float)
    
    # Legal / Institutional (حقوقی)
    legal_buy_count: Mapped[int] = mapped_column(Integer)
    legal_buy_volume: Mapped[int] = mapped_column(Integer)
    legal_buy_value: Mapped[float] = mapped_column(Float)
    legal_sell_count: Mapped[int] = mapped_column(Integer)
    legal_sell_volume: Mapped[int] = mapped_column(Integer)
    legal_sell_value: Mapped[float] = mapped_column(Float)

    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    __table_args__ = (
        UniqueConstraint("instrument_id", "trading_date", name="uq_client_type_inst_date"),
    )


# ==========================================
# 3. Fundamental / Codal Models
# ==========================================

class Filing(Base):
    __tablename__ = "filing"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    source_filing_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    instrument_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("instrument.id"), nullable=True, index=True)
    symbol: Mapped[str] = mapped_column(String(64), default="", index=True)
    title: Mapped[str] = mapped_column(String(512))
    filing_type: Mapped[str] = mapped_column(String(64))  # monthly_sales, interim_statement, material_disclosure, capital_increase, general_meeting
    filing_type_fa: Mapped[str] = mapped_column(String(128), default="")
    sentiment: Mapped[str] = mapped_column(String(32), default="neutral")  # positive, neutral, negative
    sentiment_fa: Mapped[str] = mapped_column(String(64), default="خنثی")
    impact_score: Mapped[float] = mapped_column(Float, default=5.0)  # 1.0 to 10.0
    summary_fa: Mapped[str] = mapped_column(Text, default="")
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    structured_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class FundamentalSnapshot(Base):
    """تصویر شاخص‌های بنیادی، نسبت‌های مالی و ارزندگی نماد."""
    __tablename__ = "fundamental_snapshot"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    instrument_id: Mapped[str] = mapped_column(String(36), ForeignKey("instrument.id"), index=True)
    symbol: Mapped[str] = mapped_column(String(64), index=True)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, index=True)
    
    # Valuation Multiples
    p_e_ratio: Mapped[float] = mapped_column(Float, default=0.0)
    sector_p_e: Mapped[float] = mapped_column(Float, default=0.0)
    p_s_ratio: Mapped[float] = mapped_column(Float, default=0.0)
    p_b_ratio: Mapped[float] = mapped_column(Float, default=0.0)
    eps: Mapped[float] = mapped_column(Float, default=0.0)
    dps: Mapped[float] = mapped_column(Float, default=0.0)
    dividend_yield: Mapped[float] = mapped_column(Float, default=0.0)
    peg_ratio: Mapped[float] = mapped_column(Float, default=1.0)
    
    # Margins & Return
    gross_margin_pct: Mapped[float] = mapped_column(Float, default=0.0)
    operating_margin_pct: Mapped[float] = mapped_column(Float, default=0.0)
    net_margin_pct: Mapped[float] = mapped_column(Float, default=0.0)
    roe_pct: Mapped[float] = mapped_column(Float, default=0.0)
    roa_pct: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Sales & Growth
    monthly_sales_growth_yoy: Mapped[float] = mapped_column(Float, default=0.0)
    monthly_sales_growth_mom: Mapped[float] = mapped_column(Float, default=0.0)
    latest_monthly_sales_rials: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Financial Health
    piotroski_f_score: Mapped[int] = mapped_column(Integer, default=5)  # 0 to 9
    debt_to_equity: Mapped[float] = mapped_column(Float, default=0.0)
    current_ratio: Mapped[float] = mapped_column(Float, default=1.0)
    market_cap_rials: Mapped[float] = mapped_column(Float, default=0.0)
    floating_shares_pct: Mapped[float] = mapped_column(Float, default=20.0)
    
    # Scoring & Verdict
    fundamental_score: Mapped[float] = mapped_column(Float, default=50.0)  # 0 to 100
    fundamental_grade: Mapped[str] = mapped_column(String(8), default="B")  # A+, A, B, C
    valuation_status: Mapped[str] = mapped_column(String(32), default="fair")  # undervalued, fair, overvalued
    valuation_status_fa: Mapped[str] = mapped_column(String(64), default="قیمت منصفانه")
    analysis_summary_fa: Mapped[str] = mapped_column(Text, default="")
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)


# ==========================================
# 4. Analytical & Opportunity Models
# ==========================================

class FeatureSnapshot(Base):
    __tablename__ = "feature_snapshot"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    instrument_id: Mapped[str] = mapped_column(String(36), ForeignKey("instrument.id"), index=True)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    feature_version: Mapped[str] = mapped_column(String(32), default="v1")
    features_json: Mapped[dict] = mapped_column(JSON)
    data_quality_score: Mapped[float] = mapped_column(Float, default=100.0)

    __table_args__ = (
        UniqueConstraint("instrument_id", "as_of", "feature_version", name="uq_feat_inst_asof_ver"),
    )


class MarketRegime(Base):
    __tablename__ = "market_regime"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    regime_label: Mapped[str] = mapped_column(String(32))  # risk_on, risk_off, neutral, distribution
    breadth_score: Mapped[float] = mapped_column(Float)
    turnover_ratio: Mapped[float] = mapped_column(Float)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class PublishedSignal(Base):
    """Canonical user-facing opportunity matching schemas/signal.schema.json."""
    __tablename__ = "published_signal"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # e.g. sig_20260812_FOLAD
    instrument_id: Mapped[str] = mapped_column(String(36), ForeignKey("instrument.id"), index=True)
    symbol: Mapped[str] = mapped_column(String(64), index=True)
    name_fa: Mapped[str] = mapped_column(String(255))
    market: Mapped[str] = mapped_column(String(32), default="TSE")
    sector: Mapped[str | None] = mapped_column(String(128), nullable=True)
    
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    horizon: Mapped[str] = mapped_column(String(16), default="5d")  # 1d, 3d, 5d, 10d, 20d
    direction: Mapped[str] = mapped_column(String(16), default="long")
    actionable: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    grade: Mapped[str] = mapped_column(String(8), default="A")  # A+, A, B, C
    
    # 4 distinct quantitative outputs
    opportunity_score: Mapped[float] = mapped_column(Float, index=True)  # 0-100
    p_profit: Mapped[float] = mapped_column(Float)                      # 0-1 Calibrated probability
    confidence: Mapped[float] = mapped_column(Float)                    # 0-100
    signal_strength: Mapped[float] = mapped_column(Float)               # 0-100 Percentile rank
    
    expected_return_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    expected_drawdown_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_price: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Execution & Risk Levels
    entry_zone: Mapped[dict] = mapped_column(JSON)      # {"low": 10000, "high": 10200, "max_chase": 10300}
    invalidation: Mapped[dict] = mapped_column(JSON)    # {"price": 9650, "type": "structure_atr", "reason_fa": "..."}
    exit_plan: Mapped[dict] = mapped_column(JSON)       # {"type": "...", "targets": [10800, 11200], "time_stop_sessions": 5}
    
    liquidity_score: Mapped[float] = mapped_column(Float, default=80.0)
    fill_probability_score: Mapped[float] = mapped_column(Float, default=80.0)
    data_quality: Mapped[float] = mapped_column(Float, default=95.0)
    regime: Mapped[str] = mapped_column(String(32), default="risk_on")
    
    # Explanation
    strategy_votes: Mapped[list[dict]] = mapped_column(JSON)
    top_reasons_fa: Mapped[list[str]] = mapped_column(JSON)
    risk_flags_fa: Mapped[list[str]] = mapped_column(JSON)
    
    # Versions & Expiry
    model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    strategy_version: Mapped[str] = mapped_column(String(64), default="2026.08.1")
    calibration_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    instrument: Mapped[Instrument] = relationship("Instrument", back_populates="signals")


# ==========================================
# 5. Backtest Models
# ==========================================

class BacktestRun(Base):
    __tablename__ = "backtest_run"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(128))
    strategy_key: Mapped[str] = mapped_column(String(64))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    horizon: Mapped[str] = mapped_column(String(16), default="5d")
    initial_capital: Mapped[float] = mapped_column(Float, default=1_000_000_000.0)  # 1 Billion Rials
    final_equity: Mapped[float] = mapped_column(Float, default=1_000_000_000.0)
    total_return_pct: Mapped[float] = mapped_column(Float, default=0.0)
    sharpe_ratio: Mapped[float] = mapped_column(Float, default=0.0)
    sortino_ratio: Mapped[float] = mapped_column(Float, default=0.0)
    max_drawdown_pct: Mapped[float] = mapped_column(Float, default=0.0)
    win_rate_pct: Mapped[float] = mapped_column(Float, default=0.0)
    profit_factor: Mapped[float] = mapped_column(Float, default=0.0)
    trade_count: Mapped[int] = mapped_column(Integer, default=0)
    config_json: Mapped[dict] = mapped_column(JSON)
    metrics_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="COMPLETED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    trades: Mapped[list["BacktestTrade"]] = relationship("BacktestTrade", back_populates="backtest", cascade="all, delete-orphan")


class BacktestTrade(Base):
    __tablename__ = "backtest_trade"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    backtest_id: Mapped[str] = mapped_column(String(36), ForeignKey("backtest_run.id"), index=True)
    symbol: Mapped[str] = mapped_column(String(64))
    entry_date: Mapped[date] = mapped_column(Date)
    exit_date: Mapped[date] = mapped_column(Date)
    entry_price: Mapped[float] = mapped_column(Float)
    exit_price: Mapped[float] = mapped_column(Float)
    quantity: Mapped[int] = mapped_column(Integer)
    gross_pnl: Mapped[float] = mapped_column(Float)
    net_pnl: Mapped[float] = mapped_column(Float)
    return_pct: Mapped[float] = mapped_column(Float)
    exit_reason: Mapped[str] = mapped_column(String(64))
    holding_days: Mapped[int] = mapped_column(Integer)

    backtest: Mapped[BacktestRun] = relationship("BacktestRun", back_populates="trades")


# ==========================================
# 6. Paper Trading & Ledger Models
# ==========================================

class Portfolio(Base):
    __tablename__ = "portfolio"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(64), default="پورتفوی آزمایشی پیش‌فرض")
    mode: Mapped[str] = mapped_column(String(16), default="paper")  # paper, live_disabled
    cash: Mapped[float] = mapped_column(Float, default=100_000_000_000.0)
    initial_cash: Mapped[float] = mapped_column(Float, default=100_000_000_000.0)
    realized_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    kill_switch_active: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    positions: Mapped[list["Position"]] = relationship("Position", back_populates="portfolio")
    orders: Mapped[list["BrokerOrder"]] = relationship("BrokerOrder", back_populates="portfolio")
    closed_trades: Mapped[list["ClosedTradeHistory"]] = relationship("ClosedTradeHistory", back_populates="portfolio")


class Position(Base):
    __tablename__ = "position"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    portfolio_id: Mapped[str] = mapped_column(String(36), ForeignKey("portfolio.id"), index=True)
    symbol: Mapped[str] = mapped_column(String(64), index=True)
    quantity: Mapped[int] = mapped_column(Integer)
    average_entry_price: Mapped[float] = mapped_column(Float)
    current_price: Mapped[float] = mapped_column(Float)
    unrealized_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    stop_loss: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_invested_rials: Mapped[float] = mapped_column(Float, default=0.0)
    risk_pct: Mapped[float] = mapped_column(Float, default=0.5)
    risk_reward_ratio: Mapped[str] = mapped_column(String(32), default="1:2.0")
    expected_days_to_target: Mapped[int] = mapped_column(Integer, default=5)
    market_regime: Mapped[str] = mapped_column(String(32), default="risk_on")
    decision_method: Mapped[str] = mapped_column(String(128), default="")
    entry_reason_fa: Mapped[str] = mapped_column(Text, default="")
    risk_flags_fa: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    client_power_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    is_open: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    portfolio: Mapped[Portfolio] = relationship("Portfolio", back_populates="positions")


class BrokerOrder(Base):
    __tablename__ = "broker_order"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    portfolio_id: Mapped[str] = mapped_column(String(36), ForeignKey("portfolio.id"), index=True)
    signal_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    symbol: Mapped[str] = mapped_column(String(64), index=True)
    side: Mapped[str] = mapped_column(String(8))  # BUY, SELL
    order_type: Mapped[str] = mapped_column(String(16), default="LIMIT")
    price: Mapped[float] = mapped_column(Float)
    quantity: Mapped[int] = mapped_column(Integer)
    filled_quantity: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="PENDING")  # PENDING, SUBMITTED, PARTIALLY_FILLED, FILLED, CANCELLED, REJECTED
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    portfolio: Mapped[Portfolio] = relationship("Portfolio", back_populates="orders")


class PaperTradeLog(Base):
    """لاگ کامل هر معامله آزمایشی برای آموزش ML و بازخورد."""
    __tablename__ = "paper_trade_log"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    portfolio_id: Mapped[str] = mapped_column(String(36), ForeignKey("portfolio.id"), index=True)
    symbol: Mapped[str] = mapped_column(String(64), index=True)
    side: Mapped[str] = mapped_column(String(8))  # BUY, SELL
    entry_price: Mapped[float] = mapped_column(Float)
    exit_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    quantity: Mapped[int] = mapped_column(Integer)
    total_invested_rials: Mapped[float] = mapped_column(Float, default=0.0)
    entry_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    exit_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    holding_hours: Mapped[float] = mapped_column(Float, default=0.0)
    holding_days: Mapped[float] = mapped_column(Float, default=0.0)
    expected_days_to_target: Mapped[int] = mapped_column(Integer, default=5)
    market_regime: Mapped[str] = mapped_column(String(32), default="risk_on")
    gross_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    net_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    return_pct: Mapped[float] = mapped_column(Float, default=0.0)
    risk_pct: Mapped[float] = mapped_column(Float, default=0.5)
    risk_reward_ratio: Mapped[float] = mapped_column(Float, default=2.0)
    decision_method: Mapped[str] = mapped_column(String(128), default="")
    features_at_entry: Mapped[dict] = mapped_column(JSON, default=dict)
    features_at_exit: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    strategy_votes_at_entry: Mapped[list[dict]] = mapped_column(JSON, default=list)
    exit_reason: Mapped[str] = mapped_column(String(64), default="open")
    indicator_scores: Mapped[dict] = mapped_column(JSON, default=dict)
    reason_fa: Mapped[str] = mapped_column(Text, default="")
    lesson_fa: Mapped[str] = mapped_column(Text, default="")
    is_closed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)


class IndicatorPerformance(Base):
    """عملکرد تجمعی هر اندیکاتور در معاملات آزمایشی."""
    __tablename__ = "indicator_performance"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    indicator_name: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    display_name_fa: Mapped[str] = mapped_column(String(128), default="")
    total_signals: Mapped[int] = mapped_column(Integer, default=0)
    profitable_signals: Mapped[int] = mapped_column(Integer, default=0)
    loss_signals: Mapped[int] = mapped_column(Integer, default=0)
    avg_return_when_bullish: Mapped[float] = mapped_column(Float, default=0.0)
    avg_return_when_bearish: Mapped[float] = mapped_column(Float, default=0.0)
    precision: Mapped[float] = mapped_column(Float, default=0.0)
    recall: Mapped[float] = mapped_column(Float, default=0.0)
    f1_score: Mapped[float] = mapped_column(Float, default=0.0)
    cumulative_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    last_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class PortfolioSnapshot(Base):
    """تصویر لحظه‌ای پورتفو برای نمودار equity curve."""
    __tablename__ = "portfolio_snapshot"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    portfolio_id: Mapped[str] = mapped_column(String(36), ForeignKey("portfolio.id"), index=True)
    snapshot_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, index=True)
    cash: Mapped[float] = mapped_column(Float)
    positions_value: Mapped[float] = mapped_column(Float)
    total_equity: Mapped[float] = mapped_column(Float)
    open_positions_count: Mapped[int] = mapped_column(Integer, default=0)
    realized_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    unrealized_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    drawdown_pct: Mapped[float] = mapped_column(Float, default=0.0)


class CashLedger(Base):
    """دفترکل رویدادمحور تفکیک نقدینگی و تراکنش‌های حساب."""
    __tablename__ = "cash_ledger"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    portfolio_id: Mapped[str] = mapped_column(String(36), ForeignKey("portfolio.id"), index=True)
    transaction_type: Mapped[str] = mapped_column(String(32))  # INITIAL, BUY_FILL, SELL_FILL, FEE, DIVIDEND
    amount_rials: Mapped[float] = mapped_column(Float)
    settled_cash: Mapped[float] = mapped_column(Float)
    unsettled_cash: Mapped[float] = mapped_column(Float, default=0.0)
    reserved_cash: Mapped[float] = mapped_column(Float, default=0.0)
    available_cash: Mapped[float] = mapped_column(Float)
    fees_due: Mapped[float] = mapped_column(Float, default=0.0)
    reference_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    description_fa: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class OrderFill(Base):
    """ثبت واقعی اجرای سفارشات همراه با اسلیپیج و تاخیر صف."""
    __tablename__ = "order_fill"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    order_id: Mapped[str] = mapped_column(String(64), index=True)
    symbol: Mapped[str] = mapped_column(String(64), index=True)
    side: Mapped[str] = mapped_column(String(8))
    fill_price: Mapped[float] = mapped_column(Float)
    quantity: Mapped[int] = mapped_column(Integer)
    slippage_rials: Mapped[float] = mapped_column(Float, default=0.0)
    fill_model: Mapped[str] = mapped_column(String(32), default="NEXT_BAR_AUCTION")
    fees_rials: Mapped[float] = mapped_column(Float, default=0.0)
    tax_rials: Mapped[float] = mapped_column(Float, default=0.0)
    net_value_rials: Mapped[float] = mapped_column(Float)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class CorporateAction(Base):
    """دفترکل اقدامات شرکتی (افزایش سرمایه، سود نقدی، توقف و بازگشایی)."""
    __tablename__ = "corporate_action"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    symbol: Mapped[str] = mapped_column(String(64), index=True)
    action_type: Mapped[str] = mapped_column(String(32))  # CAPITAL_INCREASE, CASH_DIVIDEND, HALT, RESUME
    ratio: Mapped[float] = mapped_column(Float, default=0.0)
    cash_per_share: Mapped[float] = mapped_column(Float, default=0.0)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    effective_date: Mapped[date] = mapped_column(Date)
    is_processed: Mapped[bool] = mapped_column(Boolean, default=True)


class DecisionAudit(Base):
    """ثبت غیرقابل تغییر دلایل پذیرش یا رد سیگنال و سفارش (Decision Envelope)."""
    __tablename__ = "decision_audit"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    symbol: Mapped[str] = mapped_column(String(64), index=True)
    signal_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model_version: Mapped[str] = mapped_column(String(64), default="v2.4-isotonic-brier")
    dataset_version: Mapped[str] = mapped_column(String(64), default="tse-pit-2026-08")
    risk_policy_version: Mapped[str] = mapped_column(String(32), default="RP-15DD-1RISK")
    decision: Mapped[str] = mapped_column(String(32))  # APPROVED, REJECTED_RISK, REJECTED_SECTOR_CAP, REJECTED_LIQUIDITY
    decision_reason_fa: Mapped[str] = mapped_column(Text, default="")
    opportunity_score: Mapped[float] = mapped_column(Float, default=0.0)
    p_profit: Mapped[float] = mapped_column(Float, default=0.0)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


# ==========================================
# 6. Closed Trade History & Learning Models
# ==========================================

class TradeExitReason(str, enum.Enum):
    STOP_LOSS = "STOP_LOSS"
    TARGET_1 = "TARGET_1"
    TARGET_2 = "TARGET_2"
    TRAILING_STOP = "TRAILING_STOP"
    TIME_STOP = "TIME_STOP"
    SIGNAL_INVALIDATED = "SIGNAL_INVALIDATED"
    REGIME_CHANGE = "REGIME_CHANGE"
    RISK_REDUCTION = "RISK_REDUCTION"
    KILL_SWITCH = "KILL_SWITCH"
    MANUAL_EXIT = "MANUAL_EXIT"
    CORPORATE_ACTION = "CORPORATE_ACTION"
    LIQUIDITY_EXIT = "LIQUIDITY_EXIT"
    OTHER = "OTHER"


class TradeOutcomeStatus(str, enum.Enum):
    WIN = "WIN"
    LOSS = "LOSS"
    BREAKEVEN = "BREAKEVEN"


class SampleSufficiency(str, enum.Enum):
    INSUFFICIENT_SAMPLE = "INSUFFICIENT_SAMPLE"  # n < 20
    EARLY_EVIDENCE = "EARLY_EVIDENCE"          # 20 <= n < 50
    EVALUATING = "EVALUATING"                  # 50 <= n < 100
    STATISTICALLY_STABLE = "STATISTICALLY_STABLE" # n >= 100 with CI convergence


class ProposalStatus(str, enum.Enum):
    PROPOSED = "PROPOSED"
    BACKTESTING = "BACKTESTING"
    REJECTED = "REJECTED"
    OOS_TESTING = "OOS_TESTING"
    PAPER_CHALLENGER = "PAPER_CHALLENGER"
    APPROVED = "APPROVED"
    PROMOTED = "PROMOTED"


class LessonCategory(str, enum.Enum):
    ENTRY = "ENTRY"
    EXIT = "EXIT"
    RISK = "RISK"
    EXECUTION = "EXECUTION"
    TECHNICAL = "TECHNICAL"
    FUNDAMENTAL = "FUNDAMENTAL"
    CODAL = "CODAL"
    LIQUIDITY = "LIQUIDITY"
    REGIME = "REGIME"
    POSITION_SIZE = "POSITION_SIZE"


class ClosedTradeHistory(Base):
    """تاریخچه کامل، تغییرناپذیر و حسابداری‌شده معاملات بسته‌شده."""
    __tablename__ = "closed_trade_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    portfolio_id: Mapped[str] = mapped_column(String(36), ForeignKey("portfolio.id"), index=True)
    position_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    instrument_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    symbol: Mapped[str] = mapped_column(String(64), index=True)
    company_name: Mapped[str] = mapped_column(String(128), default="")
    sector: Mapped[str] = mapped_column(String(64), default="عمومی", index=True)

    strategy_id: Mapped[str] = mapped_column(String(64), index=True)
    strategy_name_fa: Mapped[str] = mapped_column(String(128), default="")
    strategy_version: Mapped[str] = mapped_column(String(32), default="v1.0", index=True)
    model_version: Mapped[str] = mapped_column(String(64), default="v2.4-isotonic-brier", index=True)
    risk_policy_version: Mapped[str] = mapped_column(String(32), default="POL-TSE-2026-V2.5")
    market_rules_version: Mapped[str] = mapped_column(String(32), default="TSE-RULES-2026-V1.0")
    dataset_version: Mapped[str] = mapped_column(String(64), default="tse-pit-2026-08")

    signal_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    decision_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    decision_method: Mapped[str] = mapped_column(String(128), default="")

    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    closed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    holding_sessions: Mapped[int] = mapped_column(Integer, default=1)
    holding_duration_hours: Mapped[float] = mapped_column(Float, default=0.0)

    planned_entry: Mapped[float] = mapped_column(Float)
    avg_entry_price: Mapped[float] = mapped_column(Float)
    avg_exit_price: Mapped[float] = mapped_column(Float)
    total_quantity: Mapped[int] = mapped_column(Integer)

    gross_buy_value: Mapped[float] = mapped_column(Float, default=0.0)
    gross_sell_value: Mapped[float] = mapped_column(Float, default=0.0)
    entry_fees: Mapped[float] = mapped_column(Float, default=0.0)
    exit_fees: Mapped[float] = mapped_column(Float, default=0.0)
    tax: Mapped[float] = mapped_column(Float, default=0.0)
    slippage_cost: Mapped[float] = mapped_column(Float, default=0.0)
    total_cost: Mapped[float] = mapped_column(Float, default=0.0)

    gross_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    net_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    net_return_pct: Mapped[float] = mapped_column(Float, default=0.0)

    initial_risk_amount: Mapped[float] = mapped_column(Float, default=0.0)
    initial_risk_pct_nav: Mapped[float] = mapped_column(Float, default=0.35)
    realized_R: Mapped[float] = mapped_column(Float, default=0.0)
    MFE: Mapped[float] = mapped_column(Float, default=0.0)  # Max Favorable Excursion %
    MAE: Mapped[float] = mapped_column(Float, default=0.0)  # Max Adverse Excursion %

    initial_stop: Mapped[float] = mapped_column(Float, default=0.0)
    final_stop: Mapped[float] = mapped_column(Float, default=0.0)
    target1: Mapped[float] = mapped_column(Float, default=0.0)
    target2: Mapped[float] = mapped_column(Float, default=0.0)

    exit_reason: Mapped[str] = mapped_column(String(32), default="MANUAL_EXIT", index=True)
    exit_reason_detail: Mapped[str] = mapped_column(String(255), default="")
    market_regime_at_entry: Mapped[str] = mapped_column(String(32), default="risk_on", index=True)
    market_regime_at_exit: Mapped[str] = mapped_column(String(32), default="risk_on")

    portfolio_nav_at_entry: Mapped[float] = mapped_column(Float, default=100_000_000_000.0)
    portfolio_nav_at_exit: Mapped[float] = mapped_column(Float, default=100_000_000_000.0)
    position_weight_at_entry: Mapped[float] = mapped_column(Float, default=0.08)

    outcome_status: Mapped[str] = mapped_column(String(16), default="WIN", index=True)
    reason_fa: Mapped[str] = mapped_column(Text, default="")
    lesson_fa: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="closed_trades")
    timeline_events: Mapped[list["TradeExecutionTimeline"]] = relationship(
        "TradeExecutionTimeline", back_populates="trade", cascade="all, delete-orphan", order_by="TradeExecutionTimeline.timestamp"
    )
    post_mortem: Mapped["TradePostMortem | None"] = relationship(
        "TradePostMortem", back_populates="trade", uselist=False, cascade="all, delete-orphan"
    )


class TradeExecutionTimeline(Base):
    """ره‌گیری زمانی و گام‌به‌گام اجرای معامله (ورود، پله‌ها، تعدیل استاپ، خروج‌ها)."""
    __tablename__ = "trade_execution_timeline"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    trade_id: Mapped[str] = mapped_column(String(36), ForeignKey("closed_trade_history.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(32))  # SIGNAL_TRIGGER, ENTRY_FILL, SCALE_IN_FILL, STOP_ADJUST, TARGET_1_FILL, TARGET_2_FILL, TRAILING_STOP_FILL, FINAL_EXIT_FILL
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, index=True)
    price: Mapped[float] = mapped_column(Float)
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    portion_pct: Mapped[float] = mapped_column(Float, default=0.0)
    fees: Mapped[float] = mapped_column(Float, default=0.0)
    notes_fa: Mapped[str] = mapped_column(String(255), default="")

    trade: Mapped["ClosedTradeHistory"] = relationship("ClosedTradeHistory", back_populates="timeline_events")


class TradePostMortem(Base):
    """کالبدشکافی داده‌محور و مستقل هر معامله بسته جهت حذف سوگیری نتیجه‌گرایی."""
    __tablename__ = "trade_post_mortem"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    trade_id: Mapped[str] = mapped_column(String(36), ForeignKey("closed_trade_history.id"), unique=True, index=True)
    entry_efficiency: Mapped[float] = mapped_column(Float, default=0.95)
    exit_efficiency: Mapped[float] = mapped_column(Float, default=0.88)
    process_quality_score: Mapped[float] = mapped_column(Float, default=90.0)
    outcome_vs_process_type: Mapped[str] = mapped_column(String(32), default="GOOD_PROCESS_WIN")  # GOOD_PROCESS_WIN, GOOD_PROCESS_LOSS, BAD_PROCESS_WIN, BAD_PROCESS_LOSS
    what_worked_fa: Mapped[str] = mapped_column(Text, default="")
    what_failed_fa: Mapped[str] = mapped_column(Text, default="")
    entry_quality_fa: Mapped[str] = mapped_column(Text, default="")
    exit_quality_fa: Mapped[str] = mapped_column(Text, default="")
    position_sizing_quality_fa: Mapped[str] = mapped_column(Text, default="")
    execution_quality_fa: Mapped[str] = mapped_column(Text, default="")
    risk_compliance_fa: Mapped[str] = mapped_column(Text, default="")
    unexpected_market_behavior_fa: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    trade: Mapped["ClosedTradeHistory"] = relationship("ClosedTradeHistory", back_populates="post_mortem")


class StructuredLesson(Base):
    """درس آموخته‌شده ساختاریافته متصل به داده‌های عینی معامله."""
    __tablename__ = "structured_lesson"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    trade_id: Mapped[str] = mapped_column(String(36), ForeignKey("closed_trade_history.id"), index=True)
    category: Mapped[str] = mapped_column(String(32), index=True)  # ENTRY, EXIT, RISK, EXECUTION, TECHNICAL, FUNDAMENTAL, CODAL, LIQUIDITY, REGIME, POSITION_SIZE
    finding_fa: Mapped[str] = mapped_column(Text)
    evidence_data: Mapped[dict] = mapped_column(JSON, default=dict)
    confidence_pct: Mapped[float] = mapped_column(Float, default=85.0)
    action_candidate_fa: Mapped[str] = mapped_column(Text, default="")
    requires_validation: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class ExperimentProposal(Base):
    """صف تحقیقات کمّی: پیشنهاد بهبود بدون اجازه تغییر مستقیم پروداکشن (Challenger vs Champion)."""
    __tablename__ = "experiment_proposal"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    source_lesson_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    strategy_key: Mapped[str] = mapped_column(String(64), index=True)
    strategy_name_fa: Mapped[str] = mapped_column(String(128), default="")
    champion_version: Mapped[str] = mapped_column(String(32), default="v1.0")
    challenger_version: Mapped[str] = mapped_column(String(32), default="v1.1")
    status: Mapped[str] = mapped_column(String(32), default="PROPOSED", index=True)  # PROPOSED, BACKTESTING, REJECTED, OOS_TESTING, PAPER_CHALLENGER, APPROVED, PROMOTED
    hypothesis_fa: Mapped[str] = mapped_column(Text)
    parameter_changes: Mapped[dict] = mapped_column(JSON, default=dict)
    backtest_metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    oos_metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    sample_sufficiency: Mapped[str] = mapped_column(String(32), default="EARLY_EVIDENCE")
    rejection_reason_fa: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    promoted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


