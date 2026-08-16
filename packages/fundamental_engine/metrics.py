"""Fundamental Metrics & Piotroski Financial Health Engine for Iranian Stocks."""
from typing import Any, Dict


def compute_piotroski_f_score(data: Dict[str, Any]) -> int:
    """
    محاسبه امتیاز ۹‌معیاره پیوتروسکی (Piotroski F-Score) برای سنجش سلامت مالی شرکت:
    - سودآوری (Profitability): ۴ امتیاز (ROA مثبت، جریان نقد عملیاتی مثبت، رشد ROA، جریان نقد بیش از سود خالص)
    - اهرم و نقدینگی (Leverage & Liquidity): ۳ امتیاز (کاهش نسبت بدهی، افزایش نسبت جاری، عدم انتشار سهام جدید)
    - کارایی عملیاتی (Operating Efficiency): ۲ امتیاز (رشد حاشیه سود ناخالص، رشد گردش دارایی‌ها)
    خروجی: عددی بین ۰ تا ۹ (۸-۹: عالی، ۵-۷: متوسط و پایدار، ۰-۴: پرریسک و ضعیف).
    """
    score = 0
    
    # 1. ROA > 0
    roa = data.get("roa_pct", 0.0)
    if roa > 0:
        score += 1
        
    # 2. Operating Cash Flow (CFO) > 0
    cfo = data.get("cfo_rials", 1.0)
    if cfo > 0:
        score += 1
        
    # 3. ROA growth > 0 (current year > previous year)
    roa_prior = data.get("roa_prior_pct", roa - 1.0)
    if roa > roa_prior:
        score += 1
        
    # 4. CFO > Net Income (کیفیت سودآوری)
    net_income = data.get("net_income_rials", 0.0)
    if cfo >= net_income:
        score += 1
        
    # 5. Long-term Debt ratio decreased
    debt_ratio = data.get("debt_to_equity", 0.5)
    debt_prior = data.get("debt_to_equity_prior", debt_ratio + 0.1)
    if debt_ratio <= debt_prior:
        score += 1
        
    # 6. Current Ratio increased
    current_ratio = data.get("current_ratio", 1.2)
    cr_prior = data.get("current_ratio_prior", current_ratio - 0.1)
    if current_ratio >= cr_prior:
        score += 1
        
    # 7. No dilution (shares count did not increase by private issue)
    diluted = data.get("shares_diluted", False)
    if not diluted:
        score += 1
        
    # 8. Gross Margin increased
    gm = data.get("gross_margin_pct", 25.0)
    gm_prior = data.get("gross_margin_prior_pct", gm - 1.0)
    if gm >= gm_prior:
        score += 1
        
    # 9. Asset Turnover increased
    asset_turnover = data.get("asset_turnover", 0.8)
    at_prior = data.get("asset_turnover_prior", asset_turnover - 0.05)
    if asset_turnover >= at_prior:
        score += 1
        
    return min(9, max(0, score))


def compute_valuation_multiples(
    price: float,
    eps: float,
    sales_per_share: float,
    book_value_per_share: float,
    dps: float = 0.0,
    sector_p_e: float = 7.0,
) -> Dict[str, float]:
    """محاسبه ضرایب ارزندگی نسبت به قیمت فعلی."""
    p_e = (price / eps) if eps > 0 else 0.0
    p_s = (price / sales_per_share) if sales_per_share > 0 else 0.0
    p_b = (price / book_value_per_share) if book_value_per_share > 0 else 0.0
    div_yield = (dps / price * 100) if price > 0 and dps > 0 else 0.0
    
    return {
        "p_e_ratio": round(p_e, 2),
        "sector_p_e": round(sector_p_e, 2),
        "p_s_ratio": round(p_s, 2),
        "p_b_ratio": round(p_b, 2),
        "dividend_yield": round(div_yield, 2),
    }


