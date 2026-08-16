# 11 — Persian RTL UI / Design System

## 1. Product personality

Professional market workstation, not a casino UI. Dense enough for serious scanning, but visually calm. Avoid excessive neon, flashing badges, confetti or “guaranteed buy” language.

## 2. Language and direction

- Primary language: Persian.
- `dir="rtl"` at application root; charts remain logically left-to-right in time while labels/tooltips are Persian.
- Persian date display can use Jalali, but API/storage stays Gregorian/ISO UTC.
- Price/currency unit must always be explicit (ریال/تومان based on chosen app setting); never mix units.
- Persian font: Vazirmatn/Vazir-compatible web font if licensing/distribution permits; fallback system sans.

## 3. Layout

Desktop-first trading dashboard with mobile-responsive read access.

### App shell
- right sidebar navigation on desktop;
- top status bar: market status, data freshness, current regime, source health;
- content max-width flexible for data tables.

### Navigation
1. نمای بازار
2. فرصت‌ها
3. صنایع
4. نمادها
5. استراتژی‌ها
6. بک‌تست
7. معاملات آزمایشی
8. سلامت داده
9. تنظیمات

Future: اتصال کارگزاری.

## 4. Core screens

### Market Overview
Above fold:
- شاخص/بازار status cards;
- regime card;
- breadth visualization;
- top sectors;
- top 5 opportunities.

Below:
- sector heatmap/table;
- flow/turnover;
- queue breadth;
- recent material Codal events.

### Opportunities
High-density sortable table:
- نماد;
- Score;
- احتمال سود;
- Confidence;
- قدرت سیگنال;
- افق;
- ورود;
- ابطال/حدضرر;
- نقدشوندگی;
- استراتژی‌های موافق;
- وضعیت اجرا;
- بروزرسانی.

Click opens detail drawer/page, not a cluttered modal.

### Opportunity Detail
Sections:
- summary card;
- interactive price/volume chart;
- entry/stop/target overlays;
- strategy evidence waterfall/list;
- حقیقی/حقوقی panel;
- sector comparison;
- filing/event timeline;
- OOS reliability/calibration panel;
- risk flags;
- paper-trade action.

### Strategy Lab
- strategy status;
- parameter version;
- OOS metrics by fold/regime;
- calibration chart;
- parameter sensitivity;
- enable/disable with warning/audit.

### Backtest
- immutable config summary;
- equity curve;
- drawdown chart;
- fold table;
- trade distribution;
- sector/regime breakdown;
- fill/unfilled stats;
- calibration if probability model.

### Data Health
Traffic-light style but accessible:
- source;
- last success;
- freshness lag;
- errors;
- missing symbols;
- last checkpoint;
- backfill controls.

## 5. Color semantics

Use semantic tokens rather than hardcoded component colors:
- `positive`;
- `negative`;
- `warning`;
- `info`;
- `neutral`;
- `surface`;
- `border`;
- `accent`.

Support dark and light themes. Ensure accessible contrast. Iran market convention may associate green with positive/red with negative, but never rely on color alone; include signs/icons/text.

## 6. Typography

- numeric data uses tabular numerals;
- ticker prominent but not huge;
- score/probability labels always shown;
- avoid more than 3 text weights on a single card.

## 7. Score presentation

Never show one mysterious “AI 87%”. Display:

```text
امتیاز فرصت        86 / 100
احتمال سود ۵روزه   67٪
اطمینان برآورد      78 / 100
قدرت نسبی سیگنال   صدک 92
```

Tooltip explains each metric.

## 8. Risk language

Use:
- «ناحیه ورود پیشنهادی»
- «سطح ابطال تحلیل / حد خروج»
- «احتمال سود برآوردشده بر اساس داده خارج از نمونه»
- «ریسک عدم انجام سفارش در صف»

Avoid “قطعی”، “تضمینی”، “سود حتمی”.

## 9. Empty/degraded states

If no good signal:
> در این افق زمانی فرصت با کیفیت کافی پیدا نشد.

If source stale:
> داده بازار به‌روز نیست؛ انتشار سیگنال جدید موقتاً متوقف شده است.

Do not show old signals as if current.

## 10. Components

Reusable:
- `OpportunityScoreBadge`
- `ProbabilityBadge`
- `ConfidenceMeter`
- `DataFreshnessBadge`
- `RegimeBadge`
- `RiskFlag`
- `StrategyVoteList`
- `EntryExitPlan`
- `OOSMetricsCard`
- `CalibrationChart`
- `MarketBreadthPanel`
- `SectorStrengthTable`
- `FlowPanel`
- `FilingTimeline`

## 11. Accessibility

- keyboard navigation;
- table headers associated;
- sufficient contrast;
- no color-only meaning;
- tooltips also accessible on focus;
- responsive font/spacing.
