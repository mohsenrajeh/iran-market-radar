"""High-fidelity fixture data generator and replay adapter for Iranian stock market."""
import math
import random
from datetime import date, datetime, timedelta, timezone
from packages.data_adapters.base import BaseDataAdapter
from packages.domain.models import Sector, Instrument, EODBar, ClientTypeSnapshot, Filing
from packages.shared.datetime_utils import now_utc
from packages.shared.persian import normalize_persian_text, normalize_ticker

# TSE & IFB Top Market Sectors
FIXTURE_SECTORS = [
    {"code": "27", "name_fa": "فلزات اساسی", "desc": "تولیدکنندگان فولاد، مس، روی و آلومینیوم"},
    {"code": "39", "name_fa": "بانک‌ها و مؤسسات اعتباری", "desc": "بانک‌های تجاری و تخصصی"},
    {"code": "44", "name_fa": "خودرو و ساخت قطعات", "desc": "خودروسازان و زنجیره تأمین قطعات"},
    {"code": "23", "name_fa": "فرآورده‌های نفتی و کک", "desc": "پالایشگاه‌های نفت و تولید روانکار"},
    {"code": "44_CHEM", "name_fa": "محصولات شیمیایی و پتروشیمی", "desc": "پتروشیمی‌ها و تولیدکنندگان مواد پایه شیمیایی"},
    {"code": "13", "name_fa": "استخراج کانه‌های فلزی", "desc": "معادن سنگ آهن، مس و طلا"},
    {"code": "34", "name_fa": "چند رشته‌ای صنعتی و هلدینگ", "desc": "هلدینگ‌ها و شرکت‌های سرمایه‌گذاری مادر"},
    {"code": "43", "name_fa": "مواد و محصولات دارویی", "desc": "تولیدکنندگان دارو و مواد اولیه دارویی"},
    {"code": "53", "name_fa": "سیمان، آهک و گچ", "desc": "کارخانجات تولید سیمان و کلینکر"},
    {"code": "01", "name_fa": "زراعت و دامپروری", "desc": "مجتمع‌های کشاورزی و زنجیره پروتئین"},
    {"code": "66", "name_fa": "بیمه و بازنشستگی", "desc": "شرکت‌های بیمه بازرگانی"},
    {"code": "64", "name_fa": "مخابرات و فناوری ارتباطات", "desc": "اپراتورهای مخابراتی و دیتاسنترها"},
    {"code": "40", "name_fa": "حمل و نقل و لجستیک", "desc": "کشتیرانی و حمل و نقل چندوجهی"},
    {"code": "70", "name_fa": "املاک و مستغلات", "desc": "ساختمانی و انبوه‌سازی مسکن"},
]

