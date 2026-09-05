# Iran Market Radar — رادار بازار سرمایه ایران

سامانه پژوهش کمّی، اسکن فرصت و معاملات کاغذی برای بورس و فرابورس ایران. فاز فعلی فقط **تحلیل و Paper Trading** است؛ هیچ سفارش واقعی به کارگزاری ارسال نمی‌شود.

## وضعیت عملیاتی

- سرمایه کمپین فعال: ۱۰ میلیارد تومان (۱۰۰ میلیارد ریال).
- جلسه پیوسته بازار: ۰۹:۰۰ تا ۱۲:۳۰ به وقت تهران.
- چرخه جمع‌آوری داده همیشه روشن است: در بازار هر ۶۰ ثانیه و خارج بازار با cadence تطبیقی. اجرای کاغذی فقط وقتی تمام گیت‌ها سالم باشند فعال می‌شود.
- داده fixture از کمپین فعال قرنطینه شده است.
- نبود قیمت، timestamp، دامنه مجاز، کالیبراسیون خارج از نمونه یا دو منبع بنیادی مستقل، سفارش جدید را مسدود می‌کند.
- تنها منبع بازار فعال، JSON عمومی `cdn.tsetmc.com` است؛ هیچ fallback مخفی یا credential بازار وجود ندارد.
- هیچ قیمت نمونه یا نتیجه تاریخی ساختگی نباید در UI یا API به‌عنوان داده واقعی نمایش داده شود.

در آزمون زنده ۲۰۲۶-۰۸-۱۸، CDN رسمی بدون credential، ۳۳۴۹ ردیف خام و ۹۶۸ ورقه بورس/فرابورس برگرداند. ۸۷۲ ردیف دارای فیلد کامل جلسه به provenance مستقیم متصل شدند. نبود تاریخچه کامل، دو upstream بنیادی مستقل و calibrator همچنان خرید را fail-closed نگه می‌دارد.

## گیت صدور سیگنال قابل اقدام

یک سیگنال تنها وقتی قابل اقدام است که همه شروط زیر هم‌زمان برقرار باشند:

1. حداقل سه خانواده تکنیکال مستقل و چهار رأی صعودی واجد حدنصاب؛
2. دو منبع بنیادی سالم با upstream مستقل؛
3. snapshot رسمی تازه با timestamp منبع و دامنه مجاز واقعی؛
4. حداقل ۲۶۰ جلسه تاریخچه و کیفیت داده اندازه‌گیری‌شده؛
5. مدل احتمال سود برازش‌شده روی داده خارج از نمونه؛
6. نقدشوندگی، محدودیت صنعت، سقف موقعیت و بودجه ریسک مطابق سیاست مرکزی؛
7. اجرای کاغذی فقط روی اولین snapshot رسمی بعد از زمان ثبت سفارش.

۱۲ موتور موجود در `packages/strategies/` شامل momentum، trend، breakout، pullback، mean reversion، volume anomaly، client flow، Ichimoku، sector rotation، BB squeeze، confluence و smart-money divergence هستند. تعداد رأی به‌تنهایی کافی نیست؛ رأی‌های هم‌بسته یک خانواده مستقل محسوب نمی‌شوند.

## ثبت و حسابرسی معاملات

برای خرید، افزایش، کاهش و فروش موارد زیر نگهداری می‌شود:

- شناسه سیگنال، تصمیم، سفارش و fill؛
- نسخه مدل، نسخه استراتژی، سیاست ریسک و snapshot مبنا؛
- دلیل فارسی و اجزای ماشینی تصمیم؛
- قیمت برنامه‌ریزی‌شده و قیمت واقعی شبیه‌سازی‌شده پس از صف/اسلیپیج؛
- کارمزد و مالیات، NAV ورود و خروج، وزن موقعیت، MFE، MAE و R تحقق‌یافته؛
- timeline کامل ورود، scale-in، trim و خروج نهایی.

## راه‌اندازی محلی

```powershell
Copy-Item .env.example .env
docker compose up -d --build
```

آدرس‌ها:

