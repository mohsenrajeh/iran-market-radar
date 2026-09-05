"""Pydantic v2 schemas for API contracts, domain entities, and signals."""
from datetime import datetime, date
from typing import Literal, Any
from pydantic import BaseModel, Field, ConfigDict


# ==========================================
# 1. Market Overview & Sector Schemas
# ==========================================

class MarketIndexSummary(BaseModel):
    name_fa: str
    value: float
    change_pct: float
    change_value: float


class MarketOverviewResponse(BaseModel):
    session_status: str  # OPEN, PRE_OPEN, CLOSED
    session_status_fa: str
    current_time_utc: str
    current_time_jalali: str
    indices: list[MarketIndexSummary]
    breadth_advancers: int
    breadth_decliners: int
    breadth_unchanged: int
    total_volume: int
    total_value_rials: float
    market_regime: str  # risk_on, risk_off, neutral, distribution
    market_regime_fa: str
    regime_confidence: float
    opportunity_count_a_plus: int
    opportunity_count_a: int
    opportunity_count_b: int
    data_health_status: str  # HEALTHY, DEGRADED, STALE
    market_data_as_of_utc: str | None = None
    market_data_age_seconds: int | None = None
    data_health_reasons_fa: list[str] = Field(default_factory=list)


class SectorScorecard(BaseModel):
    sector_id: str
    code: str
    name_fa: str
    momentum_20d_pct: float
    breadth_pct: float
    net_real_inflow_rials: float
    turnover_value_rials: float
    opportunity_count: int
    relative_strength_rank: int


# ==========================================
# 2. Opportunity / Signal Schemas (Matching signal.schema.json)
# ==========================================

class EntryZone(BaseModel):
    low: float
    high: float
    max_chase: float | None = None


class Invalidation(BaseModel):
    price: float | None = None
    reason_fa: str
    type: str = "structure_atr"


class ExitPlan(BaseModel):
    type: str = "trailing_plus_time_stop"
    targets: list[float] = Field(default_factory=list)
    time_stop_sessions: int | None = None
    trailing_rule: str | None = None


class StrategyVote(BaseModel):
    strategy: str
    vote: float
    reason_fa: str


class PublishedSignalSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    instrument_id: str
    symbol: str
    name_fa: str
    market: str = "TSE"
    sector: str | None = None
    as_of: datetime
    horizon: str = "5d"
    direction: Literal["long"] = "long"
    actionable: bool = False
    grade: str = "C"
    
    opportunity_score: float = Field(ge=0, le=100)
    p_profit: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=100)
    signal_strength: float = Field(ge=0, le=100)
    
    expected_return_pct: float | None = None
    expected_drawdown_pct: float | None = None
    current_price: float = 0.0
    
    entry_zone: EntryZone
    invalidation: Invalidation
    exit_plan: ExitPlan
    
    liquidity_score: float = Field(ge=0, le=100)
    fill_probability_score: float = Field(ge=0, le=100)
    data_quality: float = Field(ge=0, le=100)
    regime: str = "unknown"
    
    strategy_votes: list[StrategyVote]
    top_reasons_fa: list[str]
    risk_flags_fa: list[str]
    decision_components: dict = Field(default_factory=dict)
    
    model_version: str | None = None
    strategy_version: str = "UNVERSIONED"
    calibration_version: str | None = None
    expires_at: datetime | None = None


# ==========================================
# 3. Chart & Bar Schemas
# ==========================================

