"""Deactivate legacy fixture market data without deleting historical rows."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from packages.domain.models import Instrument, PublishedSignal
from packages.shared.database import SyncSessionLocal


BACKUP = ROOT / "backups" / "iran_market_radar_pre_overhaul_20260817.dump"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args()
    if not args.confirm:
        raise SystemExit("Refusing fixture quarantine without --confirm")
    if not BACKUP.exists() or BACKUP.stat().st_size < 1024:
        raise SystemExit("Rollback backup is missing.")
    db = SyncSessionLocal()
    try:
        fixtures = db.query(Instrument).filter(Instrument.source_instrument_code.like("INS\\_%", escape="\\")).all()
        fixture_ids = [inst.id for inst in fixtures]
        for instrument in fixtures:
            instrument.is_active = False
            metadata = dict(instrument.metadata_json or {})
            metadata.update({"quarantined": True, "quarantine_reason": "legacy_fixture_not_official"})
            instrument.metadata_json = metadata
        signal_count = 0
        if fixture_ids:
            signals = db.query(PublishedSignal).filter(PublishedSignal.instrument_id.in_(fixture_ids)).all()
            signal_count = len(signals)
            for signal in signals:
                signal.actionable = False
                flags = list(signal.risk_flags_fa or [])
                reason = "نماد fixture قرنطینه شده و برای معامله معتبر نیست."
                if reason not in flags:
                    flags.append(reason)
                signal.risk_flags_fa = flags
        db.commit()
        print(f"Quarantined {len(fixtures)} fixture instruments and disabled {signal_count} legacy signals; no rows deleted.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
