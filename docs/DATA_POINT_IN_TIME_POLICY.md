# Data Point-in-Time Policy — Iran Market Radar

## 1. Principle of Point-in-Time Integrity
At timestamp $T$, the system and backtesting engines are strictly restricted to data that was physically available at or prior to $T$.

---

## 2. Timestamps Stored on Every Ingestion Record

```python
period_end       # The fiscal reporting period (e.g. 1404/12/29)
published_at     # The official publication timestamp on Codal/TSETMC
available_at     # The timestamp when the filing was parsed by our ingestion pipeline
ingested_at      # Database insertion timestamp
revision_id      # Revision tracking ID
supersedes_id    # Reference to original filing if this report is an amendment
```

---

## 3. Handling Codal Report Revisions & Amendments
When an amended financial statement or disclosure is filed, the historical backtester continues to see only the original unrevised report for timestamps prior to the publication date of the amendment. The revision becomes available only after its actual `published_at` timestamp.