class BarItem(BaseModel):
    date_str: str
    jalali_date: str
    open: float
    high: float
    low: float
    close: float
    last: float
    volume: int
    value: float
    trade_count: int
    allowed_min: float | None = None
    allowed_max: float | None = None
    real_buy_power_ratio: float | None = None  # سرانه حقیقی
    ema_20: float | None = None
    ema_50: float | None = None
    ema_100: float | None = None
    bb_upper: float | None = None
    bb_middle: float | None = None
    bb_lower: float | None = None
    rsi_14: float | None = None
    macd: float | None = None
    macd_signal: float | None = None
    macd_hist: float | None = None
    vol_ma_20: float | None = None
    real_buy_val: float | None = None
    legal_buy_val: float | None = None
    real_sell_val: float | None = None
    legal_sell_val: float | None = None
    net_real_inflow: float | None = None
    ichimoku_tenkan: float | None = None
    ichimoku_kijun: float | None = None
    ichimoku_senkou_a: float | None = None
    ichimoku_senkou_b: float | None = None
    supertrend: float | None = None
    supertrend_dir: float | None = None
    adx_14: float | None = None
    mfi_14: float | None = None
    stoch_rsi_k: float | None = None
    stoch_rsi_d: float | None = None
    cci_20: float | None = None
    williams_r: float | None = None
    cmf_20: float | None = None


class SymbolChartResponse(BaseModel):
    symbol: str
    name_fa: str
    isin: str
    market: str
    sector: str | None = None
    bars: list[BarItem]
    resistance_levels: list[float] = []
    support_levels: list[float] = []
    technical_analysis: dict | None = None
    orderbook_depth: list[dict] = []


# ==========================================
# 4. Strategy Diagnostic Schemas
# ==========================================

class StrategySummary(BaseModel):
    key: str
    name_fa: str
    enabled: bool
    version: str
    description_fa: str
    supported_horizons: list[str]
    historical_win_rate_pct: float | None = None
    historical_brier_score: float | None = None
    historical_trades: int = 0
    validation_status: str = "NOT_RUN"
    latest_backtest_id: str | None = None


# ==========================================
# 5. Backtest Schemas
# ==========================================

class BacktestLaunchRequest(BaseModel):
    name: str = "تست استراتژی مومنتوم و پولبک"
    strategy_key: str = "cross_sectional_momentum"
    start_date: str = "2025-01-01"
    end_date: str = "2026-08-01"
    horizon: str = "5d"
    initial_capital: float = 1_000_000_000.0


class BacktestSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    strategy_key: str
    start_date: date
    end_date: date
    horizon: str
    initial_capital: float
    final_equity: float
    total_return_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown_pct: float
    win_rate_pct: float
    profit_factor: float
    trade_count: int
    status: str
    created_at: datetime


class BacktestTradeItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    symbol: str
    entry_date: date
    exit_date: date
    entry_price: float
    exit_price: float
    quantity: int
    gross_pnl: float
    net_pnl: float
    return_pct: float
    exit_reason: str
    holding_days: int


# ==========================================
# 6. Paper Trading Schemas
# ==========================================

class OrderCreateFromSignalRequest(BaseModel):
    signal_id: str
    quantity: int | None = Field(default=None, ge=1)
    capital_allocation: float | None = Field(default=None, gt=0)


class PositionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    symbol: str
    quantity: int
    average_entry_price: float
    current_price: float
    unrealized_pnl: float
    unrealized_pnl_pct: float = 0.0
    stop_loss: float | None = None
    target_price: float | None = None
    total_invested_rials: float = 0.0
    total_invested_tomans: float = 0.0
    risk_pct: float = 0.0
    risk_reward_ratio: str | float = "UNKNOWN"
    expected_days_to_target: int = 0
    days_open: float = 0.0
    market_regime: str = "unknown"
    market_regime_fa: str = "نامشخص"
    decision_method: str = ""
    entry_reason_fa: str = ""
    distance_to_target_pct: float | None = None
    distance_to_stop_pct: float | None = None
    client_power_ratio: float | None = None
    risk_flags_fa: list[str] = []
    opened_at: datetime
    is_open: bool


class PortfolioResponse(BaseModel):
    id: str
    name: str
    campaign_id: str | None = None
    campaign_status: str | None = None
    campaign_started_at: datetime | None = None
    campaign_ends_at: datetime | None = None
    initial_cash: float
    cash: float
    total_equity: float
    realized_pnl: float
    unrealized_pnl: float
    open_positions_count: int
    kill_switch_active: bool
    portfolio_snapshot_id: str
    ledger_sequence: int
    risk_policy_version: str
    as_of: str
    positions: list[PositionResponse]


