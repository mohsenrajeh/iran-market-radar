# Runbook کمپین ۳۰روزه معامله کاغذی

## وضعیت فعلی

- سرمایه: ۱۰ میلیارد تومان = ۱۰۰ میلیارد ریال.
- بازه ثبت‌شده: ۲۰۲۶-۰۸-۱۷ تا ۲۰۲۶-۰۹-۱۵ در `Asia/Tehran`.
- شروع: `READY_BLOCKED_DATA` با kill-switch روشن.
- پورتفوی قبلی و fixtureها آرشیو/قرنطینه شده‌اند و حذف نشده‌اند.

## شرایط باز شدن campaign

همه موارد باید برقرار باشند: receipt سالم TSETMC market-watch/index/EOD/client-type، حداقل دو provider بنیادی مستقل، active universe رسمی، snapshot کمتر از ۶۰ ثانیه، market session بین ۰۹:۰۰ تا ۱۲:۳۰ شنبه تا چهارشنبه، reconciliation دفترکل و تأیید صریح اپراتور برای خاموش‌کردن kill-switch.

Scheduler در جلسه بازار هر ۶۰ ثانیه scan می‌کند. خارج جلسه معامله اجرا نمی‌شود؛ post-market فقط reconciliation/report مجاز است. هر cycle باید idempotency و status ثبت کند.

## backup و rollback

بکاپ پیش از overhaul:

`backups/iran_market_radar_pre_overhaul_20260817.dump`

SHA-256:

`8DCD2AC1EA2249D882CD8EF8241CF24CD9E233835319B711D62D6D642929CB36`

Rollback مخرب خودکار نیست. ابتدا سرویس‌های write متوقف، dump فعلی جداگانه گرفته، hash بکاپ بررسی و سپس `pg_restore` در دیتابیس تازه انجام می‌شود. بازگردانی روی دیتابیس جاری بدون تأیید کاربر ممنوع است.

## گزارش روزانه

گزارش باید source status، freshness، شاخص‌های رسمی، breadth، فرصت‌های رد/قبول، سفارش‌های pending/fill/expired، cash/NAV/exposure/drawdown، دلایل add/trim/exit و reconciliation را نشان دهد. مقدار ناموجود باید `ناموجود/تأییدنشده` باشد، نه عدد نمونه.
