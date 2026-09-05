"""Application configuration system loading YAML and environment variables."""
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
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
    adapter: str = "public_cdn_json"
    docs_url: str = "https://cdn.tsetmc.com"
    base_url: str = "https://cdn.tsetmc.com"
    max_concurrency: int = 4
    request_timeout_seconds: int = 15
    retry_attempts: int = 2
    backoff_initial_seconds: int = 1
    max_response_bytes: int = 8_000_000


class SedraConfig(BaseModel):
    enabled: bool = False
    adapter: str = "official_rest"
    enable_when_credentials_available: bool = True
    base_url: str = "https://my.codal.ir/api"


class TindexConfig(BaseModel):
    enabled: bool = False
    adapter: str = "documented_rest"
    base_url: str = "https://tindex.app"
    request_timeout_seconds: int = 10
    max_response_bytes: int = 4_000_000
    minimum_request_interval_seconds: int = 60
    daily_success_limit: int = 100
    overview_refresh_seconds: int = 300
    screener_refresh_seconds: int = 3600


class BourseViewConfig(BaseModel):
    enabled: bool = False
    adapter: str = "contract_pending"
    base_url: str = "https://api.bourseview.com"


class SourceArenaConfig(BaseModel):
    enabled: bool = False
    adapter: str = "documented_rest"
    base_url: str = "https://apis.sourcearena.ir"
    request_timeout_seconds: int = 10
    max_response_bytes: int = 8_000_000


class BrsApiConfig(BaseModel):
    enabled: bool = False
    adapter: str = "documented_rest"
    base_url: str = "https://api.brsapi.ir"
    request_timeout_seconds: int = 15
    max_response_bytes: int = 12_000_000
    # The provider documents 300 requests per five minutes. One request every
    # second is the exact ceiling; using five seconds leaves a safety margin.
    minimum_request_interval_seconds: int = 5


class CadenceConfig(BaseModel):
    instrument_master_minutes: int = 1440
    market_watch_seconds: int = 60
    orderbook_seconds: int = 10
    client_type_seconds: int = 30
    codal_poll_seconds: int = 120
    eod_reconcile_after_session_minutes: int = 20


