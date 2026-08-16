# 13 — Security, Audit and Observability

## Security

### Secrets
- environment/secret store only;
- never log passwords/tokens/cookies;
- redact Authorization headers;
- rotate credentials without image rebuild.

### Web security
- HTTPS;
- secure cookies if session auth;
- CSRF protection for cookie-based writes;
- rate-limit login/admin actions;
- strong password hashing;
- optional TOTP 2FA;
- role checks server-side.

### Network
- only reverse proxy public;
- DB/Redis private Docker network;
- firewall SSH restrictions;
- optional VPN for admin panel.

### Supply chain
- pinned dependency lockfiles;
- dependency/security scan in CI;
- minimal container images;
- non-root containers where practical.

### Broker future
Broker credentials are highest sensitivity. Separate permissions from read-only data credentials. Live adapter never exposes raw token to browser.

## Audit log

Record user/admin/system actions:
- login failures/success where appropriate;
- strategy config changes;
- risk config changes;
- model promotion;
- backtest launch;
- paper/live order intent creation/cancel;
- kill-switch changes;
- source credential/config changes (without secret value).

Audit entries are append-oriented.

## Structured logging

Every log includes:
- timestamp;
- service;
- level;
- request/job ID;
- source/instrument where relevant;
- strategy/model version where relevant.

Avoid one log line per symbol per fast cycle at INFO level; use metrics for high-volume telemetry.

## Metrics

Operational:
- ingestion requests/success/error/latency;
- source freshness lag;
- symbols updated/missing;
- feature batch duration;
- strategy run duration/candidate counts;
- opportunity publish counts by grade;
- queue depth/job failures;
- DB latency/connections;
- memory/CPU.

Quant/research monitoring:
- current signal probability distribution;
- calibration drift;
- feature drift;
- realized paper win rate vs predicted bucket;
- fill rate/slippage drift;
- strategy contribution/turnover;
- regime distribution.

## Alerts

Critical:
- market feed stale during expected session;
- database unavailable;
- job backlog threatens freshness;
- future broker reconciliation mismatch;
- live kill-switch trigger.

Warning:
- Codal degraded;
- calibration drift;
- unusual missingness;
- model artifact failure.
