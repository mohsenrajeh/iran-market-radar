# 19 — Operational Runbook

## Before market session

Automated checks:
- server clock synchronized;
- DB/Redis healthy;
- official source authentication healthy;
- instrument master/rules reconciled;
- prior EOD complete;
- market calendar/session state loaded;
- no critical data-quality incident;
- live trading remains disabled in phase 1.

## During session

- collector runs only at configured authorized cadence;
- freshness monitor updates status;
- incremental features/strategies run;
- published signals expire/update according to strategy rules;
- data-source stale condition blocks new actionable signals;
- backtests stay on separate low-priority queue.

## After session

- EOD reconciliation/backfill;
- corporate action/filing sync;
- compute final daily features/signals;
- score realized outcomes of expired fixed-horizon signals when label matures;
- update paper ledger;
- calibration/drift monitoring;
- backup.

## Incident: source outage

1. mark source degraded;
2. stop new actionable publication if critical market source exceeds freshness limit;
3. retain last data for display with stale badge;
4. exponential backoff;
5. recover from checkpoint;
6. reconcile gaps before restoring normal state.

## Incident: bad data spike

Examples: impossible price, duplicate timestamp explosion, sudden symbol identity mismatch.

1. quarantine affected source/batch;
2. do not propagate to features/signals;
3. retain raw evidence;
4. compare with source/reference;
5. repair and re-run idempotently;
6. audit event.

## Incident: model drift

If paper realized calibration materially degrades:
- reduce confidence/model ensemble weight;
- do not automatically retrain/promote without OOS validation;
- create challenger retraining run;
- preserve champion for comparison.
