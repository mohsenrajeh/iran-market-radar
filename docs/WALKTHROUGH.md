# سامانه رادار بازار سرمایه ایران — گزارش کامل پیاده‌سازی و یکپارچه‌سازی

سیستم به صورت کامل در تمامی لایه‌ها (دریافت داده، مهندسی ویژگی‌ها و اندیکاتورها، آزمایشگاه استراتژی‌ها، موتور خودکار معاملات آزمایشی، ارزیابی دقت اندیکاتورها، لاگ یادگیری ماشین و رابط کاربری فارسی) پیاده‌سازی و راه‌اندازی گردید.

---

## ۱. بسته اندیکاتورهای تکنیکال و تابلوخوانی پیشرفته (۱۲ اندیکاتور + الگوهای شمعی)

در فایل [`packages/feature_engine/indicators.py`](file:///d:/My%20Project/04_Trading-AI/iran-market-radar/packages/feature_engine/indicators.py) توابع زیر به صورت قطعی، بدون نشت داده و مبتنی بر `numpy` پیاده‌سازی شدند:

| دسته‌بندی | اندیکاتورها و توابع | خروجی‌ها |
| :--- | :--- | :--- |
| **روند (Trend)** | `compute_ichimoku`, `compute_supertrend`, `compute_adx`, `compute_ema` | Tenkan, Kijun, Senkou A/B, Chikou, Supertrend Line & Direction, ADX, +DI, -DI |
| **مومنتوم و نوسانگرها** | `compute_rsi`, `compute_stochastic_rsi`, `compute_macd`, `compute_cci`, `compute_williams_r` | RSI(14), StochRSI(K/D), MACD Hist, CCI(20), Williams %R |
| **حجم و جریان نقدینگی** | `compute_mfi`, `compute_obv`, `compute_cmf`, `compute_robust_volume_zscore` | MFI(14), OBV Slope 20d, Chaikin Money Flow (CMF 20), Volume Z-Score |
| **کانال‌ها و فشردگی نوسان** | `compute_bollinger_bands`, `compute_keltner_channels`, `compute_donchian_channels` | BB Squeeze (تلاقی بولینگر و کلدنر), Donchian Breakout |
| **تابلوخوانی بازار ایران** | فیلترهای حقیقی/حقوقی در `compute_symbol_features` | نسبت قدرت سرانه خریدار حقیقی، خالص ورود پول حقیقی، تداوم ورود پول |
| **الگوهای کندل‌استیک** | `detect_candlestick_patterns` | چکش (Hammer)، اینگولفینگ صعودی/نزولی، دوجی، ستاره صبحگاهی |

---

## ۲. آزمایشگاه و رجیستری ۱۲ استراتژی کمّی (Strategies)

در رجیستری [`packages/strategies/registry.py`](file:///d:/My%20Project/04_Trading-AI/iran-market-radar/packages/strategies/registry.py) تمامی ۱۲ استراتژی ثبت و فعال شدند:

1. **S01: مومنتوم مقطعی (Cross-Sectional Momentum)** — رتبه‌بندی بازدهی ۵ و ۲۰ روزه
2. **S02: روند سری زمانی (Time-Series Trend)** — ساختار تراز میانگین‌های متحرک EMA
3. **S03: شکست مقاومت با تایید حجم (Breakout Volume)** — شکست سقف با حجم غیرعادی
4. **S04: پولبک به میانگین‌های متحرک (Trend Pullback)** — اصلاح قیمتی به EMA20 در روند صعودی
5. **S05: بازگشت به میانگین برگزیده (Selective Mean Reversion)** — اشباع فروش RSI و لبه پایینی بولینگر
6. **S06: جهش حجم غیرعادی (Volume Anomaly)** — ورود حجم مشکوک با Z-Score > 2.0
7. **S07: انباشت پول حقیقی (Client Flow Accumulation)** — قدرت سرانه خریدار حقیقی > 1.3
8. **S08: ایچیموکو — روند ابری (Ichimoku Cloud Trend)** — قیمت بالای ابر کومو + کراس تنکان و کیجون + ADX > 25
9. **S09: چرخش صنایع برتر (Sector Rotation)** — صنایع پیشرو با بازدهی نسبی مثبت
10. **S10: فشردگی بولینگر — انفجار نوسان (BB Squeeze Breakout)** — خروج باند بولینگر از کانال کلدنر همراه جهش حجم
11. **S11: تایید چندگانه اندیکاتوری (Multi-Indicator Confluence)** — تایید همزمان حداقل ۵ اندیکاتور از ۸ اندیکاتور مستقل
12. **S12: واگرایی پول هوشمند (Smart Money Divergence)** — افت قیمت با افزایش همزمان MFI، شیب مثبت OBV و خرید سرانه حقیقی

---

## ۳. موتور خودکار معاملات آزمایشی (Auto Paper Trader) و لاگ ML

در فایل‌های [`services/paper_broker/auto_trader.py`](file:///d:/My%20Project/04_Trading-AI/iran-market-radar/services/paper_broker/auto_trader.py) و [`services/paper_broker/scheduler.py`](file:///d:/My%20Project/04_Trading-AI/iran-market-radar/services/paper_broker/scheduler.py):

* **سرمایه اولیه:** **۱ میلیارد تومان** (۱۰٬۰۰۰٬۰۰۰٬۰۰۰ ریال).
* **اجرای خودکار ساعتی:** برنامه‌ریزی شده با کرون‌جاب ساعتی.
* **ثبت دقیق اطلاعات هر معامله:**
  * **دلیل خرید و استراتژی ورود (Entry Rationale & Confluence)**
  * **سرمایه وارد شده (به میلیون تومان و ریال، تعداد سهم و قیمت ورود)**
  * **مدت باز بودن معامله (Days Open)**
  * **تخمین زمان رسیدن به سود (Expected Days to Target / Time Stop)**
  * **موقعیت در رژیم بازار (Market Regime: صعودی پرقدرت، خنثی، استراحت، توزیع)**
  * **روش تصمیم‌گیری و درصد ریسک پورتفو (Risk % و نسبت سود به زیان R/R)**
  * **درس آموخته برای هوش مصنوعی (AI Post-Mortem Lesson)**
* **ارزیابی عملکرد اندیکاتورها ([`attribution.py`](file:///d:/My%20Project/04_Trading-AI/iran-market-radar/services/paper_broker/attribution.py)):** محاسبه میزان صحت و دقت (Precision) هر یک از اندیکاتورها در سوددهی نهایی معاملات.

---

## ۴. رابط کاربری جامع فرانت‌اند ([`PaperTradingView.tsx`](file:///d:/My%20Project/04_Trading-AI/iran-market-radar/apps/web/components/PaperTradingView.tsx))

داشبورد کامل با تب‌های تعاملی و طراحی حرفه‌ای RTL:
* **تب پوزیشن‌های باز:** نمایش لحظه‌ای سرمایه وارد شده، حد ضرر، تارگت، روزهای باز، تخمین روزهای باقیمانده تا تارگت، درصد ریسک، نسبت R/R، روش تصمیم‌گیری و دلیل ورود.
* **تب نمودار رشد پورتفو (Equity Curve):** نمودار تعاملی SVG با خط مرجع ۱ میلیارد تومان و گرادیان بازدهی.
* **تب تاریخچه معاملات و دیتای ML:** جدول کامل لاگ‌ها همراه با کالبدشکافی هوش مصنوعی و درس آموخته هر معامله.
* **تب ارزیابی دقت اندیکاتورها:** مقایسه تصویری دقت و سودآوری تجمعی ۱۲ اندیکاتور تکنیکال.
* **کنترلر موتور:** کلید قطع اضطراری (Kill-Switch) و دکمه اجرای دستی چرخه معاملاتی.

---

## ۵. آزمون‌ها و صحت‌سنجی (Verification)

* **۳۶ تست واحد و یکپارچه در Pytest با موفقیت ۱۰۰٪ پاس شدند:**
  ```text
  tests\test_advanced_indicators.py ...........   [ 30%]
  tests\test_api.py .....                         [ 44%]
  tests\test_auto_trader.py .....                 [ 58%]
  tests\test_backtest.py .                        [ 61%]
  tests\test_calibration.py ..                    [ 66%]
  tests\test_features.py .                        [ 69%]
  tests\test_market_rules.py ....                 [ 80%]
  tests\test_paper_broker.py ..                   [ 86%]
  tests\test_persian.py ....                      [ 97%]
  tests\test_strategies.py .                      [100%]
  ============================= 36 passed in 7.99s ==============================
  ```
* **بیلد Next.js 14 بدون خطا (0 Errors) تایید شد.**
* **اجرای واقعی چرخه‌های موتور معاملاتی با پورتفوی ۱ میلیارد تومانی تایید و معاملات کچاد، فخوز، نوری، شبندر، وبملت، فارس، فولاد، فملی و کگل ثبت شدند.**
