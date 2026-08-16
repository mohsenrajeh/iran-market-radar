"""Market Data Collection and Radar Execution Coordinator."""
from datetime import date, datetime
from sqlalchemy.orm import Session

from packages.data_adapters.fixtures import FIXTURE_SECTORS, FIXTURE_INSTRUMENTS, FixtureReplayAdapter
from packages.domain.models import Sector, Instrument, EODBar, ClientTypeSnapshot, PublishedSignal, Portfolio
from packages.feature_engine.indicators import compute_symbol_features
from packages.feature_engine.regime import classify_market_regime
from packages.ml.calibration import SignalProbabilityCalibrator
from services.scorer.ensemble import assemble_published_signal
from packages.shared.datetime_utils import now_utc
from packages.shared.logger import logger
from packages.strategies.base import StrategyContext
from packages.strategies.registry import strategy_registry


class IngestionCoordinator:
    """Coordinates market data syncing, feature extraction, and opportunity scanning."""

    def __init__(self, db: Session):
        self.db = db
        self.adapter = FixtureReplayAdapter(seed=42)
        self.calibrator = SignalProbabilityCalibrator(method="isotonic")

    def seed_initial_universe(self):
        """Initializes reference sectors and instruments in the database."""
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
                    is_active=True,
                    base_volume=int(inst["base_price"] * 100),
                )
                self.db.add(new_inst)
        self.db.commit()

        # 3. Default Paper Portfolio
        existing_port = self.db.query(Portfolio).first()
        if not existing_port:
            port = Portfolio(
                id="port_default_paper",
                name="پورتفوی آزمایشی پیش‌فرض (۱ میلیارد تومان)",
                mode="paper",
                cash=10_000_000_000.0,
                initial_cash=10_000_000_000.0,
            )
            self.db.add(port)
            self.db.commit()

    async def sync_all_data(self, history_days: int = 260):
        """Syncs all EOD bars and client-type data for all universe symbols."""
        self.seed_initial_universe()
        instruments = self.db.query(Instrument).filter(Instrument.is_active == True).all()

        for inst in instruments:
            existing_bar_dates = {
                r[0] for r in self.db.query(EODBar.trading_date).filter(EODBar.instrument_id == inst.id).all()
            }
            existing_ct_dates = {
                r[0] for r in self.db.query(ClientTypeSnapshot.trading_date).filter(ClientTypeSnapshot.instrument_id == inst.id).all()
            }

            bars_data = await self.adapter.fetch_eod_history(inst.ticker, days=history_days)
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
                        available_at=now_utc(),
                        ingested_at=now_utc(),
                    )
                    self.db.add(new_bar)

            # Sync Client Types
            ct_data = await self.adapter.fetch_client_type_history(inst.ticker, days=history_days)
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
                        available_at=now_utc(),
                    )
                    self.db.add(new_ct)

            self.db.commit()
        logger.info("Market data synchronization completed.")

    def advance_market_step(self) -> dict:
        """Advances simulated market by 1 session, creating new bars with realistic TSE price movements."""
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
        """
        Computes features for all symbols, evaluates strategy catalog,
        and generates ranked opportunities.
        """
        instruments = self.db.query(Instrument).filter(Instrument.is_active == True).all()
        signals = []

        # 1. Determine Market Regime
        regime_res = classify_market_regime(
            advancers=11,
            decliners=4,
            stocks_above_ema20_pct=72.0,
            current_turnover=45_000_000_000.0,
            median_turnover_20d=35_000_000_000.0,
            index_ret_5d=0.024,
        )

        # 2. Extract features and evaluate strategies for each symbol
        symbol_candidates = []
        for inst in instruments:
            bars = (
                self.db.query(EODBar)
                .filter(EODBar.instrument_id == inst.id)
                .order_by(EODBar.trading_date.asc())
                .all()
            )
            if len(bars) < 30:
                continue

            ct_snapshots = (
                self.db.query(ClientTypeSnapshot)
                .filter(ClientTypeSnapshot.instrument_id == inst.id)
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
                allowed_min=bars[-1].allowed_min or (bars[-1].close * 0.95),
                allowed_max=bars[-1].allowed_max or (bars[-1].close * 1.05),
            )

            candidates = strategy_registry.evaluate_all(ctx)
            if candidates:
                symbol_candidates.append((ctx, candidates))

        # 3. Assemble and rank PublishedSignals
        symbol_candidates.sort(key=lambda item: max(c.vote for c in item[1]), reverse=True)
        total_cand = len(symbol_candidates)

        # Clear older signals
        self.db.query(PublishedSignal).delete()
        self.db.commit()

        for rank_idx, (ctx, candidates) in enumerate(symbol_candidates):
            rank_pct = 100.0 - ((rank_idx / max(1, total_cand)) * 100.0)
            sig = assemble_published_signal(
                ctx=ctx,
                candidates=candidates,
                calibrator=self.calibrator,
                cross_sectional_rank_pct=rank_pct,
                data_quality_score=96.0,
            )
            if sig:
                self.db.add(sig)
                signals.append(sig)

        self.db.commit()
        logger.info(f"Radar scan published {len(signals)} opportunities.")
        return signals
