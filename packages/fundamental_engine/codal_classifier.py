"""Codal / SEDRA Disclosures Intelligent Classifier & Sentiment Extractor."""
import re
from typing import Any, Dict


FILING_PATTERNS = [
    {
        "type": "monthly_sales",
        "name_fa": "گزارش فعالیت ماهانه (تولید و فروش)",
        "patterns": [r"گزارش فعالیت ماهانه", r"فعالیت ۱ ماهه", r"درآمد شناسایی شده"],
        "default_impact": 6.5,
    },
    {
        "type": "interim_statement",
        "name_fa": "صورت‌های مالی میاندوره‌ای",
        "patterns": [r"صورت‌های مالی", r"اطلاعات و صورت‌های مالی", r"۳ ماهه", r"۶ ماهه", r"۹ ماهه", r"۱۲ ماهه"],
        "default_impact": 8.0,
    },
    {
        "type": "material_disclosure_a",
        "name_fa": "افشای اطلاعات بااهمیت - گروه الف",
        "patterns": [r"افشای اطلاعات بااهمیت.*گروه الف", r"اطلاعات بااهمیت - گروه الف"],
        "default_impact": 9.0,
    },
    {
        "type": "material_disclosure_b",
        "name_fa": "افشای اطلاعات بااهمیت - گروه ب",
        "patterns": [r"افشای اطلاعات بااهمیت.*گروه ب", r"اطلاعات بااهمیت - گروه ب"],
        "default_impact": 6.0,
    },
    {
        "type": "capital_increase",
        "name_fa": "پیشنهاد و تصمیمات افزایش سرمایه",
        "patterns": [r"افزایش سرمایه", r"توجیهی افزایش سرمایه", r"ثبت افزایش سرمایه", r"تجدید ارزیابی"],
        "default_impact": 8.5,
    },
    {
        "type": "general_meeting",
        "name_fa": "مجمع عمومی و تقسیم سود نقدی",
        "patterns": [r"مجمع عمومی", r"تصمیمات مجمع", r"تقسیم سود", r"سود نقدی هر سهم"],
        "default_impact": 7.0,
    },
]

POSITIVE_KEYWORDS = [
    "افزایش درآمد", "رشد سود", "رشد ۶۰", "رشد ۵۰", "رشد ۴۰", "رشد ۳۰",
    "برنده شدن در مناقصه", "دریافت مجوز نرخ جدید", "تعدیل مثبت",
    "افزایش سرمایه از تجدید", "سود خالص افزایش", "رکورد تولید",
    "افزایش نرخ فروش", "صادرات موفق", "تسویه بدهی", "افزایش سودآوری",
]

NEGATIVE_KEYWORDS = [
    "توقف تولید", "کاهش سود", "تعدیل منفی", "قطعی گاز", "قطعی برق",
    "افت تقاضا", "زیان انباشته", "مشمول ماده ۱۴۱", "شکایت حقوقی",
    "عدم حصول توافق", "جریمه مالیاتی", "کاهش حاشیه سود",
]


def classify_codal_filing(title: str, body: str = "") -> Dict[str, Any]:
    """تشخیص نوع اطلاعیه کدال بر اساس عنوان و متن."""
    filing_type = "other"
    filing_type_fa = "اطلاعیه و شفاف‌سازی عمومی"
    impact_score = 5.0

    combined_text = f"{title} {body}"

    for p in FILING_PATTERNS:
        for pat in p["patterns"]:
            if re.search(pat, combined_text, re.IGNORECASE):
                filing_type = p["type"]
                filing_type_fa = p["name_fa"]
                impact_score = p["default_impact"]
                break
        if filing_type != "other":
            break

    sentiment_res = determine_filing_sentiment(title, body)

    return {
        "filing_type": filing_type,
        "filing_type_fa": filing_type_fa,
        "sentiment": sentiment_res["sentiment"],
        "sentiment_fa": sentiment_res["sentiment_fa"],
        "impact_score": impact_score,
        "summary_fa": sentiment_res["summary_fa"],
    }


def determine_filing_sentiment(title: str, body: str = "") -> Dict[str, Any]:
    """تعیین بار روانی و اثرگذاری قیمتی اطلاعیه کدال (مثبت، منفی یا خنثی)."""
    text = f"{title} {body}".lower()

    pos_hits = sum(1 for kw in POSITIVE_KEYWORDS if kw in text)
    neg_hits = sum(1 for kw in NEGATIVE_KEYWORDS if kw in text)

    # Check for monthly sales surge
    if "گزارش فعالیت ماهانه" in text or "درآمد" in text:
        if "رشد" in text or "افزایش" in text:
            pos_hits += 2

    # Check for Material Disclosure A
    if "گروه الف" in text:
        if neg_hits == 0:
            pos_hits += 2

    if pos_hits > neg_hits:
        sentiment = "positive"
        sentiment_fa = "مثبت و محرک رشد سهم"
        summary = "اطلاعیه حاوی سیگنال‌های مثبت سودآوری، رشد فروش یا افزایش سرمایه است."
    elif neg_hits > pos_hits:
        sentiment = "negative"
        sentiment_fa = "منفی و پرریسک (فشار فروش)"
        summary = "اطلاعیه شامل ریسک‌های عملیاتی، کاهش سودآوری یا عدم تحقق برنامه‌ها است."
    else:
        sentiment = "neutral"
        sentiment_fa = "خنثی و در محدوده تعادل"
        summary = "اطلاعیه در راستای شفاف‌سازی‌های روتین دوره‌ای و بدون نوسان غیرعادی است."

    return {
        "sentiment": sentiment,
        "sentiment_fa": sentiment_fa,
        "summary_fa": summary,
    }