class QualityConfig(BaseModel):
    critical_market_stale_seconds: int = 60
    fundamental_receipt_stale_seconds: int = 86_400
    minimum_expected_equity_universe: int = 900
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
    min_independent_technical_families: int = 3
    min_bullish_strategies: int = 4
    min_family_vote: float = 0.60


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

    # Authentication and browser boundary
    session_secret: str = Field(default="development-only-change-me", alias="SESSION_SECRET")
    session_ttl_minutes: int = Field(default=43_200, alias="SESSION_TTL_MINUTES")
    radar_admin_user: str = Field(default="admin", alias="RADAR_ADMIN_USER")
    radar_admin_password: str = Field(default="development-only-change-me", alias="RADAR_ADMIN_PASSWORD")
    cookie_secure: bool = Field(default=True, alias="COOKIE_SECURE")
    cors_origins: str = Field(
        default="http://127.0.0.1:3742,http://localhost:3742",
        alias="CORS_ORIGINS",
    )
    tsetmc_api_username: str | None = Field(default=None, alias="TSETMC_API_USERNAME")
    tsetmc_api_password: str | None = Field(default=None, alias="TSETMC_API_PASSWORD")
    tindex_api_token: str | None = Field(default=None, alias="TINDEX_API_TOKEN")
    bourseview_api_token: str | None = Field(default=None, alias="BOURSEVIEW_API_TOKEN")
    sourcearena_api_token: str | None = Field(default=None, alias="SOURCEARENA_API_TOKEN")
    brsapi_api_key: str | None = Field(default=None, alias="BRSAPI_API_KEY")
    persianapi_token: str | None = Field(default=None, alias="PERSIANAPI_TOKEN")
    api_ir_token: str | None = Field(default=None, alias="API_IR_TOKEN")
    data_http_proxy: str | None = Field(default=None, alias="DATA_HTTP_PROXY")
    data_http_trust_env: bool = Field(default=False, alias="DATA_HTTP_TRUST_ENV")

    # Data provenance and automated paper-trading controls
    market_data_mode: str = Field(default="official", alias="MARKET_DATA_MODE")
    auto_paper_trading_enabled: bool = Field(default=False, alias="AUTO_PAPER_TRADING_ENABLED")
    market_data_scheduler_enabled: bool = Field(default=True, alias="MARKET_DATA_SCHEDULER_ENABLED")
    tsetmc_market_hours_enforced: bool = Field(default=True, alias="TSETMC_MARKET_HOURS_ENFORCED")
    history_backfill_enabled: bool = Field(default=True, alias="HISTORY_BACKFILL_ENABLED")
    history_backfill_interval_seconds: int = Field(default=300, alias="HISTORY_BACKFILL_INTERVAL_SECONDS")
    tsetmc_network_cooldown_seconds: int = Field(default=300, alias="TSETMC_NETWORK_COOLDOWN_SECONDS")
    tsetmc_block_cooldown_seconds: int = Field(default=7_200, alias="TSETMC_BLOCK_COOLDOWN_SECONDS")
    iran_market_holidays: str = Field(default="", alias="IRAN_MARKET_HOLIDAYS")
    minimum_fundamental_sources: int = Field(default=2, alias="MINIMUM_FUNDAMENTAL_SOURCES")
    initial_portfolio_cash_rials: float = Field(
        default=100_000_000_000.0,
        alias="INITIAL_PORTFOLIO_CASH_RIALS",
    )

    # Trading Mode Safety
    trading_mode: str = Field(default="paper", alias="TRADING_MODE")
    live_trading_enabled: bool = Field(default=False, alias="LIVE_TRADING_ENABLED")
    risk_kill_switch_armed: bool = Field(default=True, alias="RISK_KILL_SWITCH_ARMED")
    broker_adapter: str | None = Field(default=None, alias="BROKER_ADAPTER")
    broker_credentials: str | None = Field(default=None, alias="BROKER_CREDENTIALS")

    # Sub-configurations
    tsetmc: TsetmcConfig = Field(default_factory=TsetmcConfig)
    sedra: SedraConfig = Field(default_factory=SedraConfig)
    tindex: TindexConfig = Field(default_factory=TindexConfig)
    bourseview: BourseViewConfig = Field(default_factory=BourseViewConfig)
    sourcearena: SourceArenaConfig = Field(default_factory=SourceArenaConfig)
    brsapi: BrsApiConfig = Field(default_factory=BrsApiConfig)
    cadence: CadenceConfig = Field(default_factory=CadenceConfig)
    quality: QualityConfig = Field(default_factory=QualityConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    strategy_engine: StrategyEngineConfig = Field(default_factory=StrategyEngineConfig)

    @property
    def allowed_cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def validate_runtime_security(self) -> None:
        """Fail closed when a production process is configured unsafely."""
        if self.trading_mode != "paper":
            required_live_gates = (
                self.live_trading_enabled,
                bool(self.broker_adapter),
                bool(self.broker_credentials),
                self.risk_kill_switch_armed,
            )
            if not all(required_live_gates):
                raise RuntimeError("Live trading requested without all five mandatory safety gates.")

        if self.app_env.lower() != "production":
            return

        known_session_secrets = {
            "development-only-change-me",
            "iran_market_radar_ultra_secure_jwt_secret_key_2026_super_long",
            "radar_institutional_grade_jwt_secret_key_2026_iran_stock_market_secure_7788",
        }
        known_admin_passwords = {"development-only-change-me", "radar2026", "admin", "password"}
        failures: list[str] = []
        if len(self.session_secret) < 32 or self.session_secret in known_session_secrets:
            failures.append("SESSION_SECRET must be a unique secret of at least 32 characters")
        if len(self.radar_admin_password) < 14 or self.radar_admin_password in known_admin_passwords:
            failures.append("RADAR_ADMIN_PASSWORD must be a unique password of at least 14 characters")
        if "*" in self.allowed_cors_origins:
            failures.append("CORS_ORIGINS cannot contain '*' when credentials are enabled")
        if self.market_data_mode != "official":
            failures.append("MARKET_DATA_MODE must be 'official' in production")
        if self.minimum_fundamental_sources < 2:
            failures.append("MINIMUM_FUNDAMENTAL_SOURCES must be at least 2 in production")
        if urlparse(self.database_url).hostname in {None, "localhost", "127.0.0.1"}:
            # Local production is valid, but it must still use an explicit non-SQLite database.
            if self.database_url.startswith("sqlite"):
                failures.append("production DATABASE_URL cannot use SQLite")
        if failures:
            raise RuntimeError("Unsafe production configuration: " + "; ".join(failures))


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
        if "tindex" in ingestion_yaml["data_sources"]:
            kwargs["tindex"] = TindexConfig(**ingestion_yaml["data_sources"]["tindex"])
        if "bourseview" in ingestion_yaml["data_sources"]:
            kwargs["bourseview"] = BourseViewConfig(**ingestion_yaml["data_sources"]["bourseview"])
        if "sourcearena" in ingestion_yaml["data_sources"]:
            kwargs["sourcearena"] = SourceArenaConfig(**ingestion_yaml["data_sources"]["sourcearena"])
        if "brsapi" in ingestion_yaml["data_sources"]:
            kwargs["brsapi"] = BrsApiConfig(**ingestion_yaml["data_sources"]["brsapi"])

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
