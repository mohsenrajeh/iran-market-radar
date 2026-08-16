# 21 — Sample Signal / Dashboard Contract

This is a shape example only. **Values are fictional and must never appear as production demo defaults without a DEMO label.**

```json
{
  "id": "sig_example",
  "instrument_id": "uuid",
  "symbol": "نماد",
  "name_fa": "شرکت نمونه",
  "market": "TSE",
  "sector": "صنعت نمونه",
  "as_of": "2026-08-12T06:30:00Z",
  "horizon": "5d",
  "direction": "long",
  "actionable": true,
  "grade": "A",
  "opportunity_score": 84,
  "p_profit": 0.64,
  "confidence": 76,
  "signal_strength": 91,
  "expected_return_pct": 4.2,
  "expected_drawdown_pct": -2.1,
  "entry_zone": {"low": 10000, "high": 10200, "max_chase": 10300},
  "invalidation": {
    "price": 9650,
    "type": "structure_atr",
    "reason_fa": "شکست کف ساختاری و عبور از بافر نوسان"
  },
  "exit_plan": {
    "type": "trailing_plus_time_stop",
    "targets": [10800, 11200],
    "time_stop_sessions": 5,
    "trailing_rule": "2ATR below highest close after entry"
  },
  "liquidity_score": 82,
  "fill_probability_score": 74,
  "data_quality": 96,
  "regime": "risk_on",
  "strategy_votes": [
    {"strategy": "cross_sectional_momentum", "vote": 0.83, "reason_fa": "قدرت نسبی بالا نسبت به بازار و صنعت"},
    {"strategy": "breakout_volume", "vote": 0.71, "reason_fa": "شکست محدوده با افزایش حجم"},
    {"strategy": "client_flow", "vote": 0.62, "reason_fa": "جریان حقیقی مثبت و پایدار"}
  ],
  "top_reasons_fa": [
    "قدرت نسبی در صدک بالای بازار",
    "صنعت در فاز چرخش مثبت",
    "حجم معامله بالاتر از خط پایه مقاوم"
  ],
  "risk_flags_fa": [
    "احتمال انجام سفارش متوسط است؛ وضعیت صف قبل از ورود بررسی شود"
  ],
  "model_version": "ensemble-meta-v1",
  "strategy_version": "2026.08.1",
  "calibration_version": "5d-isotonic-v3"
}
```

## Dashboard explanation text template

```text
چرا این نماد بالاست؟
+ قدرت نسبی سهم در افق ۲۰ و ۶۰ جلسه بالاتر از بخش عمده بازار است.
+ صنعت سهم نسبت به شاخص کل عملکرد بهتری دارد.
+ حجم/ارزش معاملات نسبت به الگوی عادی افزایش معنادار دارد.
+ چند خانواده استراتژی مستقل سیگنال هم‌جهت داده‌اند.

ریسک اصلی چیست؟
- نقدشوندگی/صف می‌تواند باعث شود ورود یا خروج دقیقاً در قیمت پیشنهادی انجام نشود.
- احتمال سود برآورد آماری است و تضمین نیست.
```