def evaluate_fundamental_score(
    p_e: float,
    sector_p_e: float,
    p_s: float,
    roe_pct: float,
    net_margin_pct: float,
    sales_growth_yoy: float,
    piotroski_score: int,
    debt_to_equity: float,
) -> Dict[str, Any]:
    """
    ارزیابی و امتیازدهی چندبعدی بنیادی (Fundamental Score 0-100) و تعیین وضعیت ارزندگی:
    1. ارزندگی نسبی P/E نسبت به صنعت (۲۵ امتیاز)
    2. بازده حقوق صاحبان سهام ROE (۲۰ امتیاز)
    3. رشد مبلغ فروش سالانه YoY (۲۰ امتیاز)
    4. سلامت مالی و پیوتروسکی F-Score (۲۰ امتیاز)
    5. حاشیه سود خالص و نسبت اهرمی بدهی (۱۵ امتیاز)
    """
    score = 0.0
    
    # 1. P/E vs Sector P/E (Max 25 pts)
    if p_e > 0 and sector_p_e > 0:
        pe_discount = (sector_p_e - p_e) / sector_p_e
        if pe_discount > 0.25:  # Over 25% discount to sector
            score += 25.0
        elif pe_discount > 0:
            score += 18.0 + pe_discount * 25.0
        elif pe_discount > -0.2:
            score += 12.0
        else:
            score += 5.0
    elif p_e > 0 and p_e < 6.0:
        score += 20.0
    else:
        score += 8.0
        
    # 2. ROE (Max 20 pts)
    if roe_pct >= 40.0:
        score += 20.0
    elif roe_pct >= 25.0:
        score += 15.0
    elif roe_pct >= 15.0:
        score += 10.0
    elif roe_pct > 0:
        score += 5.0
        
    # 3. Sales Growth YoY (Max 20 pts)
    if sales_growth_yoy >= 50.0:
        score += 20.0
    elif sales_growth_yoy >= 30.0:
        score += 16.0
    elif sales_growth_yoy >= 15.0:
        score += 11.0
    elif sales_growth_yoy > 0:
        score += 6.0
        
    # 4. Piotroski F-Score (Max 20 pts)
    score += (piotroski_score / 9.0) * 20.0
    
    # 5. Margins & Solvency (Max 15 pts)
    if net_margin_pct >= 25.0:
        score += 8.0
    elif net_margin_pct >= 15.0:
        score += 5.0
    elif net_margin_pct > 0:
        score += 2.0
        
    if debt_to_equity <= 0.6:
        score += 7.0
    elif debt_to_equity <= 1.2:
        score += 4.0
    else:
        score += 1.0
        
    final_score = round(min(100.0, max(10.0, score)), 1)
    
    # Determine Grade
    if final_score >= 82.0:
        grade = "A+"
    elif final_score >= 70.0:
        grade = "A"
    elif final_score >= 55.0:
        grade = "B"
    else:
        grade = "C"
        
    # Valuation Status
    if p_e > 0 and sector_p_e > 0 and (p_e < sector_p_e * 0.85) and roe_pct >= 20.0:
        val_status = "undervalued"
        val_status_fa = "ارزنده و دارای حباب منفی (پتانسیل رشد بالا)"
    elif p_e > sector_p_e * 1.3 or (roe_pct < 8.0 and p_e > 10.0):
        val_status = "overvalued"
        val_status_fa = "گران و بالاتر از ارزش ذاتی (ریسک اصلاح)"
    else:
        val_status = "fair"
        val_status_fa = "قیمت منصفانه و تعادلی"
        
    summary = (
        f"امتیاز بنیادی {final_score:.0f} (رتبه {grade}) • وضعیت: {val_status_fa} • "
        f"نسبت P/E سهم {p_e:.1f} در برابر P/E گروه {sector_p_e:.1f} • "
        f"بازده حقوق صاحبان سهام (ROE) معادل {roe_pct:.1f}٪ با رشد فروش {sales_growth_yoy:.1f}٪"
    )
    
    return {
        "fundamental_score": final_score,
        "fundamental_grade": grade,
        "valuation_status": val_status,
        "valuation_status_fa": val_status_fa,
        "analysis_summary_fa": summary,
    }