class PositionDetailResponse(BaseModel):
    position: PositionResponse
    name_fa: str
    sector_name: str
    target_price_2: float | None
    progress_to_target_pct: float | None
    distance_to_target_rials: float | None
    distance_to_stop_rials: float | None
    candles: list[dict]
    strategy_votes: list[dict]
    active_indicators: dict
    ai_recommendation_fa: str
    ai_summary_fa: str


# ==========================================
# 7. Data Health Schemas
# ==========================================

class SourceHealthItem(BaseModel):
    source_name: str
    status: str  # HEALTHY, WARNING, CRITICAL
    last_sync_utc: str
    freshness_delay_seconds: int
    completeness_pct: float
    duplicate_ratio: float
    error_rate_pct: float
    total_symbols_tracked: int


class DataHealthResponse(BaseModel):
    overall_status: str
    sources: list[SourceHealthItem]
    system_time_utc: str


# ==========================================
# 8. Fundamental & Codal Intelligence Schemas
# ==========================================

class FundamentalItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    symbol: str
    name_fa: str = ""
    sector_name: str = ""
    as_of: str
    
    # Valuation Multiples
    p_e_ratio: float
    sector_p_e: float
    p_s_ratio: float
    p_b_ratio: float
    eps: float
    dps: float
    dividend_yield: float
    peg_ratio: float = 1.0
    
    # Margins & Return
    gross_margin_pct: float
    operating_margin_pct: float
    net_margin_pct: float
    roe_pct: float
    roa_pct: float
    
    # Sales & Growth
    monthly_sales_growth_yoy: float
    monthly_sales_growth_mom: float
    latest_monthly_sales_rials: float
    
    # Health & Verdict
    piotroski_f_score: int
    debt_to_equity: float
    current_ratio: float
    market_cap_rials: float
    floating_shares_pct: float
    fundamental_score: float
    fundamental_grade: str
    valuation_status: str
    valuation_status_fa: str
    analysis_summary_fa: str
    recent_filings_count: int = 0
    latest_filing_sentiment: str = "neutral"


class CodalFilingItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_filing_id: str
    symbol: str
    title: str
    filing_type: str
    filing_type_fa: str
    sentiment: str
    sentiment_fa: str
    impact_score: float
    summary_fa: str
    published_at: str
    url: str | None = None


class CommodityItem(BaseModel):
    name_fa: str
    symbol: str
    category: str
    price: float
    unit: str
    change_pct: float
    change_value: float
    impact_fa: str
    beneficiary_sectors: list[str] = []


class MacroDashboardResponse(BaseModel):
    status: str = "BLOCKED"
    reason_fa: str | None = None
    provider_name: str | None = None
    nima_usd_rate: float | None
    nima_usd_change_pct: float | None
    free_market_usd_rate: float | None
    gap_nima_free_pct: float | None
    interbank_interest_rate: float | None
    commodities: list[CommodityItem]
    macro_regime_fa: str
    last_updated_jalali: str | None


# ==========================================
# 7. Closed Trade History & Real Learning Schemas
# ==========================================

class TradeExecutionTimelineItem(BaseModel):
    id: str
    event_type: str
    timestamp: str
    price: float
    quantity: int
    portion_pct: float
    fees: float
    notes_fa: str


class TradePostMortemResponse(BaseModel):
    entry_efficiency: float
    exit_efficiency: float
    process_quality_score: float
    outcome_vs_process_type: str
    what_worked_fa: str
    what_failed_fa: str
    entry_quality_fa: str
    exit_quality_fa: str
    position_sizing_quality_fa: str
    execution_quality_fa: str
    risk_compliance_fa: str
    unexpected_market_behavior_fa: str


class StructuredLessonResponse(BaseModel):
    id: str
    trade_id: str
    category: str
    finding_fa: str
    evidence_data: dict
    confidence_pct: float
    action_candidate_fa: str
    requires_validation: bool
    created_at: str


