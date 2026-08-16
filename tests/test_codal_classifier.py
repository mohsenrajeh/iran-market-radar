"""Tests for Codal NLP Classification and Sentiment Analysis."""
import pytest
from packages.fundamental_engine.codal_classifier import (
    classify_codal_filing,
    determine_filing_sentiment,
)


def test_classify_monthly_sales_filing():
    """Verify monthly sales report classification and positive sentiment on sales surge."""
    title = "گزارش فعالیت ماهانه دوره ۱ ماهه منتهی به ۱۴۰۴/۱۲/۲۹"
    body = "مبلغ فروش شرکت فولاد مبارکه در این ماه با رشد ۵۲ درصدی به رکورد جدیدی رسید."
    res = classify_codal_filing(title, body)

    assert res["filing_type"] == "monthly_sales"
    assert "فعالیت ماهانه" in res["filing_type_fa"]
    assert res["sentiment"] == "positive"
    assert res["impact_score"] >= 6.0


def test_classify_material_disclosure_a():
    """Verify Material Disclosure A is recognized with high impact score."""
    title = "افشای اطلاعات بااهمیت - (نتایج شرکت در مناقصه فروش صادراتی) - گروه الف"
    body = "انعقاد قرارداد جدید فروش صادراتی به ارزش ۵۰ میلیون دلار و افزایش سودآوری."
    res = classify_codal_filing(title, body)

    assert res["filing_type"] == "material_disclosure_a"
    assert res["impact_score"] >= 8.5
    assert res["sentiment"] == "positive"


def test_classify_negative_filing():
    """Verify negative keywords result in negative sentiment."""
    title = "شفاف‌سازی در خصوص توقف تولید ناشی از قطعی گاز"
    body = "توقف بخشی از خطوط تولید به مدت ۲ هفته به دلیل افت فشار گاز و کاهش سود."
    res = classify_codal_filing(title, body)

    assert res["sentiment"] == "negative"
    assert "منفی" in res["sentiment_fa"]