FIXTURE_INSTRUMENTS = [
    # فلزات اساسی
    {"ticker": "فولاد", "name_fa": "فولاد مبارکه اصفهان", "isin": "IRO1FOLD0001", "sector_code": "27", "base_price": 2785.0, "volatility": 0.018},
    {"ticker": "فملی", "name_fa": "ملی صنایع مس ایران", "isin": "IRO1MSMI0001", "sector_code": "27", "base_price": 3650.0, "volatility": 0.021},
    {"ticker": "فخوز", "name_fa": "فولاد خوزستان", "isin": "IRO1FKHZ0001", "sector_code": "27", "base_price": 3450.0, "volatility": 0.020},
    {"ticker": "ذوب", "name_fa": "سهامی ذوب آهن اصفهان", "isin": "IRO3ZOB10001", "sector_code": "27", "base_price": 420.0, "volatility": 0.028},
    {"ticker": "کاوه", "name_fa": "فولاد کاوه جنوب کیش", "isin": "IRO1KAVE0001", "sector_code": "27", "base_price": 9650.0, "volatility": 0.022},
    {"ticker": "فاسمین", "name_fa": "کالسیمین", "isin": "IRO1FSMN0001", "sector_code": "27", "base_price": 16200.0, "volatility": 0.024},
    {"ticker": "فباهنر", "name_fa": "مس شهید باهنر", "isin": "IRO1MSBH0001", "sector_code": "27", "base_price": 28500.0, "volatility": 0.025},

    # محصولات شیمیایی و پتروشیمی
    {"ticker": "فارس", "name_fa": "صنایع پتروشیمی خلیج فارس", "isin": "IRO1PKHF0001", "sector_code": "44_CHEM", "base_price": 12800.0, "volatility": 0.015},
    {"ticker": "نوری", "name_fa": "پتروشیمی نوری", "isin": "IRO1PBNR0001", "sector_code": "44_CHEM", "base_price": 35740.0, "volatility": 0.019},
    {"ticker": "شپدیس", "name_fa": "پتروشیمی پردیس", "isin": "IRO1PDIS0001", "sector_code": "44_CHEM", "base_price": 245000.0, "volatility": 0.020},
    {"ticker": "زاگرس", "name_fa": "پتروشیمی زاگرس", "isin": "IRO3PZAG0001", "sector_code": "44_CHEM", "base_price": 210000.0, "volatility": 0.021},
    {"ticker": "پترول", "name_fa": "گروه پتروشیمی س. ایرانیان", "isin": "IRO3GPI10001", "sector_code": "44_CHEM", "base_price": 1850.0, "volatility": 0.026},
    {"ticker": "آریا", "name_fa": "پلیمر آریا ساسول", "isin": "IRO3PASZ0001", "sector_code": "44_CHEM", "base_price": 185000.0, "volatility": 0.017},
    {"ticker": "شگویا", "name_fa": "پتروشیمی شهید تندگویان", "isin": "IRO3PGO10001", "sector_code": "44_CHEM", "base_price": 13400.0, "volatility": 0.023},
    {"ticker": "شپلی", "name_fa": "پلی اکریل ایران", "isin": "IRO1PLYI0001", "sector_code": "44_CHEM", "base_price": 5210.0, "volatility": 0.025},
    {"ticker": "تاپیکو", "name_fa": "سرمایه گذاری نفت و گاز تامین", "isin": "IRO1TOPC0001", "sector_code": "44_CHEM", "base_price": 19500.0, "volatility": 0.018},
    {"ticker": "شاراک", "name_fa": "پتروشیمی شازند", "isin": "IRO1PSHZ0001", "sector_code": "44_CHEM", "base_price": 36000.0, "volatility": 0.021},

    # پالایشی و فرآورده‌های نفتی
    {"ticker": "شاوان", "name_fa": "پالایش نفت لاوان", "isin": "IRO3PNL10001", "sector_code": "23", "base_price": 26340.0, "volatility": 0.023},
    {"ticker": "شپنا", "name_fa": "پالایش نفت اصفهان", "isin": "IRO1PNES0001", "sector_code": "23", "base_price": 4150.0, "volatility": 0.022},
    {"ticker": "شبندر", "name_fa": "پالایش نفت بندرعباس", "isin": "IRO1PNBA0001", "sector_code": "23", "base_price": 8500.0, "volatility": 0.023},
    {"ticker": "شتران", "name_fa": "پالایش نفت تهران", "isin": "IRO1PNTN0001", "sector_code": "23", "base_price": 2450.0, "volatility": 0.024},
    {"ticker": "شبریز", "name_fa": "پالایش نفت تبریز", "isin": "IRO1PNTB0001", "sector_code": "23", "base_price": 43240.0, "volatility": 0.023},

    # خودرو و قطعات
    {"ticker": "خودرو", "name_fa": "ایران خودرو", "isin": "IRO1IKCO0001", "sector_code": "44", "base_price": 2950.0, "volatility": 0.028},
    {"ticker": "خساپا", "name_fa": "سایپا", "isin": "IRO1SIPA0001", "sector_code": "44", "base_price": 2450.0, "volatility": 0.027},
    {"ticker": "خپارس", "name_fa": "پارس خودرو", "isin": "IRO1PKHD0001", "sector_code": "44", "base_price": 990.0, "volatility": 0.030},
    {"ticker": "خزامیا", "name_fa": "زامیاد", "isin": "IRO1ZAMD0001", "sector_code": "44", "base_price": 5950.0, "volatility": 0.029},
    {"ticker": "خگستر", "name_fa": "گسترش سرمایه گذاری ایران خودرو", "isin": "IRO1GIKC0001", "sector_code": "44", "base_price": 4020.0, "volatility": 0.028},
    {"ticker": "خبهمن", "name_fa": "گروه بهمن", "isin": "IRO1BAHM0001", "sector_code": "44", "base_price": 3250.0, "volatility": 0.025},

    # بانک‌ها و مؤسسات اعتباری
    {"ticker": "وبملت", "name_fa": "بانک ملت", "isin": "IRO1BMLT0001", "sector_code": "39", "base_price": 1291.0, "volatility": 0.016},
    {"ticker": "وتجارت", "name_fa": "بانک تجارت", "isin": "IRO1TEJR0001", "sector_code": "39", "base_price": 774.0, "volatility": 0.020},
    {"ticker": "وبصادر", "name_fa": "بانک صادرات ایران", "isin": "IRO1BSDR0001", "sector_code": "39", "base_price": 980.0, "volatility": 0.021},
    {"ticker": "ونوین", "name_fa": "بانک اقتصاد نوین", "isin": "IRO1ENBN0001", "sector_code": "39", "base_price": 8100.0, "volatility": 0.022},
    {"ticker": "وخاور", "name_fa": "بانک خاورمیانه", "isin": "IRO1BKHM0001", "sector_code": "39", "base_price": 6950.0, "volatility": 0.015},
    {"ticker": "وسپهر", "name_fa": "سرمایه گذاری مالی سپهر صادرات", "isin": "IRO3SPZ10001", "sector_code": "39", "base_price": 8800.0, "volatility": 0.023},

    # چند رشته‌ای صنعتی و هلدینگ‌ها
    {"ticker": "شستا", "name_fa": "سرمایه گذاری تامین اجتماعی", "isin": "IRO1SSAT0001", "sector_code": "34", "base_price": 1240.0, "volatility": 0.024},
    {"ticker": "وغدیر", "name_fa": "سرمایه گذاری غدیر", "isin": "IRO1GDIR0001", "sector_code": "34", "base_price": 22400.0, "volatility": 0.016},
    {"ticker": "وامید", "name_fa": "مدیریت سرمایه گذاری امید", "isin": "IRO1OMID0001", "sector_code": "34", "base_price": 16500.0, "volatility": 0.017},
    {"ticker": "وبانک", "name_fa": "سرمایه گذاری گروه توسعه ملی", "isin": "IRO1GTML0001", "sector_code": "34", "base_price": 10800.0, "volatility": 0.021},

    # معدنی و استخراج کانه‌های فلزی
    {"ticker": "کچاد", "name_fa": "معدنی و صنعتی چادرملو", "isin": "IRO1CHDR0001", "sector_code": "13", "base_price": 4950.0, "volatility": 0.017},
    {"ticker": "کگل", "name_fa": "معدنی و صنعتی گل گهر", "isin": "IRO1GOLG0001", "sector_code": "13", "base_price": 6850.0, "volatility": 0.018},
    {"ticker": "ومعادن", "name_fa": "توسعه معادن و فلزات", "isin": "IRO1TMDN0001", "sector_code": "13", "base_price": 5400.0, "volatility": 0.019},
    {"ticker": "کگهر", "name_fa": "سنگ آهن گهر زمین", "isin": "IRO3GHR10001", "sector_code": "13", "base_price": 48500.0, "volatility": 0.021},
    {"ticker": "کاما", "name_fa": "باما", "isin": "IRO1BAMA0001", "sector_code": "13", "base_price": 4240.0, "volatility": 0.026},
    {"ticker": "فزر", "name_fa": "پویا زرکان آق دره", "isin": "IRO3PZR10001", "sector_code": "13", "base_price": 204300.0, "volatility": 0.026},

    # دارویی
    {"ticker": "برکت", "name_fa": "گروه دارویی برکت", "isin": "IRO1BRKT0001", "sector_code": "43", "base_price": 9800.0, "volatility": 0.027},
    {"ticker": "تیپیکو", "name_fa": "سرمایه گذاری دارویی تامین", "isin": "IRO1TPCO0001", "sector_code": "43", "base_price": 32500.0, "volatility": 0.020},
    {"ticker": "داروپخش", "name_fa": "داروپخش", "isin": "IRO1DPKH0001", "sector_code": "43", "base_price": 38000.0, "volatility": 0.022},
    {"ticker": "دتولید", "name_fa": "تولید دارو", "isin": "IRO1TLDR0001", "sector_code": "43", "base_price": 13800.0, "volatility": 0.025},

    # سیمان
    {"ticker": "سفارس", "name_fa": "سیمان فارس و خوزستان", "isin": "IRO1SFKH0001", "sector_code": "53", "base_price": 37500.0, "volatility": 0.022},
    {"ticker": "ستران", "name_fa": "سیمان تهران", "isin": "IRO1STRN0001", "sector_code": "53", "base_price": 13800.0, "volatility": 0.024},
    {"ticker": "سشرق", "name_fa": "سیمان شرق", "isin": "IRO1SSHR0001", "sector_code": "53", "base_price": 14200.0, "volatility": 0.026},

    # زراعت و غذایی
    {"ticker": "سیمرغ", "name_fa": "سیمرغ", "isin": "IRO1SMRG0001", "sector_code": "01", "base_price": 27500.0, "volatility": 0.027},
    {"ticker": "سپید", "name_fa": "سپید ماکیان", "isin": "IRO1SPID0001", "sector_code": "01", "base_price": 41000.0, "volatility": 0.024},
    {"ticker": "غکورش", "name_fa": "صنعت غذایی کورش", "isin": "IRO1GKOR0001", "sector_code": "01", "base_price": 17800.0, "volatility": 0.022},

    # بیمه
    {"ticker": "دانا", "name_fa": "بیمه دانا", "isin": "IRO1DANA0001", "sector_code": "66", "base_price": 4850.0, "volatility": 0.023},
    {"ticker": "البرز", "name_fa": "بیمه البرز", "isin": "IRO1ALBZ0001", "sector_code": "66", "base_price": 4950.0, "volatility": 0.022},

    # مخابرات و آی‌تی
    {"ticker": "اخابر", "name_fa": "مخابرات ایران", "isin": "IRO1MKHB0001", "sector_code": "64", "base_price": 8200.0, "volatility": 0.020},
    {"ticker": "همراه", "name_fa": "ارتباطات سیار ایران", "isin": "IRO1MCI10001", "sector_code": "64", "base_price": 4650.0, "volatility": 0.019},
    {"ticker": "های وب", "name_fa": "داده گستر عصر نوین-های وب", "isin": "IRO1DGAN0001", "sector_code": "64", "base_price": 3100.0, "volatility": 0.028},
    {"ticker": "تپسی", "name_fa": "پیشگامان فن آوری و دانش آرامیس", "isin": "IRO3TPSI0001", "sector_code": "64", "base_price": 6800.0, "volatility": 0.030},

    # حمل و نقل، انبوه‌سازی و انرژی
    {"ticker": "حکشتی", "name_fa": "کشتیرانی جمهوری اسلامی ایران", "isin": "IRO1KSHZ0001", "sector_code": "40", "base_price": 14200.0, "volatility": 0.022},
    {"ticker": "رمپنا", "name_fa": "گروه مپنا", "isin": "IRO1MAPN0001", "sector_code": "38", "base_price": 10800.0, "volatility": 0.018},
    {"ticker": "ثفارس", "name_fa": "عمران و مسکن سازان فارس", "isin": "IRO1OMSF0001", "sector_code": "70", "base_price": 8900.0, "volatility": 0.032},
    {"ticker": "ثامید", "name_fa": "توسعه و عمران امید", "isin": "IRO1TAMD0001", "sector_code": "70", "base_price": 1700.0, "volatility": 0.026},
]


