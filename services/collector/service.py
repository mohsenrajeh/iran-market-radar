"""Market Data Collection and Radar Execution Coordinator."""
import threading
from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo
from sqlalchemy import func
from sqlalchemy.orm import Session

from packages.data_adapters.fixtures import FIXTURE_SECTORS, FIXTURE_INSTRUMENTS, FixtureReplayAdapter
from packages.data_adapters.tindex import TindexAdapter
from packages.data_adapters.sourcearena import SourceArenaAdapter
from packages.data_adapters.brsapi import BrsApiAdapter
from packages.data_adapters.tsetmc_cdn_marketwatch import TsetmcCdnMarketWatchAdapter
from packages.data_adapters.codal_public import CodalPublicAdapter
import jdatetime
from packages.domain.models import (
    Sector, Instrument, EODBar, ClientTypeSnapshot, PublishedSignal, Portfolio,
    DataSourceReceipt, MarketSnapshot, MarketIndexSnapshot,
    MarketDataBatch, ReferenceMarketObservation, Filing, FundamentalSnapshot, BrokerOrder,
)
from packages.feature_engine.indicators import compute_symbol_features
from packages.feature_engine.regime import compute_market_regime_from_db
from packages.ml.calibration import SignalProbabilityCalibrator
from services.scorer.calibration_store import load_active_calibrator
from services.scorer.ensemble import assemble_published_signal
from packages.shared.datetime_utils import now_utc, to_utc_iso
from packages.shared.logger import logger
from packages.market_rules.trading_hours import get_market_session_state


_RADAR_SCAN_LOCK = threading.Lock()
from packages.shared.config import settings
from packages.shared.persian import normalize_persian_text
from packages.strategies.base import StrategyContext
from packages.strategies.registry import strategy_registry
from services.scorer.fundamental_gate import evaluate_fundamental_gate
from services.collector.quality import instrument_data_quality_score
from services.collector.reference_store import normalize_brsapi_row, persist_reference_batch
from services.collector.trusted_queries import (
    latest_trusted_market_snapshot,
    trusted_client_type_query,
    trusted_eod_query,
)


class TsetmcCircuitOpenError(RuntimeError):
    """A sanitized, paced upstream pause that callers may sleep through."""

    def __init__(self, message: str, *, retry_after_seconds: int) -> None:
        super().__init__(message)
        self.retry_after_seconds = max(1, int(retry_after_seconds))


