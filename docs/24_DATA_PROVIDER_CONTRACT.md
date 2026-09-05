# قرارداد تک‌منبع داده بازار

از ۲۰۲۶-۰۸-۱۸ تنها provider فعال بازار، JSON عمومی CDN رسمی TSETMC است:

`https://cdn.tsetmc.com`

هیچ username، password یا token برای این مسیر لازم نیست. API احراز‌شده قدیمی، WebGW،
Tindex، BrsApi، SourceArena و سایر تجمیع‌کننده‌ها از چرخه sync، استراتژی و معامله خارج‌اند.

## endpointهای مجاز

- MarketWatch کامل: `GET /api/ClosingPrice/GetMarketWatch` با `paperTypes[0..8]`؛
- جزئیات قیمت: `GET /api/ClosingPrice/GetClosingPriceInfo/{InsCode}`؛
- پنج ردیف سفارش: `GET /api/BestLimits/{InsCode}`؛
- حقیقی/حقوقی: `GET /api/ClientType/GetClientType/{InsCode}/1/0`؛
- حقیقی/حقوقی کل بازار: `GET /api/ClientType/GetClientTypeAll`؛
- تاریخچه روزانه: `GET /api/ClosingPrice/GetClosingPriceDailyList/{InsCode}/0`؛
- جست‌وجوی نماد: `GET /api/Instrument/GetInstrumentSearch/{query}`.

## قرارداد پذیرش

آداپتور `packages/data_adapters/tsetmc_cdn_marketwatch.py` فقط JSON را با User-Agent مرورگر،
timeout محدود، سقف حجم پاسخ و retry برای خطاهای گذرا می‌پذیرد. HTML، redirect، هویت نامعتبر،
قیمت غیرعددی، دامنه نامعتبر، duplicate یا timestamp آینده رد می‌شوند. زمان هر ردیف از `hEven`
و تاریخ response رسمی ساخته می‌شود؛ ساعت محلی سرور جای آن را نمی‌گیرد.

خانواده‌های `IRO1` و `IRO3` به‌ترتیب بورس تهران و فرابورس‌اند. ورقه‌هایی که open/high/low
صفر دارند برای نمایش حفظ می‌شوند اما `trade_eligible=false` هستند. هر batch به
`tsetmc_cdn_market_watch` و schema `tsetmc-cdn-market-watch-v1` متصل است و همه queryهای
استراتژی، سفارش و fill فقط همین provenance را می‌پذیرند.

## رفتار قطع سرویس

هیچ fallback خودکاری وجود ندارد. در خطای شبکه یا تغییر schema، batch جدید منتشر نمی‌شود؛
آخرین batch معتبر فقط با برچسب `STALE` قابل مشاهده است و گیت سفارش جدید بسته می‌ماند.
fixture، OCR، scraping HTML و قیمت ساختگی در production ممنوع‌اند.

## شاهد زنده ۲۰۲۶-۰۸-۱۸

MarketWatch بدون credential از host و Docker پاسخ داد: ۳۳۴۹ ردیف خام، ۹۶۸ ورقه
`IRO1/IRO3` و ۸۷۲ ردیف دارای فیلد کامل جلسه. همان batch از مسیر API داخلی ثبت شد و
WebSocket داخلی `/api/v1/market/ws` رویداد آن را منتشر کرد. این قرارداد paper-only است؛
اتصال کارگزاری واقعی همچنان غیرفعال است.
