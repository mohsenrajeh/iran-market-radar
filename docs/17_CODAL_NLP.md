# 17 — Codal / Fundamental NLP Layer

## Principle
LLM/NLP helps transform Persian filings into structured evidence and readable summaries. It does not get unilateral control over buy/sell decisions.

## 1. Pipeline

```text
SEDRA/Codal filing
 -> document metadata + structured fields
 -> parser/table extractor
 -> deterministic fact extraction where possible
 -> optional LLM classifier/extractor
 -> validation/provenance
 -> event/fundamental features
 -> strategy/scoring
```

## 2. Deterministic first

Prefer structured source fields and explicit financial tables for numeric facts. Never let an LLM recalculate or overwrite audited numeric facts when a structured value exists.

## 3. NLP outputs

Potential schema:
- event type;
- polarity: positive/neutral/negative/uncertain;
- materiality 0–1;
- affected business/segment;
- duration/one-off vs recurring;
- extracted contract amount/date if explicitly present;
- summary_fa;
- evidence snippets/locations;
- extraction confidence;
- model/provider/version.

## 4. Guardrails

- attach source filing ID;
- require quoted/evidence location internally for material claims;
- no invented numbers;
- classify “uncertain” when ambiguous;
- corrected filings invalidate prior NLP features only from correction publication time forward;
- cache by document hash/model version.

## 5. Provider abstraction

```python
class FilingNlpProvider(Protocol):
    async def analyze(self, filing_document) -> FilingNlpResult: ...
```

Allow:
- disabled;
- local model;
- external API configured by environment.

System must remain useful without LLM availability.

## 6. Event strategy usage

NLP may add:
- event-support score;
- negative-risk flag;
- watchlist candidate;
- user explanation.

Numerical event strategy requires OOS validation using filing publication timestamps.
