from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from packages.domain.models import DataSourceReceipt, Filing, FundamentalSnapshot, Instrument
from packages.shared.database import Base
from services.scorer.fundamental_gate import evaluate_fundamental_gate


def _receipt(source_key: str, family: str, when: datetime) -> DataSourceReceipt:
    return DataSourceReceipt(
        source_key=source_key,
        source_kind="fundamental",
        provider_name=source_key,
        mode="official",
        status="HEALTHY",
        schema_version="v1",
        last_success_at=when,
        metadata_json={"independence_key": family},
    )


def test_fundamental_gate_requires_fresh_receipts_and_instrument_bound_codal_filing():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    now = datetime.now(timezone.utc)
    instrument = Instrument(
        source_instrument_code="123",
        isin="IRO1TEST00002",
        ticker="نماد",
        ticker_normalized="نماد",
        name_fa="نماد",
        is_active=True,
    )
    other = Instrument(
        source_instrument_code="456",
        isin="IRO1TEST00003",
        ticker="دیگر",
        ticker_normalized="دیگر",
        name_fa="دیگر",
        is_active=True,
    )
    db.add_all([instrument, other])
    db.flush()
    db.add_all([
        _receipt("codal_disclosures", "codal", now - timedelta(minutes=1)),
        _receipt("issuer_financials", "issuer", now - timedelta(minutes=1)),
        FundamentalSnapshot(
            instrument_id=instrument.id,
            symbol=instrument.ticker,
            as_of=now - timedelta(days=1),
            fundamental_score=80,
            piotroski_f_score=7,
            monthly_sales_growth_yoy=20,
            debt_to_equity=0.5,
            details={"source_keys": ["codal_disclosures", "issuer_financials"]},
        ),
        Filing(
            source_filing_id="wrong-instrument",
            instrument_id=other.id,
            symbol=instrument.ticker,
            title="fixture",
            filing_type="disclosure",
            published_at=now - timedelta(hours=1),
            structured_data={"source_key": "codal_disclosures"},
        ),
    ])
    db.commit()

    rejected = evaluate_fundamental_gate(db, instrument.id, instrument.ticker, decision_time=now)
    assert rejected.passed is False
    assert rejected.metrics["latest_filing_id"] is None

    db.add(Filing(
        source_filing_id="official-filing",
        instrument_id=instrument.id,
        symbol=instrument.ticker,
        title="official",
        filing_type="disclosure",
        published_at=now - timedelta(minutes=30),
        structured_data={"source_key": "codal_disclosures"},
    ))
    db.commit()
    accepted = evaluate_fundamental_gate(db, instrument.id, instrument.ticker, decision_time=now)
    assert accepted.passed is True

    for receipt in db.query(DataSourceReceipt).all():
        receipt.last_success_at = now - timedelta(days=2)
    db.commit()
    stale = evaluate_fundamental_gate(db, instrument.id, instrument.ticker, decision_time=now)
    assert stale.passed is False
    assert stale.source_keys == ()
    db.close()