class ClosedTradeResponse(BaseModel):
    id: str
    portfolio_id: str
    position_id: str | None
    symbol: str
    company_name: str
    sector: str
    strategy_id: str
    strategy_name_fa: str
    strategy_version: str
    model_version: str
    risk_policy_version: str
    market_rules_version: str
    dataset_version: str
    signal_id: str | None
    decision_id: str | None
    decision_method: str
    opened_at: str
    closed_at: str
    holding_sessions: int
    holding_duration_hours: float
    planned_entry: float
    avg_entry_price: float
    avg_exit_price: float
    total_quantity: int
    gross_buy_value: float
    gross_sell_value: float
    entry_fees: float
    exit_fees: float
    tax: float
    slippage_cost: float
    total_cost: float
    gross_pnl: float
    net_pnl: float
    net_pnl_tomans: float
    net_return_pct: float
    initial_risk_amount: float
    initial_risk_pct_nav: float
    realized_R: float
    MFE: float
    MAE: float
    initial_stop: float
    final_stop: float
    target1: float
    target2: float
    exit_reason: str
    exit_reason_fa: str
    exit_reason_detail: str
    market_regime_at_entry: str
    market_regime_at_exit: str
    portfolio_nav_at_entry: float
    portfolio_nav_at_exit: float
    position_weight_at_entry: float
    outcome_status: str
    outcome_status_fa: str
    reason_fa: str
    lesson_fa: str


class ClosedTradeDetailResponse(ClosedTradeResponse):
    timeline: list[TradeExecutionTimelineItem] = []
    post_mortem: TradePostMortemResponse | None = None
    chart_bars: list[dict] = []


class HistorySummaryResponse(BaseModel):
    total_closed_trades: int
    wins: int
    losses: int
    breakevens: int
    win_rate_pct: float
    net_pnl_rials: float
    net_pnl_tomans: float
    gross_pnl_rials: float
    avg_return_pct: float
    avg_R: float
    median_R: float
    profit_factor: float
    expectancy_R: float
    avg_holding_sessions: float
    best_trade_return_pct: float
    best_trade_symbol: str
    worst_trade_return_pct: float
    worst_trade_symbol: str
    total_fees_paid_tomans: float
    total_slippage_cost_tomans: float


class PaginatedClosedTradesResponse(BaseModel):
    items: list[ClosedTradeResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    summary: HistorySummaryResponse


class StrategyPerformanceDetail(BaseModel):
    strategy_id: str
    strategy_name_fa: str
    strategy_version: str
    closed_trades: int
    wins: int
    losses: int
    win_rate_pct: float | None
    net_expectancy: float | None
    avg_R: float | None
    median_R: float | None
    profit_factor: float | None
    avg_win_R: float | None
    avg_loss_R: float | None
    max_consecutive_losses: int
    max_consecutive_wins: int
    avg_MFE: float | None
    avg_MAE: float | None
    avg_holding_sessions: float | None
    drawdown_contribution_pct: float | None
    total_fees_tomans: float
    total_slippage_tomans: float
    sample_sufficiency: str
    sample_sufficiency_fa: str
    health_score: float | None
    health_status: str
    warnings: list[str] = []


class ExperimentProposalResponse(BaseModel):
    id: str
    source_lesson_id: str | None
    strategy_key: str
    strategy_name_fa: str
    champion_version: str
    challenger_version: str
    status: str
    status_fa: str
    hypothesis_fa: str
    parameter_changes: dict
    backtest_metrics: dict
    oos_metrics: dict
    sample_sufficiency: str
    rejection_reason_fa: str | None
    approved_by: str | None
    promoted_at: str | None
    created_at: str


class LearningDashboardResponse(BaseModel):
    total_closed_trades: int
    validated_strategies_count: int
    strategies_under_review_count: int
    active_challengers_count: int
    pending_experiments_count: int
    rejected_experiments_count: int
    data_sufficiency_status: str
    champion_status_summary: str
    overall_health_score: float | None
    tuning_stage: str
    tuning_stage_fa: str
    minimum_closed_trades_for_tuning: int
    observed_market_regimes: int
    next_action_fa: str
    automatic_promotion_enabled: bool = False