- وب: [http://127.0.0.1:3742](http://127.0.0.1:3742)
- API: [http://127.0.0.1:8742/docs](http://127.0.0.1:8742/docs)
- PostgreSQL: `127.0.0.1:5742`
- Redis: `127.0.0.1:6742`

credentialها فقط در `.env` محلی قرار می‌گیرند و نباید commit، log یا در UI نمایش داده شوند.
این Docker Compose فقط روی loopback و HTTP اجرا می‌شود و بنابراین `COOKIE_SECURE=false` را به API محلی تحمیل می‌کند؛ در استقرار HTTPS عمومی باید این مقدار حتماً `true` باشد.

### عیب‌یابی منبع داده و VPN

```powershell
py -3.11 tools/probe_data_providers.py
```

این probe secretها را چاپ نمی‌کند. `DATA_HTTP_TRUST_ENV=false` جلوی ارث‌بری proxyهای محیطی خراب را می‌گیرد. اگر VPN یک HTTP proxy واقعی دارد، آن را فقط در `DATA_HTTP_PROXY` تنظیم کنید؛ در حالت TUN/split-tunnel باید `python.exe` و Docker در برنامه VPN مجاز شوند.

جزئیات منابع و fallbackها: [docs/24_DATA_PROVIDER_CONTRACT.md](docs/24_DATA_PROVIDER_CONTRACT.md).

## یادگیری کنترل‌شده

سیستم پس از هر معامله post-mortem و داده قابل‌ردیابی ثبت می‌کند، اما با یک زیان پارامتر production را تغییر نمی‌دهد. ساخت کاندید تنها پس از حداقل ۵۰ معامله train و ۲۰ معامله بعدی OOS در دست‌کم دو رژیم بازار مجاز است. نسخه فقط وقتی قابل فعال‌سازی است که Brier در قطعه زمانی OOS بهتر شود؛ فعال‌سازی دستی و قابل‌بازگشت است.

راهنمای ساده و عملی: [docs/25_CONTROLLED_LEARNING_LOOP.md](docs/25_CONTROLLED_LEARNING_LOOP.md).

## کمپین Paper Trading

ایجاد/ترمیم کمپین فعال، آرشیو پورتفوی قدیمی و حفظ rollback:

```powershell
py -3.11 tools/start_paper_campaign.py --confirm-archive-existing
py -3.11 tools/quarantine_fixture_data.py --confirm
```

راهنمای کامل: [docs/23_PAPER_CAMPAIGN_RUNBOOK.md](docs/23_PAPER_CAMPAIGN_RUNBOOK.md).

## مستندات اصلی

- [معماری](docs/02_ARCHITECTURE.md)
- [منابع داده ایران](docs/03_DATA_SOURCES_IRAN.md)
- [کاتالوگ استراتژی](docs/06_STRATEGY_CATALOG.md)
- [امتیازدهی و کالیبراسیون](docs/07_SIGNAL_SCORING_AND_CALIBRATION.md)
- [بک‌تست و اعتبارسنجی](docs/08_BACKTEST_AND_VALIDATION.md)
- [ریسک و اجرا](docs/09_RISK_AND_EXECUTION.md)
- [امنیت و مشاهده‌پذیری](docs/13_SECURITY_AND_OBSERVABILITY.md)
- [دانش معامله‌گری](docs/22_TRADING_KNOWLEDGE_BASE.md)
- [چرخه یادگیری و تنظیم کنترل‌شده](docs/25_CONTROLLED_LEARNING_LOOP.md)
- [معیارهای پذیرش](docs/20_ACCEPTANCE_CRITERIA.md)

## کنترل کیفیت

```powershell
py -3.11 -m pytest tests/ -q
node apps/web/node_modules/typescript/bin/tsc --noEmit -p apps/web/tsconfig.json
node scripts/capture_all_views.js
```

انتشار نهایی تنها وقتی مجاز است که تست‌ها، ۱۰ فونت محلی Vazirmatn، BiDi فارسی، قیمت‌های جاری رسمی و تصاویر Playwright همگی با شواهد مستقل تأیید شده باشند.

## ایمنی اجرای واقعی

اتصال کارگزاری در فاز فعلی غیرفعال است. حتی در توسعه آینده، اجرای واقعی فقط با پنج گیت صریح `TRADING_MODE=live`، `LIVE_TRADING_ENABLED=true`، آداپتور مجاز، credential موجود و `RISK_KILL_SWITCH_ARMED=true` امکان‌پذیر خواهد بود.