class FixtureReplayAdapter(BaseDataAdapter):
    """
    Generates deterministic, mathematically consistent Iranian historical price,
    client-type and orderbook data for development and regression testing.
    """

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)

    async def fetch_instrument_master(self) -> list[dict]:
        res = []
        for i, item in enumerate(FIXTURE_INSTRUMENTS):
            res.append({
                "source_instrument_code": f"INS_{i+1001}",
                "isin": item["isin"],
                "ticker": normalize_persian_text(item["ticker"]),
                "ticker_normalized": normalize_ticker(item["ticker"]),
                "name_fa": normalize_persian_text(item["name_fa"]),
                "market": "TSE",
                "board": "بازار اول (تابلوی اصلی)",
                "sector_code": item["sector_code"],
                "base_volume": int(item["base_price"] * 100),
            })
        return res

    async def fetch_eod_history(self, symbol_or_code: str, days: int = 260) -> list[dict]:
        inst = next((x for x in FIXTURE_INSTRUMENTS if x["ticker"] == symbol_or_code or x["isin"] == symbol_or_code), FIXTURE_INSTRUMENTS[0])
        target_price = float(inst["base_price"])
        volatility = inst["volatility"]

        # Collect trading dates going backwards from today
        trading_dates = []
        current_d = date.today()
        while len(trading_dates) < days:
            if current_d.weekday() in (0, 1, 2, 5, 6):  # Sat, Sun, Mon, Tue, Wed
                trading_dates.append(current_d)
            current_d -= timedelta(days=1)
        
        # Reverse to chronological order (oldest -> newest)
        trading_dates.reverse()

        # Walk backward from today's target price to get price levels
        prices = [target_price]
        curr = target_price
        for _ in range(days - 1):
            daily_return = self.rng.gauss(0.0006, volatility)
            daily_return = max(-0.0495, min(0.0495, daily_return))
            prev = round(curr / (1.0 + daily_return))
            prices.append(prev)
            curr = prev

        prices.reverse()  # Now prices[0] is oldest, prices[-1] is target_price (today)

        bars = []
        for i, t_date in enumerate(trading_dates):
            close_price = float(prices[i])
            yesterday_price = float(prices[i - 1]) if i > 0 else float(round(close_price * 0.99))
            daily_ret = (close_price - yesterday_price) / yesterday_price if yesterday_price > 0 else 0.0
            
            open_price = float(round(yesterday_price * (1.0 + self.rng.gauss(daily_ret * 0.3, 0.004))))
            high_price = float(max(open_price, close_price, round(yesterday_price * (1.0 + min(0.05, max(daily_ret, self.rng.uniform(0.0, 0.03)))))))
            low_price = float(min(open_price, close_price, round(yesterday_price * (1.0 + max(-0.05, min(daily_ret, -self.rng.uniform(0.0, 0.03)))))))
            last_price = close_price

            allowed_min = float(round(yesterday_price * 0.95))
            allowed_max = float(round(yesterday_price * 1.05))

            volume = int(self.rng.lognormvariate(15.5, 0.8))
            value = float(volume * close_price)
            trade_count = max(100, int(volume / self.rng.uniform(2000, 6000)))

            bars.append({
                "trading_date": t_date.isoformat(),
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "last": last_price,
                "yesterday_price": yesterday_price,
                "volume": volume,
                "value": value,
                "trade_count": trade_count,
                "allowed_min": allowed_min,
                "allowed_max": allowed_max,
            })

        return bars

    async def fetch_market_watch(self) -> list[dict]:
        res = []
        for inst in FIXTURE_INSTRUMENTS:
            price = inst["base_price"] * (1.0 + self.rng.gauss(0.01, 0.02))
            res.append({
                "insCode": f"INS_{inst['ticker']}",
                "lVal30": inst["ticker"],
                "lVal18": inst["name_fa"],
                "lVal18AFC": inst["isin"],
                "pClosing": round(price),
                "pDrCotVal": round(price),
                "priceYesterday": round(inst["base_price"]),
                "qTotTran5J": int(self.rng.uniform(5_000_000, 50_000_000)),
                "qTotCap": float(price * 10_000_000),
                "zTotTran": int(self.rng.uniform(2000, 15000)),
            })
        return res

    async def fetch_client_type_history(self, symbol_or_code: str, days: int = 260) -> list[dict]:
        eod_bars = await self.fetch_eod_history(symbol_or_code, days)
        res = []
        for bar in eod_bars:
            vol = bar["volume"]
            real_buy_ratio = self.rng.uniform(0.55, 0.90)
            real_sell_ratio = self.rng.uniform(0.50, 0.85)

            real_buy_vol = int(vol * real_buy_ratio)
            legal_buy_vol = vol - real_buy_vol
            real_sell_vol = int(vol * real_sell_ratio)
            legal_sell_vol = vol - real_sell_vol

            real_buy_cnt = max(50, int(real_buy_vol / self.rng.uniform(3000, 8000)))
            real_sell_cnt = max(50, int(real_sell_vol / self.rng.uniform(2000, 6000)))

            res.append({
                "trading_date": bar["trading_date"],
                "real_buy_count": real_buy_cnt,
                "real_buy_volume": real_buy_vol,
                "real_buy_value": float(real_buy_vol * bar["close"]),
                "real_sell_count": real_sell_cnt,
                "real_sell_volume": real_sell_vol,
                "real_sell_value": float(real_sell_vol * bar["close"]),
                "legal_buy_count": max(1, int(legal_buy_vol / 50000)),
                "legal_buy_volume": legal_buy_vol,
                "legal_buy_value": float(legal_buy_vol * bar["close"]),
                "legal_sell_count": max(1, int(legal_sell_vol / 50000)),
                "legal_sell_volume": legal_sell_vol,
                "legal_sell_value": float(legal_sell_vol * bar["close"]),
            })
        return res

    async def fetch_orderbook_depth(self, symbol_or_code: str) -> dict | None:
        inst = next((x for x in FIXTURE_INSTRUMENTS if x["ticker"] == symbol_or_code), FIXTURE_INSTRUMENTS[0])
        p = inst["base_price"]
        levels = []
        for lv in range(1, 6):
            levels.append({
                "level": lv,
                "bid_price": round(p - (lv * 10)),
                "bid_volume": int(self.rng.uniform(50_000, 500_000)),
                "bid_count": int(self.rng.uniform(5, 50)),
                "ask_price": round(p + (lv * 10)),
                "ask_volume": int(self.rng.uniform(40_000, 450_000)),
                "ask_count": int(self.rng.uniform(4, 45)),
            })
        return {"bestLimits": levels}
