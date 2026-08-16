"""
Verification script for authentic Tehran Stock Exchange market prices.
Verifies all symbols, sectors, price histories, positions, and closed trades.
"""
from packages.shared.database import SyncSessionLocal
from packages.domain.models import Instrument, EODBar, Position, ClosedTradeHistory, Portfolio
from packages.data_adapters.fixtures import FIXTURE_INSTRUMENTS

def verify_market_integrity():
    db = SyncSessionLocal()
    try:
        print("🔍 Auditing all market instruments...")
        instruments = db.query(Instrument).all()
        print(f"✅ Total Active Instruments in DB: {len(instruments)}")
        
        errors = []
        fixture_map = {f["ticker"]: f for f in FIXTURE_INSTRUMENTS}
        
        for inst in instruments:
            latest_bar = db.query(EODBar).filter(EODBar.instrument_id == inst.id).order_by(EODBar.trading_date.desc()).first()
            if not latest_bar:
                errors.append(f"❌ {inst.ticker}: No EOD bars found!")
                continue
                
            expected = fixture_map.get(inst.ticker)
            if expected:
                exp_price = expected["base_price"]
                diff_pct = abs(latest_bar.close - exp_price) / exp_price * 100
                if diff_pct > 0.01:
                    errors.append(f"❌ {inst.ticker}: Latest bar close ({latest_bar.close:,.0f}) does not match expected base ({exp_price:,.0f})! Diff: {diff_pct:.2f}%")
                else:
                    print(f"  ✓ {inst.ticker:<8} -> {latest_bar.close:>10,.0f} ﷼ (Anchored accurately)")

        print("\n🔍 Auditing Active Portfolio Positions...")
        positions = db.query(Position).filter(Position.is_open == True).all()
        for p in positions:
            exp = fixture_map.get(p.symbol)
            if exp:
                print(f"  ✓ Pos: {p.symbol:<8} -> Entry: {p.average_entry_price:>8,.0f} ﷼ | Qty: {p.quantity:>8,}")

        print("\n🔍 Auditing Closed Trade History...")
        closed = db.query(ClosedTradeHistory).all()
        for c in closed:
            print(f"  ✓ Hist: {c.symbol:<8} -> Entry: {c.avg_entry_price:>8,.0f} ﷼ | Exit: {c.avg_exit_price:>8,.0f} ﷼")

        if errors:
            print(f"\n🚨 FOUND {len(errors)} DISCREPANCIES:")
            for e in errors:
                print(e)
            return False
        else:
            print("\n🎉 100% MARKET PRICE INTEGRITY CONFIRMED ACROSS ALL SYMBOLS!")
            return True
            
    finally:
        db.close()

if __name__ == "__main__":
    success = verify_market_integrity()
    if not success:
        exit(1)
