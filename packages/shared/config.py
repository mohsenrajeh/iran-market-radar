"""Application configuration system loading YAML and environment variables."""
import os
from pathlib import Path
from typing import Any
import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _load_yaml(file_path: Path) -> dict[str, Any]:
    if not file_path.exists():
        return {}
    with open(file_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"


class TsetmcConfig(BaseModel):
    enabled: bool = True
    adapter: str = "official_rest"
    docs_url: str = "https://api.tsetmc.com/docs/"
    base_url: str = "https://cdn.tsetmc.com/api"
    max_concurrency: int = 4
    request_timeout_seconds: int = 3
    retry_attempts: int = 2
    backoff_initial_seconds: int = 1


class SedraConfig(BaseModel):
    enabled: bool = False
    adapter: str = "official_rest"
    enable_when_credentials_available: bool = True
    base_url: str = "https://my.codal.ir/api"


class CadenceConfig(BaseModel):
    instrument_master_minutes: int = 1440
    market_watch_seconds: int = 10
    orderbook_seconds: int = 10
    client_type_seconds: int = 30
    codal_poll_seconds: int = 120
    eod_reconcile_after_session_minutes: int = 20


class QualityConfig(BaseModel):
    critical_market_stale_seconds: int = 60
    max_duplicate_ratio: float = 0.001
    minimum_symbol_completeness_ratio: float = 0.98


class RiskConfig(BaseModel):
    risk_per_trade_pct_nav: float = 0.005
    max_position_pct_nav: float = 0.10
    max_sector_pct_nav: float = 0.25
    max_open_positions: int = 10
    max_gross_exposure_pct_nav: float = 0.80
    max_daily_new_risk_pct_nav: float = 0.02
    max_drawdown_kill_switch_pct: float = 0.12
    min_liquidity_score: float = 60.0
    max_participation_pct_of_expected_volume: float = 0.05
    stale_data_block_seconds: int = 60


class ExecutionConfig(BaseModel):
    default_order_type: str = "limit"
    max_chase_atr_fraction: float = 0.25
    conservative_queue_fill: bool = True
    allow_partial_fill: bool = True
    entry_expiry_sessions: int = 2


class StrategyEngineConfig(BaseModel):
    default_horizons: list[str] = ["1d", "3d", "5d", "10d", "20d"]
    actionable_horizons: list[str] = ["3d", "5d", "10d"]
    min_data_quality_score: float = 85.0
    min_history_sessions: int = 260
    min_opportunity_score: float = 70.0
    min_confidence: float = 55.0
    require_positive_expected_edge_after_costs: bool = True
    max_published_per_horizon: int = 25


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Iran Market Radar"
    app_env: str = Field(default="development", alias="APP_ENV")
    app_port: int = Field(default=8742, alias="APP_PORT")
    web_port: int = Field(default=3742, alias="WEB_PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///./iran_market_radar.db",
        alias="DATABASE_URL"
    )
    database_sync_url: str = Field(
        default="sqlite:///./iran_market_radar.db",
        alias="DATABASE_SYNC_URL"
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    # Trading Mode Safety
    trading_mode: str = Field(default="paper", alias="TRADING_MODE")
    live_trading_enabled: bool = Field(default=False, alias="LIVE_TRADING_ENABLED")
    risk_kill_switch_armed: bool = Field(default=True, alias="RISK_KILL_SWITCH_ARMED")

    # Sub-configurations
    tsetmc: TsetmcConfig = Field(default_factory=TsetmcConfig)
    sedra: SedraConfig = Field(default_factory=SedraConfig)
    cadence: CadenceConfig = Field(default_factory=CadenceConfig)
    quality: QualityConfig = Field(default_factory=QualityConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    strategy_engine: StrategyEngineConfig = Field(default_factory=StrategyEngineConfig)


def get_settings() -> Settings:
    """Instantiates Settings and merges YAML configurations."""
    ingestion_yaml = _load_yaml(CONFIG_DIR / "data_ingestion_defaults.yaml")
    risk_yaml = _load_yaml(CONFIG_DIR / "risk_defaults.yaml")
    strategy_yaml = _load_yaml(CONFIG_DIR / "strategy_defaults.yaml")

    kwargs: dict[str, Any] = {}

    if "data_sources" in ingestion_yaml:
        if "tsetmc" in ingestion_yaml["data_sources"]:
            kwargs["tsetmc"] = TsetmcConfig(**ingestion_yaml["data_sources"]["tsetmc"])
        if "sedra" in ingestion_yaml["data_sources"]:
            kwargs["sedra"] = SedraConfig(**ingestion_yaml["data_sources"]["sedra"])

    if "cadence" in ingestion_yaml:
        kwargs["cadence"] = CadenceConfig(**ingestion_yaml["cadence"])

    if "quality" in ingestion_yaml:
        kwargs["quality"] = QualityConfig(**ingestion_yaml["quality"])

    if "risk" in risk_yaml:
        kwargs["risk"] = RiskConfig(**risk_yaml["risk"])

    if "execution" in risk_yaml:
        kwargs["execution"] = ExecutionConfig(**risk_yaml["execution"])

    if "strategy_engine" in strategy_yaml:
        engine_dict = strategy_yaml["strategy_engine"].copy()
        if "publication" in strategy_yaml:
            engine_dict.update(strategy_yaml["publication"])
        kwargs["strategy_engine"] = StrategyEngineConfig(**engine_dict)

    return Settings(**kwargs)


settings = get_settings()
