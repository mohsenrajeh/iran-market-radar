"""Point-in-time fundamental, CODAL, and macro APIs backed only by persisted receipts."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from packages.domain.models import DataSourceReceipt, Filing, FundamentalSnapshot, Instrument
from packages.domain.schemas import CodalFilingItem, CommodityItem, FundamentalItem, MacroDashboardResponse
from packages.shared.database import get_sync_db
from packages.shared.datetime_utils import to_jalali_str
from services.collector.quality import healthy_fundamental_receipts, fundamental_independence_key


router = APIRouter(prefix="/fundamentals", tags=["Fundamental Analysis & Codal"])


def _latest_snapshot(db: Session, instrument_id: str) -> FundamentalSnapshot | None:
    snapshots = (
        db.query(FundamentalSnapshot)
        .filter(FundamentalSnapshot.instrument_id == instrument_id)
        .order_by(FundamentalSnapshot.as_of.desc())
        .limit(20)
        .all()
    )
    receipts = {item.source_key: item for item in healthy_fundamental_receipts(db)}
    for snapshot in snapshots:
        source_keys = set((snapshot.details or {}).get("source_keys") or [])
        matched = [receipts[key] for key in source_keys if key in receipts]
        independence = {fundamental_independence_key(item) for item in matched}
        if source_keys and source_keys.issubset(receipts) and len(independence) >= 2:
            return snapshot
    return None


def _fundamental_item(db: Session, instrument: Instrument, snapshot: FundamentalSnapshot) -> FundamentalItem:
    filings = (
        db.query(Filing)
        .filter(Filing.instrument_id == instrument.id, Filing.published_at <= snapshot.as_of)
        .order_by(Filing.published_at.desc())
        .all()
    )
    return FundamentalItem(
        id=snapshot.id, symbol=instrument.ticker, name_fa=instrument.name_fa,
        sector_name=instrument.sector.name_fa if instrument.sector else "",
        as_of=to_jalali_str(snapshot.as_of, include_time=True),
        p_e_ratio=snapshot.p_e_ratio, sector_p_e=snapshot.sector_p_e,
        p_s_ratio=snapshot.p_s_ratio, p_b_ratio=snapshot.p_b_ratio,
        eps=snapshot.eps, dps=snapshot.dps, dividend_yield=snapshot.dividend_yield,
        peg_ratio=snapshot.peg_ratio, gross_margin_pct=snapshot.gross_margin_pct,
        operating_margin_pct=snapshot.operating_margin_pct, net_margin_pct=snapshot.net_margin_pct,
        roe_pct=snapshot.roe_pct, roa_pct=snapshot.roa_pct,
        monthly_sales_growth_yoy=snapshot.monthly_sales_growth_yoy,
        monthly_sales_growth_mom=snapshot.monthly_sales_growth_mom,
        latest_monthly_sales_rials=snapshot.latest_monthly_sales_rials,
        piotroski_f_score=snapshot.piotroski_f_score,
        debt_to_equity=snapshot.debt_to_equity, current_ratio=snapshot.current_ratio,
        market_cap_rials=snapshot.market_cap_rials,
        floating_shares_pct=snapshot.floating_shares_pct,
        fundamental_score=snapshot.fundamental_score,
        fundamental_grade=snapshot.fundamental_grade,
        valuation_status=snapshot.valuation_status,
        valuation_status_fa=snapshot.valuation_status_fa,
        analysis_summary_fa=snapshot.analysis_summary_fa,
        recent_filings_count=len(filings),
        latest_filing_sentiment=filings[0].sentiment if filings else "unavailable",
    )


@router.get("/symbols", response_model=list[FundamentalItem])
def get_all_symbols_fundamentals(
    sector: str | None = None,
    grade: str | None = None,
    sort_by: str = "fundamental_score",
    db: Session = Depends(get_sync_db),
):
    """Return only persisted PIT snapshots; missing data stays missing."""
    instruments = (
        db.query(Instrument).options(joinedload(Instrument.sector))
        .filter(Instrument.is_active == True).all()
    )
    results: list[FundamentalItem] = []
    for instrument in instruments:
        if sector and (not instrument.sector or instrument.sector.name_fa != sector):
            continue
        snapshot = _latest_snapshot(db, instrument.id)
        if snapshot is None:
            continue
        item = _fundamental_item(db, instrument, snapshot)
        if grade and item.fundamental_grade != grade:
            continue
        results.append(item)
    sorters = {
        "fundamental_score": lambda item: -item.fundamental_score,
        "p_e": lambda item: (item.p_e_ratio <= 0, item.p_e_ratio),
        "roe": lambda item: -item.roe_pct,
        "sales_growth": lambda item: -item.monthly_sales_growth_yoy,
    }
    results.sort(key=sorters.get(sort_by, sorters["fundamental_score"]))
    return results


@router.get("/summary/{symbol}", response_model=FundamentalItem)
def get_symbol_fundamental_summary(symbol: str, db: Session = Depends(get_sync_db)):
    instrument = db.query(Instrument).options(joinedload(Instrument.sector)).filter(
        Instrument.ticker == symbol, Instrument.is_active == True
    ).first()
    if instrument is None:
        raise HTTPException(status_code=404, detail=f"نماد فعال {symbol} یافت نشد.")
    snapshot = _latest_snapshot(db, instrument.id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail=f"snapshot بنیادی معتبر برای {symbol} ثبت نشده است.")
    return _fundamental_item(db, instrument, snapshot)


@router.get("/codal-feed", response_model=list[CodalFilingItem])
def get_codal_disclosures_feed(
    symbol: str | None = None,
    sentiment: str | None = None,
    filing_type: str | None = None,
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_sync_db),
):
    """Return persisted CODAL/SEDRA filings; never curated templates."""
    receipt_keys = {item.source_key for item in healthy_fundamental_receipts(db)}
    query = db.query(Filing)
    if symbol:
        query = query.filter(Filing.symbol == symbol)
    if sentiment:
        query = query.filter(Filing.sentiment == sentiment)
    if filing_type:
        query = query.filter(Filing.filing_type == filing_type)
    candidates = query.order_by(Filing.published_at.desc()).limit(limit * 5).all()
    rows = [
        row for row in candidates
        if (row.structured_data or {}).get("source_key") in receipt_keys
    ][:limit]
    return [
        CodalFilingItem(
            id=row.id, source_filing_id=row.source_filing_id, symbol=row.symbol,
            title=row.title, filing_type=row.filing_type, filing_type_fa=row.filing_type_fa,
            sentiment=row.sentiment, sentiment_fa=row.sentiment_fa,
            impact_score=row.impact_score, summary_fa=row.summary_fa,
            published_at=to_jalali_str(row.published_at, include_time=True), url=row.url,
        )
        for row in rows
    ]


@router.get("/macro", response_model=MacroDashboardResponse)
def get_macro_and_commodities_dashboard(db: Session = Depends(get_sync_db)):
    """Return macro figures only from a healthy timestamped provider receipt."""
    receipt = (
        db.query(DataSourceReceipt)
        .filter(
            DataSourceReceipt.source_kind == "macro",
            DataSourceReceipt.status == "HEALTHY",
            DataSourceReceipt.mode == "official",
            DataSourceReceipt.last_success_at.isnot(None),
        )
        .order_by(DataSourceReceipt.last_success_at.desc()).first()
    )
    if receipt is None:
        return MacroDashboardResponse(
            status="BLOCKED", reason_fa="هیچ receipt سالم و زمان‌دار از منبع ماکرو ثبت نشده است.",
            provider_name=None, nima_usd_rate=None, nima_usd_change_pct=None,
            free_market_usd_rate=None, gap_nima_free_pct=None, interbank_interest_rate=None,
            commodities=[], macro_regime_fa="نامشخص — داده ساختگی جایگزین نمی‌شود.",
            last_updated_jalali=None,
        )
    metadata = receipt.metadata_json or {}
    commodities = []
    for item in metadata.get("commodities", []):
        try:
            commodities.append(CommodityItem(**item))
        except Exception:
            continue
    return MacroDashboardResponse(
        status="HEALTHY", reason_fa=None, provider_name=receipt.provider_name,
        nima_usd_rate=metadata.get("nima_usd_rate"),
        nima_usd_change_pct=metadata.get("nima_usd_change_pct"),
        free_market_usd_rate=metadata.get("free_market_usd_rate"),
        gap_nima_free_pct=metadata.get("gap_nima_free_pct"),
        interbank_interest_rate=metadata.get("interbank_interest_rate"),
        commodities=commodities,
        macro_regime_fa=str(metadata.get("macro_regime_fa") or "نامشخص"),
        last_updated_jalali=to_jalali_str(receipt.last_success_at, include_time=True),
    )