class IngestionCoordinator:
    """Coordinates market data syncing, feature extraction, and opportunity scanning."""

    def __init__(self, db: Session):
        self.db = db
        if settings.market_data_mode == "fixture":
            if settings.app_env.lower() == "production":
                raise RuntimeError("Fixture market data is forbidden in production.")
            self.adapter = FixtureReplayAdapter(seed=42)
        elif settings.market_data_mode == "official":
            self.adapter = TsetmcCdnMarketWatchAdapter()
        else:
            raise RuntimeError(f"Unsupported MARKET_DATA_MODE: {settings.market_data_mode}")
        self.calibrator = SignalProbabilityCalibrator(method="isotonic")

    def _record_receipt(
        self,
        *,
        source_key: str,
        source_kind: str,
        provider_name: str,
        status: str,
        record_count: int = 0,
        error_message: str | None = None,
        schema_version: str = "unverified",
        metadata: dict | None = None,
        mode: str | None = None,
        provider_url: str | None = None,
    ) -> None:
        receipt = (
            self.db.query(DataSourceReceipt)
            .filter(DataSourceReceipt.source_key == source_key)
            .first()
        )
        if receipt is None:
            receipt = DataSourceReceipt(
                source_key=source_key,
                source_kind=source_kind,
                provider_name=provider_name,
                provider_url=provider_url or (settings.tsetmc.base_url if source_key.startswith("tsetmc_") else None),
            )
            self.db.add(receipt)
        receipt.source_kind = source_kind
        receipt.provider_name = provider_name
        if provider_url is not None:
            receipt.provider_url = provider_url
        receipt.mode = mode or settings.market_data_mode
        receipt.status = status
        receipt.record_count = record_count
        receipt.last_attempt_at = now_utc()
        receipt.error_message = (error_message or "")[:512] or None
        receipt.schema_version = schema_version
        receipt.metadata_json = metadata or {}
        if status == "HEALTHY":
            receipt.last_success_at = now_utc()
        self.db.commit()

    @staticmethod
    def _market_source_timestamp(item: dict) -> datetime | None:
        """Parse provider date/time; never substitute local ingestion time for source time."""
        raw_date = str(item.get("DEven") or item.get("dEven") or "").replace("-", "")
        raw_time = str(item.get("HEven") or item.get("hEven") or "").zfill(6)
        if len(raw_date) != 8 or not raw_date.isdigit() or len(raw_time) != 6 or not raw_time.isdigit():
            return None
        try:
            local_dt = datetime.strptime(raw_date + raw_time, "%Y%m%d%H%M%S").replace(
                tzinfo=ZoneInfo("Asia/Tehran")
            )
            return local_dt.astimezone(timezone.utc)
        except ValueError:
            return None

    async def sync_market_watch(self) -> int:
        if settings.market_data_mode == "official":
            raise RuntimeError("Retired provider path: use sync_cdn_market_watch only.")
        """Persist canonical official intraday snapshots with source timestamps."""
        if settings.market_data_mode != "official":
            raise RuntimeError("Market watch sync is official-mode only.")
        rows = await self.adapter.fetch_market_watch()
        if not rows:
            self._record_receipt(
                source_key="tsetmc_market_watch",
                source_kind="market",
                provider_name="TSETMC",
                status="UNAVAILABLE",
                error_message="No provider rows returned (network/VPN, endpoint, or schema failure).",
            )
            raise RuntimeError("Official TSETMC market watch is unavailable; sync failed closed.")

        thresholds = await self.adapter.fetch_thresholds()
        if not thresholds:
            self._record_receipt(
                source_key="tsetmc_market_watch",
                source_kind="market",
                provider_name="TSETMC",
                status="UNAVAILABLE",
                error_message="Official price-limit Threshold service returned no verified rows.",
            )
            raise RuntimeError("Official TSETMC price thresholds are unavailable; sync failed closed.")
        instruments = {
            str(inst.source_instrument_code): inst
            for inst in self.db.query(Instrument).filter(Instrument.is_active == True).all()
        }
        accepted = 0
        missing_source_timestamp = 0
        for item in rows:
            if not isinstance(item, dict):
                continue
            source_code = str(item.get("InsCode") or item.get("insCode") or "")
            inst = instruments.get(source_code)
            source_timestamp = self._market_source_timestamp(item)
            threshold = thresholds.get(source_code)
            if inst is None or source_timestamp is None or threshold is None:
                missing_source_timestamp += int(inst is not None and source_timestamp is None)
                continue
            last_price = float(item.get("PDrCotVal") or item.get("pDrCotVal") or 0)
            close_price = float(item.get("PClosing") or item.get("pClosing") or 0)
            yesterday = float(item.get("PriceYesterday") or item.get("priceYesterday") or 0)
            high = float(item.get("PriceMax") or item.get("priceMax") or 0)
            low = float(item.get("PriceMin") or item.get("priceMin") or 0)
            if min(last_price, close_price, yesterday, high, low) <= 0 or high < low:
                continue
            self.db.add(MarketSnapshot(
                instrument_id=inst.id,
                source_timestamp=source_timestamp,
                last_price=last_price,
                close_price=close_price,
                high_price=high,
                low_price=low,
                yesterday_price=yesterday,
                volume=max(0, int(item.get("QTotTran5J") or item.get("qTotTran5J") or 0)),
                value=max(0.0, float(item.get("QTotCap") or item.get("qTotCap") or 0)),
                trade_count=max(0, int(item.get("ZTotTran") or item.get("zTotTran") or 0)),
                allowed_min=threshold[0],
                allowed_max=threshold[1],
                state=str(item.get("Last") or item.get("last") or "UNKNOWN"),
                available_at=source_timestamp,
                ingested_at=now_utc(),
            ))
            accepted += 1

        if not accepted:
            self.db.rollback()
            self._record_receipt(
                source_key="tsetmc_market_watch",
                source_kind="market",
                provider_name="TSETMC",
                status="SCHEMA_ERROR",
                record_count=0,
                error_message="Rows did not match the verified canonical market-watch schema.",
                metadata={"provider_rows": len(rows), "missing_source_timestamp": missing_source_timestamp},
            )
            raise RuntimeError("TSETMC market watch schema could not be verified; sync failed closed.")
        self.db.commit()
        self._record_receipt(
            source_key="tsetmc_market_watch",
            source_kind="market",
            provider_name="TSETMC",
            status="HEALTHY",
            record_count=accepted,
            schema_version="tsetmc-market-watch-canonical-v1",
            metadata={"provider_rows": len(rows), "missing_source_timestamp": missing_source_timestamp},
        )
        return accepted

    async def sync_indices(self) -> int:
        if settings.market_data_mode == "official":
            raise RuntimeError("Retired provider path: use sync_cdn_market_watch only.")
        """Persist official TSE and IFB index observations without fallback values."""
        if settings.market_data_mode != "official":
            raise RuntimeError("Index sync is official-mode only.")
        rows: list[dict] = []
        rows.extend(await self.adapter.fetch_indices(flow=1))
        rows.extend(await self.adapter.fetch_indices(flow=2))
        accepted = 0
        for item in rows:
            source_timestamp = self._market_source_timestamp(item)
            code = str(item.get("InsCode") or "")
            name = normalize_persian_text(str(item.get("LVal30") or ""))
            value = float(item.get("XDrNivJIdx004") or 0)
            change_pct = float(item.get("XVarIdxJRfV") or 0)
            if not source_timestamp or not code or not name or value <= 0:
                continue
            previous = value / (1.0 + change_pct / 100.0) if change_pct > -100 else value
            existing = self.db.query(MarketIndexSnapshot).filter(
                MarketIndexSnapshot.source_index_code == code,
                MarketIndexSnapshot.source_timestamp == source_timestamp,
            ).first()
            if existing:
                continue
            self.db.add(MarketIndexSnapshot(
                source_index_code=code,
                name_fa=name,
                source_timestamp=source_timestamp,
                value=value,
                change_pct=change_pct,
                change_value=value - previous,
                advancers=max(0, int(item.get("ZValHauIbs") or 0)),
                decliners=max(0, int(item.get("ZValBaiIbs") or 0)),
                unchanged=max(0, int(item.get("ZValIchgIbs") or 0)),
                total_constituents=max(0, int(item.get("ZTotValIbs") or 0)),
            ))
            accepted += 1
        if not accepted:
            self.db.rollback()
            self._record_receipt(
                source_key="tsetmc_indices", source_kind="market", provider_name="TSETMC",
                status="SCHEMA_ERROR" if rows else "UNAVAILABLE", record_count=0,
                error_message="No canonical index rows were accepted.",
            )
            raise RuntimeError("Official TSETMC indices are unavailable; sync failed closed.")
        self.db.commit()
        self._record_receipt(
            source_key="tsetmc_indices", source_kind="market", provider_name="TSETMC",
            status="HEALTHY", record_count=accepted, schema_version="tsetmc-index-last-data-v1",
        )
        return accepted

    async def bootstrap_if_empty(self, history_days: int = 260) -> dict:
        """Bootstrap an empty official database only from the public CDN feed."""
        if self.db.query(Instrument).count() > 0:
            return {"bootstrapped": False, "reason": "existing_database_preserved"}
        if settings.market_data_mode == "official":
            result = await self.sync_cdn_market_watch()
            return {
                "bootstrapped": not bool(result.get("skipped")),
                "provider": "TSETMC_PUBLIC_CDN",
                **result,
            }
        await self.sync_all_data(history_days=history_days)
        signals = self.run_radar_scan()
        return {"bootstrapped": True, "signals": len(signals)}

    def seed_initial_universe(self):
        """Initializes reference sectors and instruments in the database."""
        if settings.market_data_mode != "fixture":
            raise RuntimeError("Fixture universe seeding is disabled outside explicit fixture mode.")
        # 1. Sectors
        for sec in FIXTURE_SECTORS:
            existing_sec = self.db.query(Sector).filter(Sector.code == sec["code"]).first()
            if not existing_sec:
                new_sec = Sector(
                    id=f"sec_{sec['code']}",
                    code=sec["code"],
                    name_fa=sec["name_fa"],
                    description=sec["desc"],
                )
                self.db.add(new_sec)
        self.db.commit()

        # 2. Instruments
        for inst in FIXTURE_INSTRUMENTS:
            existing_inst = self.db.query(Instrument).filter(Instrument.ticker == inst["ticker"]).first()
            if not existing_inst:
                sec_obj = self.db.query(Sector).filter(Sector.code == inst["sector_code"]).first()
                new_inst = Instrument(
                    id=f"inst_{inst['ticker']}",
                    source_instrument_code=f"INS_{inst['ticker']}",
                    isin=inst["isin"],
                    ticker=inst["ticker"],
                    ticker_normalized=inst["ticker"],
                    name_fa=inst["name_fa"],
                    market="TSE",
                    board="بازار اول",
                    sector_id=sec_obj.id if sec_obj else None,
                    is_active=row["trade_eligible"],
                    base_volume=int(inst["base_price"] * 100),
                )
                self.db.add(new_inst)
        self.db.commit()

        # 3. Default Paper Portfolio
        existing_port = self.db.query(Portfolio).first()
        if not existing_port:
            port = Portfolio(
                id="port_default_paper",
                name="پورتفوی آزمایشی پیش‌فرض (۱۰ میلیارد تومان)",
                mode="paper",
                cash=settings.initial_portfolio_cash_rials,
                initial_cash=settings.initial_portfolio_cash_rials,
            )
            self.db.add(port)
            self.db.commit()

    async def sync_all_data(self, history_days: int = 260):
        """Backfill EOD and client-type history; never call this from a live UI refresh."""
        if settings.market_data_mode == "official":
            raise RuntimeError("Retired provider path: use CDN live sync and CDN backfill worker only.")
        if settings.market_data_mode == "fixture":
            self.seed_initial_universe()
        else:
            await self.sync_reference_universe()
        instruments = self.db.query(Instrument).filter(Instrument.is_active == True).all()
        eod_received = 0
        client_type_received = 0
        eod_symbols_received = 0
        client_type_symbols_received = 0

        if settings.market_data_mode == "official" and any(
            str(inst.source_instrument_code).startswith("INS_") for inst in instruments
        ):
            raise RuntimeError(
                "Database contains fixture instruments. Official sync refuses to mix simulated and authentic prices."
            )

        if settings.market_data_mode == "official":
            await self.sync_market_watch()
            await self.sync_indices()

        for inst in instruments:
            existing_bar_dates = {
                r[0] for r in self.db.query(EODBar.trading_date).filter(EODBar.instrument_id == inst.id).all()
            }
            existing_ct_dates = {
                r[0] for r in self.db.query(ClientTypeSnapshot.trading_date).filter(ClientTypeSnapshot.instrument_id == inst.id).all()
            }

            source_code = inst.source_instrument_code if settings.market_data_mode == "official" else inst.ticker
            bars_data = await self.adapter.fetch_eod_history(source_code, days=history_days)
            eod_received += len(bars_data)
            eod_symbols_received += int(bool(bars_data))
            if settings.market_data_mode == "official" and not bars_data:
                logger.warning("No official EOD history returned for %s; symbol skipped.", inst.ticker)
                continue
            for b in bars_data:
                b_date = date.fromisoformat(b["trading_date"])
                if b_date not in existing_bar_dates:
                    new_bar = EODBar(
                        id=f"eod_{inst.ticker}_{b['trading_date']}",
                        instrument_id=inst.id,
                        trading_date=b_date,
                        open=b["open"],
                        high=b["high"],
                        low=b["low"],
                        close=b["close"],
                        last=b["last"],
                        yesterday_price=b["yesterday_price"],
                        volume=b["volume"],
                        value=b["value"],
                        trade_count=b["trade_count"],
                        allowed_min=b.get("allowed_min", int(b["yesterday_price"] * 0.95) if b["yesterday_price"] else int(b["close"] * 0.95)),
                        allowed_max=b.get("allowed_max", int(b["yesterday_price"] * 1.05) if b["yesterday_price"] else int(b["close"] * 1.05)),
                        available_at=datetime.combine(
                            b_date, time(13, 0), tzinfo=ZoneInfo("Asia/Tehran")
                        ).astimezone(timezone.utc),
                        ingested_at=now_utc(),
                    )
                    self.db.add(new_bar)

            # Sync Client Types
            ct_data = await self.adapter.fetch_client_type_history(source_code, days=history_days)
            client_type_received += len(ct_data)
            client_type_symbols_received += int(bool(ct_data))
            for ct in ct_data:
                ct_date = date.fromisoformat(ct["trading_date"])
                if ct_date not in existing_ct_dates:
                    new_ct = ClientTypeSnapshot(
                        id=f"ct_{inst.ticker}_{ct['trading_date']}",
                        instrument_id=inst.id,
                        trading_date=ct_date,
                        real_buy_count=ct["real_buy_count"],
                        real_buy_volume=ct["real_buy_volume"],
                        real_buy_value=ct["real_buy_value"],
                        real_sell_count=ct["real_sell_count"],
                        real_sell_volume=ct["real_sell_volume"],
                        real_sell_value=ct["real_sell_value"],
                        legal_buy_count=ct["legal_buy_count"],
                        legal_buy_volume=ct["legal_buy_volume"],
                        legal_buy_value=ct["legal_buy_value"],
                        legal_sell_count=ct["legal_sell_count"],
                        legal_sell_volume=ct["legal_sell_volume"],
                        legal_sell_value=ct["legal_sell_value"],
                        available_at=datetime.combine(
                            ct_date, time(13, 0), tzinfo=ZoneInfo("Asia/Tehran")
                        ).astimezone(timezone.utc),
                    )
                    self.db.add(new_ct)

            self.db.commit()
        if settings.market_data_mode == "official":
            expected_symbols = len(instruments)
            eod_completeness = eod_symbols_received / expected_symbols if expected_symbols else 0.0
            client_completeness = client_type_symbols_received / expected_symbols if expected_symbols else 0.0
            eod_status = "HEALTHY" if (
                eod_received and eod_completeness >= settings.quality.minimum_symbol_completeness_ratio
            ) else ("DEGRADED" if eod_received else "UNAVAILABLE")
            client_status = "HEALTHY" if (
                client_type_received and client_completeness >= settings.quality.minimum_symbol_completeness_ratio
            ) else ("DEGRADED" if client_type_received else "UNAVAILABLE")
            self._record_receipt(
                source_key="tsetmc_eod",
                source_kind="market",
                provider_name="TSETMC",
                status=eod_status,
                record_count=eod_received,
                schema_version="tsetmc-inst-trade-v1" if eod_received else "unverified",
                error_message=None if eod_status == "HEALTHY" else "Official InstTrade universe completeness is below the configured threshold.",
                metadata={"symbols_with_rows": eod_symbols_received, "expected_symbols": expected_symbols, "completeness_ratio": eod_completeness},
            )
            self._record_receipt(
                source_key="tsetmc_client_type",
                source_kind="market",
                provider_name="TSETMC",
                status=client_status,
                record_count=client_type_received,
                schema_version="tsetmc-client-type-by-ins-v1" if client_type_received else "unverified",
                error_message=None if client_status == "HEALTHY" else "Official client-type universe completeness is below the configured threshold.",
                metadata={"symbols_with_rows": client_type_symbols_received, "expected_symbols": expected_symbols, "completeness_ratio": client_completeness},
            )
            if eod_status != "HEALTHY" or client_status != "HEALTHY":
                raise RuntimeError("Official TSETMC historical universe is incomplete; sync failed closed.")
        logger.info("Market data synchronization completed.")

    async def sync_reference_universe(self) -> int:
        """Load the official instrument master only when no active universe exists."""
        raise RuntimeError("Retired provider path: the CDN market watch is the instrument universe.")
        if settings.market_data_mode != "official":
            return 0
        if self.db.query(Instrument).filter(Instrument.is_active == True).count() > 0:
            return 0
        master = await self.adapter.fetch_instrument_master()
        if not master:
            self._record_receipt(
                source_key="tsetmc_instrument_master",
                source_kind="market",
                provider_name="TSETMC",
                status="AUTH_ERROR" if getattr(self.adapter, "last_error_code", None) in {-102, -103, -104, -107} else "UNAVAILABLE",
                error_message=self.adapter.last_error or "Official instrument master returned no rows.",
                metadata={"api_error_code": getattr(self.adapter, "last_error_code", None)},
            )
            raise RuntimeError("Official TSETMC instrument master is unavailable; sync failed closed.")
        created = 0
        for item in master:
            instrument_id = f"inst_{item['source_instrument_code']}"
            if self.db.query(Instrument).filter(Instrument.id == instrument_id).first():
                continue
            self.db.add(Instrument(
                id=instrument_id,
                source_instrument_code=item["source_instrument_code"],
                isin=item.get("isin") or None,
                ticker=item["ticker"],
                ticker_normalized=item["ticker_normalized"],
                name_fa=item["name_fa"],
                market=item["market"],
                board=item.get("board") or "",
                base_volume=item.get("base_volume") or 1,
                is_active=True,
            ))
            created += 1
        self.db.commit()
        return created

    async def sync_reference_fallback(self, *, official_error: str) -> dict[str, Any]:
        raise RuntimeError("Provider failover is disabled; only TSETMC public CDN is allowed.")
        """Try configured reference feeds without ever making them trade-eligible."""
        providers: list[str] = []
        configured: list[str] = []
        previous_reference_count = 0
        tindex_crawl_attempted = False
        tindex_cooldown_remaining_seconds = 0
        tindex_refresh_action = "not_configured"

        tindex = TindexAdapter()
        if tindex.configured:
            configured.append("Tindex")
            overview_receipt = self.db.query(DataSourceReceipt).filter(
                DataSourceReceipt.source_key == "tindex_market_overview_crosscheck"
            ).first()
            screener_receipt = self.db.query(DataSourceReceipt).filter(
                DataSourceReceipt.source_key == "tindex_symbol_screener_reference"
            ).first()
            overview_meta = (overview_receipt.metadata_json or {}) if overview_receipt else {}
            screener_meta = (screener_receipt.metadata_json or {}) if screener_receipt else {}
            previous_reference_count = int(screener_receipt.record_count if screener_receipt else 0)

            def age_seconds(receipt: DataSourceReceipt | None) -> float | None:
                value = receipt.last_success_at if receipt else None
                if value and value.tzinfo is None:
                    value = value.replace(tzinfo=timezone.utc)
                return (now_utc() - value.astimezone(timezone.utc)).total_seconds() if value else None

            overview_age = age_seconds(overview_receipt)
            successful_receipts = [
                receipt for receipt in (overview_receipt, screener_receipt)
                if receipt and receipt.last_success_at
            ]
            last_tindex_age = min(
                (age_seconds(receipt) for receipt in successful_receipts),
                default=None,
            )
            within_local_window = bool(
                last_tindex_age is not None
                and last_tindex_age < settings.tindex.minimum_request_interval_seconds
            )
            if within_local_window and last_tindex_age is not None:
                tindex_cooldown_remaining_seconds = max(
                    1,
                    int(settings.tindex.minimum_request_interval_seconds - last_tindex_age + 0.999),
                )
                tindex_refresh_action = "quota_cooldown"
            cached_overview_valid = bool(
                overview_receipt
                and overview_receipt.status == "HEALTHY"
                and overview_receipt.mode == "reference_only"
                and overview_meta.get("indices")
            )
            overview_due = bool(
                not cached_overview_valid
                or overview_age is None
                or overview_age >= settings.tindex.overview_refresh_seconds
            )

            # An incomplete/resumable screener generation must not be starved
            # by the shorter overview refresh interval.  Only one request is
            # sent per quota window; finish the universe first, then refresh
            # the small overview payload on a later cycle.
            crawl_complete_before_fetch = bool(screener_meta.get("completed"))
            refresh_in_progress_before_fetch = bool(screener_meta.get("refresh_in_progress"))
            screener_age_before_fetch = age_seconds(screener_receipt)
            crawl_refresh_due_before_fetch = bool(
                crawl_complete_before_fetch
                and screener_age_before_fetch is not None
                and screener_age_before_fetch >= settings.tindex.screener_refresh_seconds
            )
            screener_due = bool(
                not crawl_complete_before_fetch
                or refresh_in_progress_before_fetch
                or crawl_refresh_due_before_fetch
            )
            fetch_overview_now = bool(overview_due and not screener_due)

            overview = overview_meta if cached_overview_valid else None
            if not within_local_window and fetch_overview_now:
                overview = await tindex.fetch_market_overview()
                tindex_refresh_action = "overview_refreshed"
            indices = overview.get("indices") if isinstance(overview, dict) else None
            as_of = overview.get("as_of") if isinstance(overview, dict) else None
            valid_indices: list[dict[str, Any]] = []
            try:
                as_of_date = date.fromisoformat(str(as_of))
                age_days = (date.today() - as_of_date).days
            except (TypeError, ValueError):
                age_days = 10_000
            if isinstance(indices, list) and 0 <= age_days <= 7:
                for item in indices[:20]:
                    try:
                        value = float(item.get("value") or 0)
                        change_pct = float(item.get("change_percent", item.get("change_pct")) or 0)
                    except (AttributeError, TypeError, ValueError):
                        continue
                    if value <= 0:
                        continue
                    valid_indices.append({
                        "code": str(item.get("slug") or item.get("code") or item.get("name") or ""),
                        "name_fa": str(item.get("name") or item.get("name_fa") or item.get("slug") or "شاخص"),
                        "value": value,
                        "change_pct": change_pct,
                    })
            if not within_local_window and fetch_overview_now:
                tindex_status = "HEALTHY" if valid_indices else "UNAVAILABLE"
                self._record_receipt(
                    source_key="tindex_market_overview_crosscheck",
                    source_kind="market_reference",
                    provider_name="Tindex",
                    provider_url=settings.tindex.base_url,
                    status=tindex_status,
                    record_count=len(valid_indices),
                    error_message=None if valid_indices else (tindex.last_error or "Tindex freshness/schema validation failed."),
                    schema_version="tindex-market-overview-v1" if valid_indices else "unverified",
                    mode="reference_only",
                    metadata={
                        "trade_eligible": False,
                        "as_of": as_of,
                        "indices": valid_indices,
                        "breadth": overview.get("breadth", {}) if isinstance(overview, dict) else {},
                        "totals": overview.get("totals", {}) if isinstance(overview, dict) else {},
                        "official_error": official_error[:240],
                    },
                )

            crawl_progress: dict[str, Any] = {}
            crawl_complete = bool(screener_meta.get("completed"))
            refresh_in_progress = bool(screener_meta.get("refresh_in_progress"))
            screener_age = age_seconds(screener_receipt)
            crawl_refresh_due = bool(
                crawl_complete
                and screener_age is not None
                and screener_age >= settings.tindex.screener_refresh_seconds
            )
            if not within_local_window and screener_due:
                tindex_crawl_attempted = True
                tindex_refresh_action = "screener_page_requested"
                starting_refresh = bool(crawl_refresh_due and not refresh_in_progress)
                if starting_refresh:
                    requested_page = 1
                elif refresh_in_progress:
                    requested_page = max(1, int(screener_meta.get("pending_next_page") or 1))
                else:
                    requested_page = max(1, int(screener_meta.get("next_page") or 1))
                page = await tindex.fetch_stock_page_envelope(page=requested_page, per_page=100)
                if page:
                    page_meta = page["meta"]
                    is_refresh_generation = bool(starting_refresh or refresh_in_progress)
                    if starting_refresh:
                        prior_rows = []
                    elif refresh_in_progress:
                        prior_rows = screener_meta.get("pending_symbols") if isinstance(screener_meta.get("pending_symbols"), list) else []
                    else:
                        prior_rows = screener_meta.get("symbols") if isinstance(screener_meta.get("symbols"), list) else []
                    merged_by_slug = {
                        str(row.get("slug")): row
                        for row in prior_rows
                        if isinstance(row, dict) and row.get("slug")
                    }
                    accepted_rows = 0
                    for row in page["rows"]:
                        try:
                            slug = str(row.get("slug") or "").strip()
                            ticker = normalize_persian_text(str(row.get("ticker") or "").strip())
                            name_fa = normalize_persian_text(str(row.get("name") or ticker).strip())
                            last_price = float(row.get("last_price") or 0)
                            closing_price = float(row.get("closing_price") or 0)
                            change_pct = float(row.get("change") or 0)
                            volume = max(0, int(row.get("volume") or 0))
                            value_rials = max(0.0, float(row.get("value") or 0))
                            market_cap_rials = max(0.0, float(row.get("market_cap") or 0))
                            pe = float(row["pe"]) if row.get("pe") is not None else None
                        except (AttributeError, TypeError, ValueError):
                            continue
                        if not slug or not ticker or last_price < 0:
                            continue
                        merged_by_slug[slug] = {
                            "slug": slug,
                            "ticker": ticker,
                            "name_fa": name_fa,
                            "last_price_rials": last_price if last_price > 0 else None,
                            "closing_price_rials": closing_price if closing_price > 0 else None,
                            "change_pct": change_pct,
                            "volume": volume,
                            "value_rials": value_rials,
                            "market_cap_rials": market_cap_rials,
                            "pe": pe,
                            "source_updated_at": row.get("updated_at"),
                        }
                        accepted_rows += 1
                    generation_symbols = sorted(merged_by_slug.values(), key=lambda item: item["ticker"])
                    try:
                        reported_page = int(page_meta.get("page"))
                        reported_total = int(page_meta.get("total"))
                        reported_last_page = int(page_meta.get("last_page"))
                        reported_per_page = int(page_meta.get("per_page"))
                    except (TypeError, ValueError):
                        reported_page = reported_total = reported_last_page = reported_per_page = -1
                    expected_prefix = "pending_" if is_refresh_generation else ""
                    expected_total = screener_meta.get(f"{expected_prefix}total")
                    expected_last_page = screener_meta.get(f"{expected_prefix}last_page")
                    expected_per_page = screener_meta.get(f"{expected_prefix}per_page")
                    try:
                        expected_generation = (
                            int(expected_total), int(expected_last_page), int(expected_per_page)
                        ) if all(value is not None for value in (expected_total, expected_last_page, expected_per_page)) else None
                    except (TypeError, ValueError):
                        expected_generation = None
                    has_more = bool(page_meta.get("has_more"))
                    page_error: str | None = None
                    if not page["rows"] or accepted_rows != len(page["rows"]):
                        page_error = "Tindex screener page contained zero or invalid contract rows."
                    elif reported_page != requested_page:
                        page_error = "Tindex screener pagination did not match the requested page."
                    elif reported_total < len(generation_symbols) or reported_last_page < reported_page or reported_page < 1 or reported_per_page < 1:
                        page_error = "Tindex screener pagination totals were logically inconsistent."
                    elif expected_generation is not None and expected_generation != (
                        reported_total, reported_last_page, reported_per_page
                    ):
                        page_error = "Tindex screener pagination metadata changed within one generation."
                    elif has_more != (reported_page < reported_last_page):
                        page_error = "Tindex screener has_more flag contradicted last_page."
                    elif not has_more and len(generation_symbols) != reported_total:
                        page_error = "Tindex final page did not complete the advertised symbol total."

                    if page_error:
                        tindex_refresh_action = "screener_page_rejected"
                        # Never replace a published cache with a partial/invalid
                        # generation. Preserve both the published rows and any
                        # previously validated pending pages so this page can be
                        # retried after the provider contract recovers.
                        error_metadata = {**screener_meta, "trade_eligible": False, "official_error": official_error[:240]}
                        if starting_refresh:
                            error_metadata.update({
                                "refresh_in_progress": True,
                                "pending_symbols": [],
                                "pending_next_page": 1,
                                "refresh_cycle_started": True,
                                "refresh_cycle_started_at": to_utc_iso(now_utc()),
                            })
                        self._record_receipt(
                            source_key="tindex_symbol_screener_reference",
                            source_kind="symbol_reference",
                            provider_name="Tindex",
                            provider_url=settings.tindex.base_url,
                            status="SCHEMA_ERROR",
                            record_count=int(screener_receipt.record_count if screener_receipt else 0),
                            error_message=page_error,
                            schema_version="unverified",
                            mode="reference_only",
                            metadata=error_metadata,
                        )
                    else:
                        tindex_refresh_action = "screener_page_accepted"
                        generation_completed = not has_more
                        next_page = requested_page + 1 if has_more else 1
                        published_rows = (
                            generation_symbols
                            if not is_refresh_generation or generation_completed
                            else (screener_meta.get("symbols") if isinstance(screener_meta.get("symbols"), list) else [])
                        )
                        published_at = (
                            to_utc_iso(now_utc())
                            if not is_refresh_generation or generation_completed
                            else (screener_meta.get("published_at") or to_utc_iso(screener_receipt.last_success_at if screener_receipt else None))
                        )
                        crawl_progress = {
                            "collected": len(generation_symbols),
                            "total": reported_total,
                            "page": requested_page,
                            "last_page": reported_last_page,
                            "completed": generation_completed,
                        }
                        metadata = {
                            "trade_eligible": False,
                            "symbols": published_rows,
                            "next_page": next_page if not is_refresh_generation else 1,
                            "last_page": crawl_progress["last_page"],
                            "total": crawl_progress["total"],
                            "per_page": reported_per_page,
                            "completed": generation_completed if not is_refresh_generation else True,
                            "last_page_fetched": requested_page if not is_refresh_generation or generation_completed else int(screener_meta.get("last_page_fetched") or 0),
                            "refresh_in_progress": bool(is_refresh_generation and not generation_completed),
                            "refresh_cycle_started": bool(starting_refresh),
                            "published_at": published_at,
                            "official_error": official_error[:240],
                        }
                        if is_refresh_generation and not generation_completed:
                            metadata.update({
                                "pending_symbols": generation_symbols,
                                "pending_next_page": next_page,
                                "pending_last_page_fetched": requested_page,
                                "pending_total": reported_total,
                                "pending_last_page": reported_last_page,
                                "pending_per_page": reported_per_page,
                                "refresh_cycle_started_at": screener_meta.get("refresh_cycle_started_at") or to_utc_iso(now_utc()),
                            })
                        self._record_receipt(
                            source_key="tindex_symbol_screener_reference",
                            source_kind="symbol_reference",
                            provider_name="Tindex",
                            provider_url=settings.tindex.base_url,
                            status="HEALTHY",
                            record_count=len(published_rows),
                            schema_version="tindex-stock-screener-reference-v1",
                            mode="reference_only",
                            metadata=metadata,
                        )
                elif tindex.last_error and not tindex.last_error.startswith("LOCAL_RATE_LIMIT"):
                    tindex_refresh_action = "screener_unavailable"
                    self._record_receipt(
                        source_key="tindex_symbol_screener_reference",
                        source_kind="symbol_reference",
                        provider_name="Tindex",
                        provider_url=settings.tindex.base_url,
                        status="UNAVAILABLE",
                        record_count=int(screener_receipt.record_count if screener_receipt else 0),
                        error_message=tindex.last_error,
                        schema_version="unverified",
                        mode="reference_only",
                        metadata={**screener_meta, "trade_eligible": False, "official_error": official_error[:240]},
                    )
            if valid_indices or tindex_refresh_action == "screener_page_accepted":
                providers.append("Tindex")

        sourcearena = SourceArenaAdapter()
        if sourcearena.configured:
            configured.append("SourceArena")
            rows = await sourcearena.fetch_market_rows()
            status = "DEGRADED" if rows else "UNAVAILABLE"
            self._record_receipt(
                source_key="sourcearena_market_reference",
                source_kind="market_reference",
                provider_name="SourceArena",
                provider_url=settings.sourcearena.base_url,
                status=status,
                record_count=len(rows),
                error_message=(
                    "Full-market rows received, but the bulk contract has no authoritative source timestamp; trading remains blocked."
                    if rows else (sourcearena.last_error or "SourceArena returned no contract-valid rows.")
                ),
                schema_version="sourcearena-all-symbols-v1" if rows else "unverified",
                mode="reference_only",
                metadata={"trade_eligible": False, "official_error": official_error[:240]},
            )
            if rows:
                providers.append("SourceArena")

        brsapi = BrsApiAdapter()
        if brsapi.configured:
            configured.append("BrsApi")
            rows = await brsapi.fetch_market_rows()
            source_times = sorted({str(row.get("time") or "") for row in rows if row.get("time")})
            status = "DEGRADED" if rows else "UNAVAILABLE"
            normalized_rows = [
                item for item in (
                    normalize_brsapi_row(row, source_timestamp=brsapi.last_response_at)
                    for row in rows
                ) if item is not None
            ]
            complete = bool(len(normalized_rows) >= 1000 and len(normalized_rows) / max(1, len(rows)) >= 0.95)
            if normalized_rows:
                persist_reference_batch(
                    self.db,
                    source_key="brsapi_market_reference",
                    provider_name="BrsApi",
                    schema_version="brsapi-all-symbols-v2",
                    rows=normalized_rows,
                    source_timestamp=brsapi.last_response_at,
                    complete=complete,
                    metadata={
                        "independence_key": brsapi.independence_key,
                        "upstream": "TSETMC_DERIVED",
                        "trade_eligible": False,
                        "raw_row_count": len(rows),
                    },
                )
            self._record_receipt(
                source_key="brsapi_market_reference",
                source_kind="market_reference",
                provider_name="BrsApi",
                provider_url=settings.brsapi.base_url,
                status=status,
                record_count=len(rows),
                error_message=(
                    "Full-market TSETMC-derived rows received, but the bulk contract exposes time without a source date; trading remains blocked."
                    if rows else (brsapi.last_error or "BrsApi returned no contract-valid rows.")
                ),
                schema_version="brsapi-all-symbols-v2" if rows else "unverified",
                mode="reference_only",
                metadata={
                    "trade_eligible": False,
                    "independence_key": brsapi.independence_key,
                    "source_time_min": source_times[0] if source_times else None,
                    "source_time_max": source_times[-1] if source_times else None,
                    "normalized_row_count": len(normalized_rows),
                    "complete": complete,
                    "source_response_at": to_utc_iso(brsapi.last_response_at),
                    "official_error": official_error[:240],
                },
            )
            if rows:
                providers.append("BrsApi")

        if providers:
            screener_receipt = self.db.query(DataSourceReceipt).filter(
                DataSourceReceipt.source_key == "tindex_symbol_screener_reference"
            ).first()
            screener_meta = (screener_receipt.metadata_json or {}) if screener_receipt else {}
            collected = int(screener_receipt.record_count if screener_receipt else 0)
            total = int(screener_meta.get("total") or 0)
            added = max(0, collected - previous_reference_count)
            crawl_message = (
                f" دیده‌بان مرجع Tindex: {collected} از {total} نماد جمع شده است."
                if total else ""
            )
            if added > 0:
                refresh_detail = f" در همین درخواست {added} نماد جدید به cache مرجع افزوده شد."
            elif tindex_refresh_action == "quota_cooldown":
                refresh_detail = (
                    f" برای رعایت سهمیه Tindex، صفحه جدید تا حدود "
                    f"{tindex_cooldown_remaining_seconds} ثانیه دیگر درخواست نمی‌شود؛ cache قبلی حفظ شد."
                )
            elif tindex_refresh_action == "overview_refreshed":
                refresh_detail = " در این درخواست نمای شاخص‌های Tindex تازه شد؛ صفحه بعدی نمادها در نوبت مجاز بعدی دریافت می‌شود."
            elif tindex_crawl_attempted:
                refresh_detail = " صفحه بعدی Tindex بررسی شد اما تعداد نمادهای منتشرشده تغییر نکرد."
            else:
                refresh_detail = " cache مرجع بررسی شد و صفحه جدیدی در این نوبت لازم نبود."
            return {
                "trade_eligible": False,
                "fallback": True,
                "providers": providers,
                "reference_symbols_collected": collected,
                "reference_symbols_total": total,
                "reference_symbols_added": added,
                "tindex_refresh_action": tindex_refresh_action,
                "tindex_cooldown_remaining_seconds": tindex_cooldown_remaining_seconds,
                "message_fa": "داده جایگزین صرفاً برای نمایش/کنترل دریافت شد؛ خرید تا تأیید داده رسمی مسدود است." + crawl_message + refresh_detail,
            }
        if configured:
            raise RuntimeError("منابع پشتیبان تنظیم شده‌اند اما پاسخ تازه و منطبق با قرارداد ندادند.")
        raise RuntimeError("توکن Tindex، SourceArena یا BrsApi برای مسیر پشتیبان تنظیم نشده است.")

    async def sync_cdn_market_watch(self) -> dict[str, Any]:
        """Ingest the official public TSETMC CDN as the sole live market source."""
        receipt = self.db.query(DataSourceReceipt).filter(
            DataSourceReceipt.source_key == "tsetmc_market_watch"
        ).first()
        session = get_market_session_state()
        if settings.tsetmc_market_hours_enforced and not session["upstream_requests_allowed"]:
            latest_batch = (
                self.db.query(MarketDataBatch)
                .filter(
                    MarketDataBatch.source_key == "tsetmc_cdn_market_watch",
                    MarketDataBatch.complete == True,
                )
                .order_by(MarketDataBatch.source_timestamp.desc().nullslast())
                .first()
            )
            last_at = (
                latest_batch.source_timestamp
                if latest_batch is not None
                else (receipt.last_success_at if receipt is not None else None)
            )
            return {
                "trade_eligible": False,
                "fallback": False,
                "skipped": True,
                "skip_reason": "market_closed",
                "providers": ["TSETMC Public CDN"],
                "market_rows": int(latest_batch.row_count if latest_batch else 0),
                "index_rows": 0,
                "last_market_update_at": to_utc_iso(last_at),
                "next_open_at_tehran": session["next_open_at_tehran"],
                "seconds_until_next_open": session["seconds_until_next_open"],
                "message_fa": (
                    "بازار بسته است؛ هیچ درخواست جدیدی به TSETMC ارسال نشد. "
                    "آخرین snapshot ثبت‌شده فقط برای نمایش نگه داشته می‌شود و "
                    f"دریافت زنده از {session['next_open_jalali']} آغاز خواهد شد."
                ),
            }
        circuit_until_raw = (receipt.metadata_json or {}).get("circuit_open_until") if receipt else None
        if circuit_until_raw:
            try:
                circuit_until = datetime.fromisoformat(str(circuit_until_raw))
                if circuit_until.tzinfo is None:
                    circuit_until = circuit_until.replace(tzinfo=timezone.utc)
                remaining = int((circuit_until - now_utc()).total_seconds())
                if remaining > 0:
                    raise TsetmcCircuitOpenError(
                        f"TSETMC cooldown is active; next single probe is allowed in {remaining} seconds.",
                        retry_after_seconds=remaining,
                    )
            except ValueError:
                pass

        # Exactly one bulk request per cycle.  The adapter's retry path is
        # intentionally disabled here so manual clicks, startup and scheduler
        # cannot multiply one upstream failure into a request burst.
        adapter = TsetmcCdnMarketWatchAdapter(retry_attempts=0)
        rows = await adapter.fetch_market_rows()
        raw_equity_count = len(rows) + int(adapter.rejected_row_count or 0)
        completeness = len(rows) / max(1, raw_equity_count)
        active_official_count = self.db.query(Instrument).filter(
            Instrument.is_active == True,
            ~Instrument.source_instrument_code.like("INS\\_%", escape="\\"),
        ).count()
        previous_full_count = self.db.query(func.max(MarketDataBatch.row_count)).filter(
            MarketDataBatch.source_key == "tsetmc_cdn_market_watch",
            MarketDataBatch.complete == True,
            MarketDataBatch.trade_eligible == True,
        ).scalar() or 0
        # Cold starts use a reviewed lower bound. Later cycles tighten it with
        # the last complete CDN equity batch, preventing silent truncation.
        expected_universe = max(
            active_official_count,
            int(previous_full_count or 0),
            settings.quality.minimum_expected_equity_universe,
        )
        universe_coverage = len(rows) / max(1, expected_universe)
        identity_unique = len({row["isin"] for row in rows}) == len(rows)
        healthy = bool(
            adapter.last_response_at
            and len(rows) >= settings.quality.minimum_expected_equity_universe
            and completeness >= settings.quality.minimum_symbol_completeness_ratio
            and universe_coverage >= settings.quality.minimum_symbol_completeness_ratio
            and identity_unique
        )
        if not healthy:
            cooldown_required = bool(
                adapter.last_failure_kind in {"blocked", "network"}
                or (not rows and adapter.last_error)
            )
            cooldown_seconds = (
                max(300, settings.tsetmc_block_cooldown_seconds)
                if adapter.last_failure_kind == "blocked"
                else max(60, settings.tsetmc_network_cooldown_seconds)
            )
            circuit_until = (
                now_utc() + timedelta(seconds=cooldown_seconds)
                if cooldown_required else None
            )
            self._record_receipt(
                source_key="tsetmc_market_watch",
                source_kind="market",
                provider_name=adapter.provider_name,
                provider_url=adapter.base_url,
                status="SCHEMA_ERROR" if rows else "UNAVAILABLE",
                record_count=len(rows),
                error_message=adapter.last_error or "Official TSETMC CDN contract is below threshold.",
                schema_version="unverified",
                mode="official",
                metadata={
                    "accepted": len(rows), "rejected": adapter.rejected_row_count,
                    "completeness_ratio": completeness, "expected_universe": expected_universe,
                    "universe_coverage": universe_coverage, "identity_unique": identity_unique,
                    "raw_provider_rows": adapter.raw_row_count,
                    "failure_kind": adapter.last_failure_kind,
                    "circuit_open_until": to_utc_iso(circuit_until) if circuit_until else None,
                    "request_policy": "single_bulk_request_no_retry",
                    "transport_clock_source": adapter.transport_clock_source,
                },
            )
            if circuit_until:
                raise TsetmcCircuitOpenError(
                    "Official TSETMC CDN is unreachable or blocked; the circuit is open and repeated requests are stopped.",
                    retry_after_seconds=cooldown_seconds,
                )
            raise RuntimeError("Official TSETMC CDN market watch failed its freshness/completeness contract.")

        existing_batch = self.db.query(MarketDataBatch).filter(
            MarketDataBatch.source_key == "tsetmc_cdn_market_watch",
            MarketDataBatch.source_timestamp == adapter.last_response_at,
        ).first()
        if existing_batch:
            self._record_receipt(
                source_key="tsetmc_market_watch",
                source_kind="market",
                provider_name=adapter.provider_name,
                provider_url=adapter.base_url,
                status="HEALTHY",
                record_count=existing_batch.row_count,
                schema_version="tsetmc-cdn-market-watch-v1",
                mode="official",
                metadata={
                    "batch_id": existing_batch.id,
                    "source_timestamp": to_utc_iso(adapter.last_response_at),
                    "accepted": len(rows), "rejected": adapter.rejected_row_count,
                    "completeness_ratio": completeness, "expected_universe": expected_universe,
                    "universe_coverage": universe_coverage, "identity_unique": identity_unique,
                    "raw_provider_rows": adapter.raw_row_count,
                    "transport_clock_source": adapter.transport_clock_source,
                    "trust_tier": "OFFICIAL_DIRECT", "reused_batch": True,
                },
            )
            return {
                "trade_eligible": True, "fallback": False, "providers": [adapter.provider_name],
                "market_rows": existing_batch.row_count, "index_rows": 0,
                "message_fa": f"داده مستقیم CDN رسمی TSETMC تازه است؛ {existing_batch.row_count} نماد جمع شده است.",
            }

        batch = MarketDataBatch(
            source_key="tsetmc_cdn_market_watch",
            provider_name=adapter.provider_name,
            source_timestamp=adapter.last_response_at,
            received_at=now_utc(),
            mode="official",
            trust_tier="OFFICIAL_DIRECT",
            trade_eligible=True,
            schema_version="tsetmc-cdn-market-watch-v1",
            row_count=len(rows),
            complete=True,
            metadata_json={
                "accepted": len(rows), "rejected": adapter.rejected_row_count,
                "completeness_ratio": completeness, "expected_universe": expected_universe,
                "universe_coverage": universe_coverage, "identity_unique": identity_unique,
                "raw_provider_rows": adapter.raw_row_count,
                "transport_clock_source": adapter.transport_clock_source,
            },
        )
        self.db.add(batch)
        self.db.flush()
        valuation_count = 0
        for row in rows:
            instrument = self.db.query(Instrument).filter(Instrument.isin == row["isin"]).first()
            if instrument is not None and instrument.source_instrument_code.startswith("INS_"):
                # Never reactivate fixture history by identity collision. Keep
                # it archived under a non-market ISIN and create a clean
                # official instrument for the real feed.
                instrument.is_active = False
                instrument.isin = f"FX_{instrument.id}"[:32]
                self.db.flush()
                instrument = None
            if instrument is None:
                instrument = Instrument(
                    id=f"inst_{row['isin']}",
                    source_instrument_code=row["source_instrument_code"],
                    isin=row["isin"],
                    ticker=row["ticker"],
                    ticker_normalized=row["ticker_normalized"],
                    name_fa=row["name_fa"],
                    market=row["market"],
                    board=row["market"],
                    base_volume=1,
                    is_active=True,
                    metadata_json={"source": "TSETMC_PUBLIC_CDN"},
                )
                self.db.add(instrument)
                self.db.flush()
            else:
                instrument.source_instrument_code = row["source_instrument_code"]
                instrument.ticker = row["ticker"]
                instrument.ticker_normalized = row["ticker_normalized"]
                instrument.name_fa = row["name_fa"]
                instrument.market = row["market"]
                instrument.board = row["market"]
                instrument.is_active = row["trade_eligible"]

            high = row["high"]
            low = row["low"]
            self.db.add(MarketSnapshot(
                instrument_id=instrument.id,
                source_timestamp=row["observed_at"],
                last_price=row["last"], close_price=row["close"],
                high_price=high, low_price=low, yesterday_price=row["yesterday_price"],
                volume=row["volume"], value=row["value"], trade_count=row["trade_count"],
                allowed_min=row["allowed_min"], allowed_max=row["allowed_max"], state=row["state"] or "UNKNOWN",
                source_key="tsetmc_cdn_market_watch", batch_id=batch.id,
                trust_tier="OFFICIAL_DIRECT", trade_eligible=row["trade_eligible"],
            ))
            self.db.add(ReferenceMarketObservation(
                batch_id=batch.id, source_key="tsetmc_cdn_market_watch",
                source_instrument_code=row["source_instrument_code"], isin=row["isin"],
                ticker=row["ticker"], name_fa=row["name_fa"], market=row["market"],
                source_timestamp=row["observed_at"],
                last_price=row["last"], close_price=row["close"], first_price=row["open"],
                high_price=high, low_price=low, yesterday_price=row["yesterday_price"],
                allowed_min=row["allowed_min"], allowed_max=row["allowed_max"],
                volume=row["volume"], value=row["value"], trade_count=row["trade_count"],
                state=row["state"], pe=row.get("pe"), eps=row.get("eps"), market_cap=row.get("market_value"),
                raw_json={"trust_tier": "OFFICIAL_DIRECT", "clock_source": "TSETMC_CDN_hEven"},
            ))
            if row.get("pe") is not None or row.get("eps") is not None:
                latest_fundamental = self.db.query(FundamentalSnapshot).filter(
                    FundamentalSnapshot.instrument_id == instrument.id
                ).order_by(FundamentalSnapshot.as_of.desc()).first()
                latest_date = latest_fundamental.as_of.date() if latest_fundamental else None
                if latest_date != adapter.last_response_at.date():
                    self.db.add(FundamentalSnapshot(
                        instrument_id=instrument.id,
                        symbol=instrument.ticker,
                        as_of=adapter.last_response_at,
                        p_e_ratio=float(row.get("pe") or 0.0),
                        eps=float(row.get("eps") or 0.0),
                        market_cap_rials=float(row.get("market_value") or 0.0),
                        fundamental_score=0.0,
                        fundamental_grade="C",
                        valuation_status="insufficient_evidence",
                        valuation_status_fa="نیازمند صورت مالی و محاسبات کدال",
                        analysis_summary_fa="فقط نسبت بازار TSE دریافت شده؛ برای تصمیم بنیادی کافی نیست.",
                        details={
                            "source_keys": ["market_valuation"],
                            "source": "TSETMC Public CDN",
                            "metrics_scope": ["pe", "eps", "market_cap"],
                            "decision_eligible": False,
                        },
                    ))
                valuation_count += 1
        self.db.commit()
        self._record_receipt(
            source_key="tsetmc_market_watch",
            source_kind="market",
            provider_name=adapter.provider_name,
            provider_url=adapter.base_url,
            status="HEALTHY",
            record_count=len(rows),
            schema_version="tsetmc-cdn-market-watch-v1",
            mode="official",
            metadata={
                "batch_id": batch.id, "source_timestamp": to_utc_iso(adapter.last_response_at),
                "accepted": len(rows), "rejected": adapter.rejected_row_count,
                "completeness_ratio": completeness, "expected_universe": expected_universe,
                "universe_coverage": universe_coverage, "identity_unique": identity_unique,
                "raw_provider_rows": adapter.raw_row_count,
                "transport_clock_source": adapter.transport_clock_source,
                "trust_tier": "OFFICIAL_DIRECT",
            },
        )
        self._record_receipt(
            source_key="market_valuation",
            source_kind="fundamental",
            provider_name="TSETMC CDN market valuation",
            provider_url=adapter.base_url,
            status="HEALTHY" if valuation_count >= 300 else "DEGRADED",
            record_count=valuation_count,
            error_message=None if valuation_count >= 300 else "Too few contract-valid PE/EPS valuation rows.",
            schema_version="tsetmc-cdn-valuation-v1" if valuation_count >= 300 else "unverified",
            mode="official",
            metadata={
                "independence_key": "TSETMC_OFFICIAL_PUBLIC_CDN",
                "batch_id": batch.id,
                "metrics_scope": ["pe", "eps", "market_cap"],
                "decision_eligible_without_codal_metrics": False,
            },
        )
        return {
            "trade_eligible": True, "fallback": False, "providers": [adapter.provider_name],
            "market_rows": len(rows), "index_rows": 0, "batch_id": batch.id,
            "message_fa": f"داده مستقیم CDN رسمی TSETMC به‌روز شد؛ {len(rows)} نماد جمع شده است.",
        }

    @staticmethod
    def _codal_datetime_to_utc(raw: str | None) -> datetime | None:
        if not raw:
            return None
        try:
            value = jdatetime.datetime.strptime(raw, "%Y/%m/%d %H:%M:%S").togregorian()
        except ValueError:
            try:
                value = datetime.combine(
                    jdatetime.datetime.strptime(raw, "%Y/%m/%d").togregorian().date(), time(0, 0)
                )
            except ValueError:
                return None
        return value.replace(tzinfo=ZoneInfo("Asia/Tehran")).astimezone(timezone.utc)

    async def sync_codal_disclosures(self) -> dict[str, Any]:
        """Persist the latest official CODAL disclosure page without inventing metrics."""
        adapter = CodalPublicAdapter()
        rows = await adapter.fetch_disclosures(page_number=1, page_size=20)
        accepted = 0
        for row in rows:
            published_at = self._codal_datetime_to_utc(row.get("publish_date_time") or row.get("sent_date_time"))
            if published_at is None:
                continue
            source_id = f"codal_{row['tracing_no']}"
            existing_filing = self.db.query(Filing).filter(Filing.source_filing_id == source_id).first()
            if existing_filing:
                existing_data = dict(existing_filing.structured_data or {})
                if existing_data.get("source_key") != "codal_disclosures":
                    existing_data["source_key"] = "codal_disclosures"
                    existing_filing.structured_data = existing_data
                accepted += 1
                continue
            instrument = self.db.query(Instrument).filter(
                Instrument.is_active == True,
                Instrument.ticker_normalized == row["symbol_normalized"],
            ).first()
            self.db.add(Filing(
                source_filing_id=source_id,
                instrument_id=instrument.id if instrument else None,
                symbol=row["symbol"],
                title=row["title"],
                filing_type=row.get("letter_code") or "disclosure",
                filing_type_fa="اطلاعیه رسمی کدال",
                sentiment="neutral",
                sentiment_fa="بدون تفسیر ماشینی",
                impact_score=5.0,
                summary_fa=row["title"],
                published_at=published_at,
                url=row.get("url"),
                structured_data={
                    "source_key": "codal_disclosures",
                    "source": row["source"], "company_name": row["company_name"],
                    "sent_date_time": row.get("sent_date_time"), "metrics_extracted": False,
                },
            ))
            accepted += 1
        self.db.commit()
        status = "HEALTHY" if rows and accepted else "UNAVAILABLE"
        self._record_receipt(
            source_key="codal_disclosures",
            source_kind="fundamental",
            provider_name="CODAL public search",
            provider_url=adapter.base_url,
            status=status,
            record_count=accepted,
            error_message=None if status == "HEALTHY" else (adapter.last_error or "CODAL returned no contract-valid disclosures."),
            schema_version="codal-public-search-v1" if status == "HEALTHY" else "unverified",
            mode="official",
            metadata={
                "independence_key": adapter.independence_key,
                "total_reported": adapter.last_total,
                "page_count_reported": adapter.last_page_count,
                "metrics_extracted": False,
            },
        )
        return {"status": status, "rows": accepted, "metrics_extracted": False}

    async def sync_live_cycle(self) -> dict[str, Any]:
        """Bounded intraday refresh using only the official public CDN JSON API.

        There is deliberately no hidden provider failover. On transport or
        contract failure the last persisted batch remains readable but no new
        trade-eligible batch is published.
        """
        if settings.market_data_mode != "official":
            raise RuntimeError("Live refresh requires official market-data mode.")
        return await self.sync_cdn_market_watch()

    def advance_market_step(self) -> dict:
        """Advances simulated market by 1 session, creating new bars with realistic TSE price movements."""
        if settings.market_data_mode != "fixture":
            raise RuntimeError("Synthetic market advancement is available only in explicit fixture mode.")
        import random
        from datetime import timedelta
        instruments = self.db.query(Instrument).filter(Instrument.is_active == True).all()
        updated = 0
        for inst in instruments:
            latest_bar = (
                self.db.query(EODBar)
                .filter(EODBar.instrument_id == inst.id)
                .order_by(EODBar.trading_date.desc())
                .first()
            )
            if not latest_bar:
                continue

            next_date = latest_bar.trading_date + timedelta(days=1)
            # Skip Iranian weekend (Thursday=3, Friday=4 in python weekday)
            while next_date.weekday() in (3, 4):
                next_date += timedelta(days=1)

            drift = random.uniform(-0.022, 0.038)
            yesterday_price = latest_bar.close
            new_close = max(100.0, round(yesterday_price * (1.0 + drift)))
            new_open = round(yesterday_price * (1.0 + drift * 0.35))
            high_bonus = random.uniform(0.002, 0.012)
            low_penalty = random.uniform(0.002, 0.012)
            new_high = max(new_open, new_close, round(yesterday_price * (1.0 + max(drift, 0) + high_bonus)))
            new_low = min(new_open, new_close, round(yesterday_price * (1.0 + min(drift, 0) - low_penalty)))
            new_vol = int(latest_bar.volume * random.uniform(0.85, 1.45))
            new_val = new_close * new_vol
            trade_cnt = int((latest_bar.trade_count or 1500) * random.uniform(0.9, 1.3))

            existing = (
                self.db.query(EODBar)
                .filter(EODBar.instrument_id == inst.id, EODBar.trading_date == next_date)
                .first()
            )
            if not existing:
                new_bar = EODBar(
                    id=f"eod_{inst.ticker}_{next_date.isoformat()}",
                    instrument_id=inst.id,
                    trading_date=next_date,
                    open=new_open,
                    high=new_high,
                    low=new_low,
                    close=new_close,
                    last=new_close,
                    yesterday_price=yesterday_price,
                    volume=new_vol,
                    value=new_val,
                    trade_count=trade_cnt,
                    allowed_min=round(yesterday_price * 0.95),
                    allowed_max=round(yesterday_price * 1.05),
                    available_at=now_utc(),
                    ingested_at=now_utc(),
                )
                self.db.add(new_bar)

                real_buy_vol = int(new_vol * (0.60 + drift * 2))
                real_sell_vol = max(0, new_vol - real_buy_vol)
                new_ct = ClientTypeSnapshot(
                    id=f"ct_{inst.ticker}_{next_date.isoformat()}",
                    instrument_id=inst.id,
                    trading_date=next_date,
                    real_buy_count=int(trade_cnt * 0.7),
                    real_buy_volume=max(0, real_buy_vol),
                    real_buy_value=max(0, real_buy_vol * new_close),
                    real_sell_count=int(trade_cnt * 0.6),
                    real_sell_volume=real_sell_vol,
                    real_sell_value=max(0, real_sell_vol * new_close),
                    legal_buy_count=10,
                    legal_buy_volume=max(0, new_vol - real_buy_vol),
                    legal_buy_value=max(0, (new_vol - real_buy_vol) * new_close),
                    legal_sell_count=15,
                    legal_sell_volume=max(0, new_vol - real_sell_vol),
                    legal_sell_value=max(0, (new_vol - real_sell_vol) * new_close),
                    available_at=now_utc(),
                )
                self.db.add(new_ct)
                updated += 1

        self.db.commit()
        logger.info(f"Advanced market forward for {updated} instruments.")
        return {"updated_instruments": updated}

    def run_radar_scan(self) -> list[PublishedSignal]:
        """Serialize scans so scheduler/backfill cannot race signal publication."""
        if not _RADAR_SCAN_LOCK.acquire(blocking=False):
            logger.info("Radar scan skipped because another scan is already running.")
            return []
        try:
            return self._run_radar_scan_locked()
        finally:
            _RADAR_SCAN_LOCK.release()

    def _run_radar_scan_locked(self) -> list[PublishedSignal]:
        """
        Computes features for all symbols, evaluates strategy catalog,
        and generates ranked opportunities.
        """
        self.calibrator = load_active_calibrator(self.db)
        instruments = self.db.query(Instrument).filter(Instrument.is_active == True).all()
        signals = []
        # 1. Determine Market Regime
        regime_res = compute_market_regime_from_db(self.db)
        if regime_res is None:
            logger.warning("Radar scan blocked: insufficient official PIT evidence for market regime.")
            return []

        # 2. Extract features and evaluate strategies for each symbol
        symbol_candidates = []
        for inst in instruments:
            bars = (
                trusted_eod_query(self.db, inst.id)
                .order_by(EODBar.trading_date.asc())
                .all()
            )
            if len(bars) < settings.strategy_engine.min_history_sessions:
                continue

            ct_snapshots = (
                trusted_client_type_query(self.db, inst.id)
                .order_by(ClientTypeSnapshot.trading_date.asc())
                .all()
            )

            bars_dict_list = [
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

            ct_dict_list = [
                {
                    "trading_date": ct.trading_date.isoformat(),
                    "real_buy_count": ct.real_buy_count,
                    "real_buy_volume": ct.real_buy_volume,
                    "real_buy_value": ct.real_buy_value,
                    "real_sell_count": ct.real_sell_count,
                    "real_sell_volume": ct.real_sell_volume,
                    "real_sell_value": ct.real_sell_value,
                    "legal_buy_value": ct.legal_buy_value,
                    "legal_sell_value": ct.legal_sell_value,
                }
                for ct in ct_snapshots
            ]

            features = compute_symbol_features(bars_dict_list, ct_dict_list)

            latest_snapshot = latest_trusted_market_snapshot(
                self.db,
                inst.id,
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
                data_quality_score = instrument_data_quality_score(bars, ct_snapshots)
                sample_support_score = min(100.0, len(bars) / settings.strategy_engine.min_history_sessions * 100.0)
                symbol_candidates.append((ctx, candidates, data_quality_score, sample_support_score))

        # 3. Assemble and rank PublishedSignals
        symbol_candidates.sort(key=lambda item: max(c.vote for c in item[1]), reverse=True)
        total_cand = len(symbol_candidates)

        # Preserve immutable signal evidence referenced by pending orders.
        # Other snapshots are replaced atomically by this scan's new results.
        pending_signal_ids = {
            signal_id for (signal_id,) in self.db.query(BrokerOrder.signal_id).filter(
                BrokerOrder.status.in_(["SUBMITTED", "PARTIALLY_FILLED"]),
                BrokerOrder.signal_id.isnot(None),
            ).all()
            if signal_id and not signal_id.startswith("position:")
        }
        stale_query = self.db.query(PublishedSignal)
        if pending_signal_ids:
            stale_query = stale_query.filter(PublishedSignal.id.notin_(pending_signal_ids))
        stale_query.delete(synchronize_session=False)

        for rank_idx, (ctx, candidates, data_quality_score, sample_support_score) in enumerate(symbol_candidates):
            rank_pct = 100.0 - ((rank_idx / max(1, total_cand)) * 100.0)
            sig = assemble_published_signal(
                ctx=ctx,
                candidates=candidates,
                calibrator=self.calibrator,
                cross_sectional_rank_pct=rank_pct,
                data_quality_score=data_quality_score,
                sample_support_score=sample_support_score,
                fundamental_evidence=evaluate_fundamental_gate(self.db, ctx.instrument_id, ctx.symbol),
            )
            if sig:
                self.db.add(sig)
                signals.append(sig)

        self.db.commit()
        logger.info(f"Radar scan published {len(signals)} opportunities.")
        return signals
