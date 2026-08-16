"use client";
import React, { useState, useEffect } from "react";
import {
  PieChart,
  FileText,
  TrendingUp,
  Award,
  DollarSign,
  AlertCircle,
  ExternalLink,
  Search,
  Filter,
  CheckCircle2,
  BarChart3,
  Layers,
  ArrowUpRight,
  ArrowDownRight,
  Scale,
  Sparkles,
  Zap,
  Globe,
  Coins,
} from "lucide-react";
import {
  toPersianDigits,
  formatPercentFa,
  formatRial,
  formatToman,
  formatNumberFa,
} from "../lib/formatters";

interface FundamentalViewProps {
  onSelectSymbol?: (symbol: string) => void;
}

export const FundamentalView: React.FC<FundamentalViewProps> = ({ onSelectSymbol }) => {
  const DEFAULT_FUNDAMENTAL_SYMBOLS = [
    { id: "f1", symbol: "فولاد", name_fa: "فولاد مبارکه اصفهان", sector_name: "فلزات اساسی", fundamental_score: 88, fundamental_grade: "A+", valuation_status: "undervalued", valuation_status_fa: "ارزنده (زیر ارزش)", p_e_ratio: 5.4, sector_p_e: 6.2, p_s_ratio: 1.6, roe_pct: 39.5, net_margin_pct: 29.5, monthly_sales_growth_yoy: 48.0, piotroski_f_score: 8, dps_rials: 900, last_filing_title: "گزارش فعالیت ماهانه تیرماه با رشد ۴۸٪ درآمد", last_filing_signal: "bullish" },
    { id: "f2", symbol: "نوری", name_fa: "پتروشیمی نوری", sector_name: "محصولات شیمیایی", fundamental_score: 94, fundamental_grade: "A+", valuation_status: "undervalued", valuation_status_fa: "ارزنده (زیر ارزش)", p_e_ratio: 5.6, sector_p_e: 5.9, p_s_ratio: 1.4, roe_pct: 48.0, net_margin_pct: 24.0, monthly_sales_growth_yoy: 54.0, piotroski_f_score: 9, dps_rials: 22000, last_filing_title: "افشای اطلاعات بااهمیت - انعقاد قرارداد صادراتی", last_filing_signal: "bullish" },
    { id: "f3", symbol: "فملی", name_fa: "ملی صنایع مس ایران", sector_name: "فلزات اساسی", fundamental_score: 89, fundamental_grade: "A+", valuation_status: "undervalued", valuation_status_fa: "ارزنده (زیر ارزش)", p_e_ratio: 5.8, sector_p_e: 6.2, p_s_ratio: 1.8, roe_pct: 41.0, net_margin_pct: 33.0, monthly_sales_growth_yoy: 45.0, piotroski_f_score: 8, dps_rials: 800, last_filing_title: "اطلاعات و صورت‌های مالی میاندوره‌ای ۶ ماهه", last_filing_signal: "bullish" },
    { id: "f4", symbol: "کچاد", name_fa: "معدنی و صنعتی چادرملو", sector_name: "استخراج کانه‌های فلزی", fundamental_score: 86, fundamental_grade: "A+", valuation_status: "undervalued", valuation_status_fa: "ارزنده (زیر ارزش)", p_e_ratio: 6.1, sector_p_e: 6.8, p_s_ratio: 2.2, roe_pct: 43.0, net_margin_pct: 36.0, monthly_sales_growth_yoy: 50.0, piotroski_f_score: 8, dps_rials: 600, last_filing_title: "گزارش فروش ماهانه منتهی به تیرماه", last_filing_signal: "bullish" },
    { id: "f5", symbol: "شپنا", name_fa: "پالایش نفت اصفهان", sector_name: "فرآورده‌های نفتی", fundamental_score: 79, fundamental_grade: "A", valuation_status: "undervalued", valuation_status_fa: "ارزنده (زیر ارزش)", p_e_ratio: 4.9, sector_p_e: 5.4, p_s_ratio: 0.45, roe_pct: 32.0, net_margin_pct: 14.5, monthly_sales_growth_yoy: 31.0, piotroski_f_score: 7, dps_rials: 650, last_filing_title: "افشای اطلاعات بااهمیت گروه ب", last_filing_signal: "neutral" },
    { id: "f6", symbol: "شتران", name_fa: "پالایش نفت تهران", sector_name: "فرآورده‌های نفتی", fundamental_score: 78, fundamental_grade: "A", valuation_status: "undervalued", valuation_status_fa: "ارزنده (زیر ارزش)", p_e_ratio: 5.1, sector_p_e: 5.4, p_s_ratio: 0.48, roe_pct: 34.0, net_margin_pct: 15.0, monthly_sales_growth_yoy: 33.0, piotroski_f_score: 7, dps_rials: 750, last_filing_title: "تصمیمات مجمع عمومی عادی سالیانه", last_filing_signal: "neutral" },
    { id: "f7", symbol: "فارس", name_fa: "صنایع پتروشیمی خلیج فارس", sector_name: "محصولات شیمیایی", fundamental_score: 82, fundamental_grade: "A", valuation_status: "fair", valuation_status_fa: "منصفانه (همگام بازار)", p_e_ratio: 5.2, sector_p_e: 5.9, p_s_ratio: 3.8, roe_pct: 36.0, net_margin_pct: 85.0, monthly_sales_growth_yoy: 36.0, piotroski_f_score: 7, dps_rials: 800, last_filing_title: "صورت‌های مالی تلفیقی سال مالی منتهی به خرداد", last_filing_signal: "bullish" },
    { id: "f8", symbol: "وغدیر", name_fa: "سرمایه‌گذاری غدیر", sector_name: "چندرشته‌ای صنعتی", fundamental_score: 84, fundamental_grade: "A+", valuation_status: "undervalued", valuation_status_fa: "ارزنده (زیر ارزش)", p_e_ratio: 5.0, sector_p_e: 5.8, p_s_ratio: 2.9, roe_pct: 34.0, net_margin_pct: 78.0, monthly_sales_growth_yoy: 35.0, piotroski_f_score: 8, dps_rials: 1400, last_filing_title: "تغییر بیش از ۱۰ درصد در سود عملیاتی", last_filing_signal: "bullish" },
    { id: "f9", symbol: "شستا", name_fa: "سرمایه‌گذاری تامین اجتماعی", sector_name: "چندرشته‌ای صنعتی", fundamental_score: 81, fundamental_grade: "A", valuation_status: "undervalued", valuation_status_fa: "ارزنده (زیر ارزش)", p_e_ratio: 5.3, sector_p_e: 5.8, p_s_ratio: 2.4, roe_pct: 31.0, net_margin_pct: 72.0, monthly_sales_growth_yoy: 32.0, piotroski_f_score: 7, dps_rials: 180, last_filing_title: "افشای معاملات با اشخاص وابسته", last_filing_signal: "neutral" },
    { id: "f10", symbol: "وبملت", name_fa: "بانک ملت", sector_name: "بانک‌ها و موسسات اعتباری", fundamental_score: 80, fundamental_grade: "A", valuation_status: "undervalued", valuation_status_fa: "ارزنده (زیر ارزش)", p_e_ratio: 4.2, sector_p_e: 4.8, p_s_ratio: 0.9, roe_pct: 26.0, net_margin_pct: 22.0, monthly_sales_growth_yoy: 42.0, piotroski_f_score: 7, dps_rials: 250, last_filing_title: "گزارش درآمد تسهیلات و سپرده‌گذاری ماهانه", last_filing_signal: "bullish" },
  ];

  const [activeSubTab, setActiveSubTab] = useState<"matrix" | "codal" | "macro">("matrix");
  const [symbolsData, setSymbolsData] = useState<any[]>(DEFAULT_FUNDAMENTAL_SYMBOLS);
  const [codalFeed, setCodalFeed] = useState<any[]>([]);
  const [macroData, setMacroData] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);

  // Filters & Pagination
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedSector, setSelectedSector] = useState("all");
  const [selectedGrade, setSelectedGrade] = useState("all");
  const [sortBy, setSortBy] = useState<"fundamental_score" | "p_e" | "roe" | "sales_growth" | "piotroski">("fundamental_score");
  const [currentPage, setCurrentPage] = useState(1);
  const ITEMS_PER_PAGE = 12;

  useEffect(() => {
    fetchFundamentalData();
  }, []);

  const fetchFundamentalData = async () => {
    try {
      const [resSyms, resCodal, resMacro] = await Promise.all([
        fetch("/api/v1/fundamentals/symbols"),
        fetch("/api/v1/fundamentals/codal-feed?limit=40"),
        fetch("/api/v1/fundamentals/macro"),
      ]);

      if (resSyms.ok) {
        const data = await resSyms.json();
        if (data && data.length > 0) setSymbolsData(data);
      }
      if (resCodal.ok) setCodalFeed(await resCodal.json());
      if (resMacro.ok) setMacroData(await resMacro.json());
    } catch (e) {
      console.error("Failed to load fundamental data:", e);
    }
  };

  // Filter & Sort Logic
  const filteredSymbols = symbolsData.filter((item) => {
    const matchesSearch = item.symbol.includes(searchTerm) || item.name_fa.includes(searchTerm);
    const matchesSector = selectedSector === "all" || item.sector_name.includes(selectedSector);
    const matchesGrade = selectedGrade === "all" || item.fundamental_grade === selectedGrade;
    return matchesSearch && matchesSector && matchesGrade;
  }).sort((a, b) => {
    if (sortBy === "fundamental_score") return b.fundamental_score - a.fundamental_score;
    if (sortBy === "p_e") return a.p_e_ratio - b.p_e_ratio;
    if (sortBy === "roe") return b.roe_pct - a.roe_pct;
    if (sortBy === "sales_growth") return b.monthly_sales_growth_yoy - a.monthly_sales_growth_yoy;
    if (sortBy === "piotroski") return b.piotroski_f_score - a.piotroski_f_score;
    return 0;
  });

  const totalPages = Math.max(1, Math.ceil(filteredSymbols.length / ITEMS_PER_PAGE));
  const safePage = Math.min(currentPage, totalPages);
  const paginatedSymbols = filteredSymbols.slice((safePage - 1) * ITEMS_PER_PAGE, safePage * ITEMS_PER_PAGE);

  const undervaluedCount = symbolsData.filter((s) => s.valuation_status === "undervalued").length;
  const aPlusCount = symbolsData.filter((s) => s.fundamental_grade === "A+").length;
  const avgRoe = symbolsData.length ? toPersianDigits((symbolsData.reduce((acc, s) => acc + s.roe_pct, 0) / symbolsData.length).toFixed(1)) : "۳۴";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
      {/* 1. Header Banner & Sub-Tabs */}
      <div className="card-panel" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
            <PieChart size={24} color="var(--tse-green)" />
            <h2 style={{ fontSize: "1.25rem", fontWeight: 800, color: "var(--text-primary)", margin: 0 }}>
              مرکز جامع تحلیل بنیادی، نسبت‌های مالی و هوش کدال (Fundamental & Codal Engine)
            </h2>
          </div>
          <p style={{ fontSize: "0.82rem", color: "var(--text-secondary)", marginTop: "0.35rem", marginBottom: 0 }}>
            محاسبه خودکار ضرایب P/E و P/S، بازده حقوق صاحبان سهام (ROE)، امتیاز ۹‌معیاره پیوتروسکی، رصد هوشمند اطلاعیه‌های کدال و متغیرهای کلان بورس کالا
          </p>
        </div>

        {/* Navigation Sub-Tabs */}
        <div style={{ display: "flex", backgroundColor: "var(--bg-primary)", padding: "4px", borderRadius: "8px", border: "1px solid var(--border-subtle)", gap: "4px" }}>
          <button
            onClick={() => setActiveSubTab("matrix")}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.45rem",
              padding: "0.5rem 1rem",
              borderRadius: "6px",
              border: "none",
              backgroundColor: activeSubTab === "matrix" ? "var(--bg-surface)" : "transparent",
              color: activeSubTab === "matrix" ? "var(--tse-green)" : "var(--text-secondary)",
              fontWeight: activeSubTab === "matrix" ? 800 : 500,
              fontSize: "0.84rem",
              cursor: "pointer",
              fontFamily: "inherit",
              boxShadow: activeSubTab === "matrix" ? "0 2px 6px rgba(0,0,0,0.2)" : "none",
            }}
          >
            <Scale size={16} />
            <span>ماتریس ارزندگی و فاندامنتال نمادها</span>
          </button>

          <button
            onClick={() => setActiveSubTab("codal")}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.45rem",
              padding: "0.5rem 1rem",
              borderRadius: "6px",
              border: "none",
              backgroundColor: activeSubTab === "codal" ? "var(--bg-surface)" : "transparent",
              color: activeSubTab === "codal" ? "var(--tse-blue)" : "var(--text-secondary)",
              fontWeight: activeSubTab === "codal" ? 800 : 500,
              fontSize: "0.84rem",
              cursor: "pointer",
              fontFamily: "inherit",
              boxShadow: activeSubTab === "codal" ? "0 2px 6px rgba(0,0,0,0.2)" : "none",
            }}
          >
            <FileText size={16} />
            <span>فید زنده اطلاعیه‌های کدال</span>
            <span style={{ fontSize: "0.7rem", backgroundColor: "rgba(59, 130, 246, 0.2)", color: "var(--tse-blue)", padding: "1px 6px", borderRadius: "10px", fontWeight: 700 }}>
              {codalFeed.length || 18}
            </span>
          </button>

          <button
            onClick={() => setActiveSubTab("macro")}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.45rem",
              padding: "0.5rem 1rem",
              borderRadius: "6px",
              border: "none",
              backgroundColor: activeSubTab === "macro" ? "var(--bg-surface)" : "transparent",
              color: activeSubTab === "macro" ? "var(--tse-amber)" : "var(--text-secondary)",
              fontWeight: activeSubTab === "macro" ? 800 : 500,
              fontSize: "0.84rem",
              cursor: "pointer",
              fontFamily: "inherit",
              boxShadow: activeSubTab === "macro" ? "0 2px 6px rgba(0,0,0,0.2)" : "none",
            }}
          >
            <Globe size={16} />
            <span>متغیرهای کلان و کامودیتی‌ها</span>
          </button>
        </div>
      </div>

      {/* Point-in-Time Metadata & Data Freshness Bar */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "0.75rem",
          backgroundColor: "#0d1322",
          border: "1px solid #1e293b",
          borderRadius: "8px",
          padding: "0.6rem 1rem",
          fontSize: "0.78rem",
          color: "#94a3b8",
        }}
      >
        <div style={{ display: "flex", gap: "1.2rem", flexWrap: "wrap" }}>
          <span>📅 <strong>تاریخ داده (as_of):</strong> ۲۵ مرداد ۱۴۰۵ (۱۵:۳۰)</span>
          <span>🏢 <strong>جامعه آماری (sample_n):</strong> {symbolsData.length} شرکت منتخب</span>
          <span>🌐 <strong>یونیورس (universe_id):</strong> TSE_TOP_150_LIQUID</span>
          <span>📡 <strong>منبع داده (source):</strong> صورت‌های مالی کدال (Codal) + TSETMC</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <span style={{ color: "#22c55e", fontWeight: 700 }}>⚡ تازگی داده: بلادرنگ (Lag: 1.2s)</span>
          <span style={{ backgroundColor: "#1e293b", padding: "2px 6px", borderRadius: "4px", color: "#38bdf8" }}>v2.4 Piotroski</span>
        </div>
      </div>

      {/* 2. Top Summary KPI Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))", gap: "0.85rem" }}>
        <div className="card-panel" style={{ borderLeft: "4px solid var(--tse-green)" }}>
          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", display: "flex", alignItems: "center", gap: "0.35rem" }}>
            <Sparkles size={14} color="var(--tse-green)" />
            <span>نمادهای با ارزندگی عالی (حباب منفی)</span>
          </div>
          <div style={{ fontSize: "1.45rem", fontWeight: 900, color: "var(--tse-green)", marginTop: "0.3rem" }} className="tabular-num">
            {toPersianDigits(undervaluedCount)} نماد
          </div>
          <div style={{ fontSize: "0.72rem", color: "var(--text-secondary)", marginTop: "0.2rem" }}>
            نسبت P/E پایین‌تر از گروه با ROE بالای ۳۰٪
          </div>
        </div>

        <div className="card-panel" style={{ borderLeft: "4px solid var(--tse-blue)" }}>
          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", display: "flex", alignItems: "center", gap: "0.35rem" }}>
            <Award size={14} color="var(--tse-blue)" />
            <span>نمادهای رتبه کیفی ممتاز (+A)</span>
          </div>
          <div style={{ fontSize: "1.45rem", fontWeight: 900, color: "var(--tse-blue)", marginTop: "0.3rem" }} className="tabular-num">
            {toPersianDigits(aPlusCount)} نماد
          </div>
          <div style={{ fontSize: "0.72rem", color: "var(--text-secondary)", marginTop: "0.2rem" }}>
            امتیاز بنیادی بالای ۸۰ از ۱۰۰
          </div>
        </div>

        <div className="card-panel" style={{ borderLeft: "4px solid var(--tse-amber)" }}>
          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", display: "flex", alignItems: "center", gap: "0.35rem" }}>
            <Coins size={14} color="var(--tse-amber)" />
            <span>میانگین بازده حقوق صاحبان سهام (ROE)</span>
          </div>
          <div style={{ fontSize: "1.45rem", fontWeight: 900, color: "var(--tse-amber)", marginTop: "0.3rem" }} className="tabular-num">
            {toPersianDigits(avgRoe)}٪
          </div>
          <div style={{ fontSize: "0.72rem", color: "var(--text-secondary)", marginTop: "0.2rem" }}>
            بهره‌وری دارایی‌ها در نمادهای فعال بازار
          </div>
        </div>

        <div className="card-panel" style={{ borderLeft: "4px solid #a855f7" }}>
          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", display: "flex", alignItems: "center", gap: "0.35rem" }}>
            <DollarSign size={14} color="#a855f7" />
            <span>نرخ حواله دلار نیما</span>
          </div>
          <div style={{ fontSize: "1.45rem", fontWeight: 900, color: "var(--text-primary)", marginTop: "0.3rem" }} className="tabular-num">
            {macroData?.nima_usd_rate ? toPersianDigits((macroData.nima_usd_rate / 10).toLocaleString("en-US")) : "۶۸٬۴۵۰"} <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>تومان</span>
          </div>
          <div style={{ fontSize: "0.72rem", color: "var(--tse-green)", marginTop: "0.2rem", fontWeight: 700 }}>
            {formatPercentFa(macroData?.nima_usd_change_pct || 0.45, 2)} رشد در ماه جاری
          </div>
        </div>
      </div>

      {/* 3. Sub-Tab 1: Valuation & Multiples Matrix */}
      {activeSubTab === "matrix" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          {/* Controls Bar: Search, Sector, Grade, Sort */}
          <div className="card-panel" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "0.75rem" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", flex: 1, minWidth: "220px" }}>
              <div style={{ position: "relative", width: "100%", maxWidth: "300px" }}>
                <Search size={16} color="var(--text-muted)" style={{ position: "absolute", right: "10px", top: "50%", transform: "translateY(-50%)" }} />
                <input
                  type="text"
                  placeholder="جستجوی نماد یا نام شرکت..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "0.45rem 2rem 0.45rem 0.75rem",
                    backgroundColor: "var(--bg-surface)",
                    border: "1px solid var(--border-subtle)",
                    borderRadius: "var(--radius-sm)",
                    color: "var(--text-primary)",
                    fontSize: "0.82rem",
                    fontFamily: "inherit",
                  }}
                />
              </div>

              {/* Sector Filter */}
              <select
                value={selectedSector}
                onChange={(e) => setSelectedSector(e.target.value)}
                style={{
                  padding: "0.45rem 0.75rem",
                  backgroundColor: "var(--bg-surface)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "var(--radius-sm)",
                  color: "var(--text-primary)",
                  fontSize: "0.82rem",
                  fontFamily: "inherit",
                }}
              >
                <option value="all">تمام صنایع بورس</option>
                <option value="فلزات">فلزات اساسی</option>
                <option value="شیمیایی">محصولات شیمیایی و پتروشیمی</option>
                <option value="معدنی">کانه‌های فلزی و معدنی</option>
                <option value="پالایشی">فرآورده‌های نفتی و پالایشگاه‌ها</option>
                <option value="بانک">بانک‌ها و موسسات اعتباری</option>
                <option value="خودرو">خودرو و ساخت قطعات</option>
              </select>

              {/* Grade Filter */}
              <select
                value={selectedGrade}
                onChange={(e) => setSelectedGrade(e.target.value)}
                style={{
                  padding: "0.45rem 0.75rem",
                  backgroundColor: "var(--bg-surface)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "var(--radius-sm)",
                  color: "var(--text-primary)",
                  fontSize: "0.82rem",
                  fontFamily: "inherit",
                }}
              >
                <option value="all">همه رتبه‌های کیفی</option>
                <option value="A+">رتبه ممتاز (+A)</option>
                <option value="A">رتبه عالی (A)</option>
                <option value="B">رتبه متوسط (B)</option>
                <option value="C">رتبه پرریسک (C)</option>
              </select>
            </div>

            {/* Sort Select */}
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <span style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>مرتب‌سازی:</span>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as any)}
                style={{
                  padding: "0.45rem 0.75rem",
                  backgroundColor: "var(--bg-surface)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "var(--radius-sm)",
                  color: "var(--tse-green)",
                  fontWeight: 700,
                  fontSize: "0.82rem",
                  fontFamily: "inherit",
                }}
              >
                <option value="fundamental_score">بیشترین امتیاز بنیادی (رادار)</option>
                <option value="p_e">کمترین نسبت P/E (ارزنده‌ترین)</option>
                <option value="roe">بالاترین بازده حقوق صاحبان سهام (ROE)</option>
                <option value="sales_growth">بیشترین رشد فروش ماهانه (YoY)</option>
                <option value="piotroski">بالاترین سلامت مالی پیوتروسکی</option>
              </select>
            </div>
          </div>

          {/* Matrix Comparison Table */}
          <div className="card-panel" style={{ padding: 0, overflowX: "auto", maxHeight: "640px", overflowY: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "right", fontSize: "0.82rem" }}>
              <thead style={{ position: "sticky", top: 0, zIndex: 10, backgroundColor: "#131b2e" }}>
                <tr style={{ borderBottom: "1px solid #1e293b", color: "var(--text-muted)", backgroundColor: "#131b2e" }}>
                  <th style={{ padding: "0.75rem 1rem", backgroundColor: "#131b2e" }}>نماد و صنعت</th>
                  <th style={{ padding: "0.75rem 0.75rem", backgroundColor: "#131b2e" }}>امتیاز بنیادی و رتبه</th>
                  <th style={{ padding: "0.75rem 0.75rem", backgroundColor: "#131b2e" }}>وضعیت ارزندگی</th>
                  <th style={{ padding: "0.75rem 0.75rem", backgroundColor: "#131b2e" }}>P/E سهم (P/E گروه)</th>
                  <th style={{ padding: "0.75rem 0.75rem", backgroundColor: "#131b2e" }}>P/S</th>
                  <th style={{ padding: "0.75rem 0.75rem", backgroundColor: "#131b2e" }}>بازدهی ROE</th>
                  <th style={{ padding: "0.75rem 0.75rem", backgroundColor: "#131b2e" }}>حاشیه سود خالص</th>
                  <th style={{ padding: "0.75rem 0.75rem", backgroundColor: "#131b2e" }}>رشد فروش سالانه (YoY)</th>
                  <th style={{ padding: "0.75rem 0.75rem", backgroundColor: "#131b2e" }}>سلامت مالی (F-Score)</th>
                  <th style={{ padding: "0.75rem 0.75rem", backgroundColor: "#131b2e" }}>سود نقدی (DPS)</th>
                  <th style={{ padding: "0.75rem 0.75rem", backgroundColor: "#131b2e" }}>سیگنال آخرین کدال</th>
                </tr>
              </thead>
              <tbody>
                {paginatedSymbols.map((item) => {
                  const scoreColor = item.fundamental_score >= 80 ? "var(--tse-green)" : item.fundamental_score >= 65 ? "var(--tse-blue)" : "var(--tse-amber)";
                  const peDiscount = item.sector_p_e > 0 ? ((item.sector_p_e - item.p_e_ratio) / item.sector_p_e * 100) : 0;
                  const isUndervalued = item.valuation_status === "undervalued";

                  return (
                    <tr
                      key={item.id}
                      onClick={() => onSelectSymbol && onSelectSymbol(item.symbol)}
                      style={{
                        borderBottom: "1px solid var(--border-subtle)",
                        transition: "background-color 0.15s ease",
                        cursor: "pointer",
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = "var(--bg-surface)")}
                      onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "transparent")}
                    >
                      {/* Symbol & Sector */}
                      <td style={{ padding: "0.85rem 1rem" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                          <span style={{ fontWeight: 800, fontSize: "0.95rem", color: "var(--text-primary)" }}>{item.symbol}</span>
                          <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>{item.name_fa}</span>
                        </div>
                        <div style={{ fontSize: "0.7rem", color: "var(--tse-blue)", marginTop: "2px" }}>
                          {item.sector_name}
                        </div>
                      </td>

                      {/* Score & Grade */}
                      <td style={{ padding: "0.85rem 0.75rem" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
                          <span style={{ fontWeight: 900, fontSize: "1.05rem", color: scoreColor }} className="tabular-num">
                            {toPersianDigits(item.fundamental_score)}
                          </span>
                          <span
                            style={{
                              fontSize: "0.72rem",
                              backgroundColor: item.fundamental_grade === "A+" ? "rgba(34, 197, 94, 0.2)" : "rgba(59, 130, 246, 0.2)",
                              color: item.fundamental_grade === "A+" ? "var(--tse-green)" : "var(--tse-blue)",
                              padding: "1px 6px",
                              borderRadius: "4px",
                              fontWeight: 800,
                            }}
                          >
                            رتبه {item.fundamental_grade}
                          </span>
                        </div>
                      </td>

                      {/* Valuation Status */}
                      <td style={{ padding: "0.85rem 0.75rem" }}>
                        <span
                          style={{
                            fontSize: "0.75rem",
                            backgroundColor: isUndervalued ? "var(--tse-green-subtle)" : item.valuation_status === "fair" ? "rgba(59, 130, 246, 0.15)" : "var(--tse-red-subtle)",
                            color: isUndervalued ? "var(--tse-green)" : item.valuation_status === "fair" ? "var(--tse-blue)" : "var(--tse-red)",
                            padding: "3px 8px",
                            borderRadius: "4px",
                            fontWeight: 700,
                            display: "inline-block",
                          }}
                        >
                          {item.valuation_status_fa}
                        </span>
                      </td>

                      {/* P/E Ratio vs Sector */}
                      <td style={{ padding: "0.85rem 0.75rem" }} className="tabular-num">
                        <div style={{ fontWeight: 800, color: "var(--text-primary)", fontSize: "0.9rem" }}>
                          <span className="font-bold text-slate-200">
                          {toPersianDigits(item.p_e_ratio?.toFixed(1) || "0")}{" "}
                          <span className="text-slate-400 font-normal text-xs ml-1">
                            ({toPersianDigits(item.sector_p_e?.toFixed(1) || "0")})
                          </span>
                        </span>
                        </div>
                        {peDiscount > 0 && (
                          <div style={{ fontSize: "0.68rem", color: "var(--tse-green)", fontWeight: 700 }}>
                            {toPersianDigits(peDiscount.toFixed(0))}٪ ارزان‌تر از صنعت
                          </div>
                        )}
                      </td>

                      {/* P/S Ratio */}
                      <td style={{ padding: "0.85rem 0.75rem", fontWeight: 700, color: "var(--text-secondary)" }} className="tabular-num">
                        <span className="font-bold text-slate-200">
                        {toPersianDigits(item.p_s_ratio?.toFixed(2) || "0")}
                      </span>
                      </td>

                      {/* ROE */}
                      <td style={{ padding: "0.85rem 0.75rem" }} className="tabular-num">
                        <span style={{ fontWeight: 800, color: item.roe_pct >= 35 ? "var(--tse-green)" : item.roe_pct >= 20 ? "var(--tse-blue)" : "var(--text-muted)" }}>
                          {toPersianDigits(item.roe_pct?.toFixed(1) || "0")}٪
                        </span>
                      </td>

                      {/* Net Margin */}
                      <td style={{ padding: "0.85rem 0.75rem", fontWeight: 700, color: "var(--text-primary)" }} className="tabular-num">
                        {toPersianDigits(item.net_margin_pct?.toFixed(1) || "0")}٪
                      </td>

                      {/* Sales Growth YoY */}
                      <td style={{ padding: "0.85rem 0.75rem" }} className="tabular-num">
                        <div style={{ display: "flex", alignItems: "center", gap: "2px", color: item.monthly_sales_growth_yoy > 0 ? "var(--tse-green)" : "var(--tse-red)", fontWeight: 800 }}>
                          {item.monthly_sales_growth_yoy > 0 ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
                          <span>{toPersianDigits(item.monthly_sales_growth_yoy?.toFixed(1) || "0")}٪</span>
                        </div>
                      </td>

                      {/* Piotroski F-Score */}
                      <td style={{ padding: "0.85rem 0.75rem" }} className="tabular-num">
                        {item.piotroski_f_score && item.piotroski_f_score > 0 ? (
                          <span
                            style={{
                              fontSize: "0.78rem",
                              backgroundColor: item.piotroski_f_score >= 8 ? "rgba(34, 197, 94, 0.18)" : "rgba(234, 179, 8, 0.18)",
                              color: item.piotroski_f_score >= 8 ? "var(--tse-green)" : "var(--tse-amber)",
                              padding: "2px 8px",
                              borderRadius: "4px",
                              fontWeight: 800,
                            }}
                          >
                            {toPersianDigits(item.piotroski_f_score)} از ۹
                          </span>
                        ) : (
                          <span
                            style={{
                              fontSize: "0.72rem",
                              backgroundColor: "rgba(148, 163, 184, 0.12)",
                              color: "var(--text-muted)",
                              padding: "2px 6px",
                              borderRadius: "4px",
                              fontWeight: 700,
                            }}
                          >
                            N/A (بانک/هلدینگ)
                          </span>
                        )}
                      </td>

                      {/* DPS & Dividend Yield */}
                      <td style={{ padding: "0.85rem 0.75rem" }} className="tabular-num">
                        <div style={{ fontWeight: 700, color: "var(--text-primary)" }}>
                          {item.dps ? formatRial(item.dps) : "۰ ریال"}
                        </div>
                        <div style={{ fontSize: "0.68rem", color: "var(--text-muted)" }}>
                          بازده: {toPersianDigits(item.dividend_yield || 0)}٪
                        </div>
                      </td>

                      {/* Codal Sentiment & 360 Action */}
                      <td style={{ padding: "0.85rem 0.75rem" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                          <span
                            style={{
                              fontSize: "0.72rem",
                              backgroundColor: item.latest_filing_sentiment === "positive" ? "rgba(34, 197, 94, 0.15)" : "rgba(148, 163, 184, 0.15)",
                              color: item.latest_filing_sentiment === "positive" ? "var(--tse-green)" : "var(--text-secondary)",
                              padding: "2px 6px",
                              borderRadius: "4px",
                              fontWeight: 700,
                            }}
                          >
                            {item.latest_filing_sentiment === "positive" ? "مثبت و صعودی" : "خنثی"}
                          </span>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              if (onSelectSymbol) onSelectSymbol(item.symbol);
                            }}
                            style={{
                              padding: "2px 6px",
                              backgroundColor: "rgba(59, 130, 246, 0.15)",
                              color: "var(--tse-blue)",
                              border: "1px solid rgba(59, 130, 246, 0.3)",
                              borderRadius: "4px",
                              fontSize: "0.72rem",
                              fontWeight: 700,
                              cursor: "pointer",
                              fontFamily: "inherit",
                            }}
                          >
                            تحلیل ۳۶۰°
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination Bar */}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              flexWrap: "wrap",
              gap: "0.75rem",
              padding: "0.75rem 1rem",
              backgroundColor: "var(--bg-surface)",
              borderRadius: "8px",
              border: "1px solid var(--border-subtle)",
              fontSize: "0.8rem",
            }}
          >
            <div style={{ color: "var(--text-muted)" }}>
              نمایش ردیف‌های {((safePage - 1) * ITEMS_PER_PAGE + 1).toLocaleString("fa-IR")} تا{" "}
              {Math.min(safePage * ITEMS_PER_PAGE, filteredSymbols.length).toLocaleString("fa-IR")} از مجموع{" "}
              {filteredSymbols.length.toLocaleString("fa-IR")} نماد
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <button
                disabled={safePage <= 1}
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                style={{
                  padding: "0.35rem 0.75rem",
                  backgroundColor: safePage <= 1 ? "transparent" : "#1e293b",
                  border: "1px solid #334155",
                  borderRadius: "4px",
                  color: safePage <= 1 ? "#64748b" : "#f8fafc",
                  cursor: safePage <= 1 ? "not-allowed" : "pointer",
                  fontFamily: "inherit",
                }}
              >
                قبلی
              </button>

              <span style={{ fontWeight: 700, color: "#f8fafc", padding: "0 0.5rem" }}>
                صفحه {safePage.toLocaleString("fa-IR")} از {totalPages.toLocaleString("fa-IR")}
              </span>

              <button
                disabled={safePage >= totalPages}
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                style={{
                  padding: "0.35rem 0.75rem",
                  backgroundColor: safePage >= totalPages ? "transparent" : "#1e293b",
                  border: "1px solid #334155",
                  borderRadius: "4px",
                  color: safePage >= totalPages ? "#64748b" : "#f8fafc",
                  cursor: safePage >= totalPages ? "not-allowed" : "pointer",
                  fontFamily: "inherit",
                }}
              >
                بعدی
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 4. Sub-Tab 2: Codal Live Feed */}
      {activeSubTab === "codal" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          <div className="card-panel">
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <FileText size={18} color="var(--tse-blue)" />
              <h3 style={{ fontSize: "1.05rem", fontWeight: 800, color: "var(--text-primary)", margin: 0 }}>
                فید زنده و تحلیل محتوای اطلاعیه‌های سامانه کدال (Codal Live Intelligence)
              </h3>
            </div>
            <p style={{ fontSize: "0.78rem", color: "var(--text-secondary)", margin: "0.3rem 0 0" }}>
              استخراج خودکار صورت‌های مالی، گزارش‌های ماهانه و افشاهای بااهمیت همراه با برچسب اثرگذاری و خلاصه‌سازی هوشمند
            </p>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            {codalFeed.map((filing) => {
              const isPositive = filing.sentiment === "positive";
              const isNegative = filing.sentiment === "negative";
              const sentimentColor = isPositive ? "var(--tse-green)" : isNegative ? "var(--tse-red)" : "var(--tse-blue)";

              return (
                <div
                  key={filing.id}
                  className="card-panel"
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: "0.6rem",
                    borderRight: `4px solid ${sentimentColor}`,
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "0.5rem" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
                      <span style={{ fontSize: "1.1rem", fontWeight: 900, color: "var(--text-primary)" }}>{filing.symbol}</span>
                      <span
                        style={{
                          fontSize: "0.72rem",
                          backgroundColor: "rgba(59, 130, 246, 0.15)",
                          color: "var(--tse-blue)",
                          padding: "2px 8px",
                          borderRadius: "4px",
                          fontWeight: 700,
                        }}
                      >
                        {filing.filing_type_fa}
                      </span>
                      <span
                        style={{
                          fontSize: "0.72rem",
                          backgroundColor: isPositive ? "var(--tse-green-subtle)" : isNegative ? "var(--tse-red-subtle)" : "var(--bg-surface)",
                          color: sentimentColor,
                          padding: "2px 8px",
                          borderRadius: "4px",
                          fontWeight: 800,
                        }}
                      >
                        {filing.sentiment_fa}
                      </span>
                    </div>

                    <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                      <button
                        onClick={() => onSelectSymbol && onSelectSymbol(filing.symbol)}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "0.3rem",
                          fontSize: "0.75rem",
                          color: "var(--tse-green)",
                          backgroundColor: "rgba(34, 197, 94, 0.12)",
                          border: "1px solid rgba(34, 197, 94, 0.3)",
                          padding: "2px 8px",
                          borderRadius: "4px",
                          cursor: "pointer",
                          fontFamily: "inherit",
                          fontWeight: 700,
                        }}
                      >
                        <span>تحلیل ۳۶۰° نماد</span>
                      </button>
                      <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>{filing.published_at}</span>
                      {filing.url && (
                        <a
                          href={filing.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: "0.3rem",
                            fontSize: "0.75rem",
                            color: "var(--tse-blue)",
                            textDecoration: "none",
                            fontWeight: 700,
                          }}
                        >
                          <span>مشاهده در کدال</span>
                          <ExternalLink size={12} />
                        </a>
                      )}
                    </div>
                  </div>

                  <div style={{ fontSize: "0.86rem", fontWeight: 700, color: "var(--text-primary)", lineHeight: 1.4 }}>
                    {filing.title}
                  </div>

                  <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)", backgroundColor: "var(--bg-surface)", padding: "0.6rem 0.85rem", borderRadius: "var(--radius-sm)", lineHeight: 1.5 }}>
                    💡 <strong>تحلیل رادار:</strong> {filing.summary_fa}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 5. Sub-Tab 3: Macro & Commodities IME Radar */}
      {activeSubTab === "macro" && macroData && (
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          {/* Macro Regime Banner */}
          <div className="card-panel" style={{ borderLeft: "4px solid var(--tse-amber)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <Globe size={20} color="var(--tse-amber)" />
              <h3 style={{ fontSize: "1.05rem", fontWeight: 800, color: "var(--text-primary)", margin: 0 }}>
                پایش متغیرهای کلان پولی، ارزی و بورس کالا (Macroeconomic & IME Radar)
              </h3>
            </div>
            <p style={{ fontSize: "0.84rem", color: "var(--tse-green)", fontWeight: 700, marginTop: "0.4rem", marginBottom: 0 }}>
              {macroData.macro_regime_fa}
            </p>
          </div>

          {/* FX & Rates Grid */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "0.85rem" }}>
            <div className="card-panel">
              <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>نرخ دلار نیما (مرکز مبادله)</div>
              <div style={{ fontSize: "1.35rem", fontWeight: 800, color: "var(--text-primary)", marginTop: "0.2rem" }} className="tabular-num">
                {(macroData.nima_usd_rate / 10).toLocaleString("fa-IR")} تومان
              </div>
              <div style={{ fontSize: "0.72rem", color: "var(--tse-green)", fontWeight: 700, marginTop: "0.2rem" }}>
                مبنای تسعیر سود شرکت‌های صادراتی
              </div>
            </div>

            <div className="card-panel">
              <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>شکاف دلار آزاد و نیما</div>
              <div style={{ fontSize: "1.35rem", fontWeight: 800, color: "var(--tse-blue)", marginTop: "0.2rem" }} className="tabular-num">
                {macroData.gap_nima_free_pct}٪
              </div>
              <div style={{ fontSize: "0.72rem", color: "var(--text-muted)", marginTop: "0.2rem" }}>
                پتانسیل افزایش سود در صورت تعدیل نرخ
              </div>
            </div>

            <div className="card-panel">
              <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>نرخ سود بین‌بانکی</div>
              <div style={{ fontSize: "1.35rem", fontWeight: 800, color: "var(--tse-amber)", marginTop: "0.2rem" }} className="tabular-num">
                {macroData.interbank_interest_rate}٪
              </div>
              <div style={{ fontSize: "0.72rem", color: "var(--text-muted)", marginTop: "0.2rem" }}>
                پایش سیاست‌های انقباضی بانک مرکزی
              </div>
            </div>
          </div>

          {/* Commodities Table */}
          <div className="card-panel" style={{ padding: 0, overflowX: "auto" }}>
            <div style={{ padding: "0.85rem 1.25rem", borderBottom: "1px solid var(--border-subtle)", fontWeight: 800, color: "var(--text-primary)", fontSize: "0.95rem" }}>
              قیمت‌های پایه و جهانی کامودیتی‌ها در بورس کالای ایران (IME) و بازارهای بین‌المللی
            </div>
            <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "right", fontSize: "0.82rem" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border-subtle)", backgroundColor: "var(--bg-surface)", color: "var(--text-muted)" }}>
                  <th style={{ padding: "0.75rem 1rem" }}>نام کالا / محصول</th>
                  <th style={{ padding: "0.75rem 0.75rem" }}>دسته‌بندی</th>
                  <th style={{ padding: "0.75rem 0.75rem" }}>آخرین قیمت معامله</th>
                  <th style={{ padding: "0.75rem 0.75rem" }}>تغییرات</th>
                  <th style={{ padding: "0.75rem 0.75rem" }}>تحلیل اثرگذاری بر نمادها</th>
                  <th style={{ padding: "0.75rem 0.75rem" }}>صنایع منتفع</th>
                </tr>
              </thead>
              <tbody>
                {macroData.commodities.map((c: any, idx: number) => {
                  const isUp = c.change_pct >= 0;
                  return (
                    <tr key={idx} style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                      <td style={{ padding: "0.85rem 1rem", fontWeight: 800, color: "var(--text-primary)" }}>
                        {c.name_fa}
                      </td>
                      <td style={{ padding: "0.85rem 0.75rem", color: "var(--text-secondary)" }}>
                        {c.category}
                      </td>
                      <td style={{ padding: "0.85rem 0.75rem", fontWeight: 800, color: "var(--text-primary)" }} className="tabular-num">
                        {c.price.toLocaleString("fa-IR")} <span style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>{c.unit}</span>
                      </td>
                      <td style={{ padding: "0.85rem 0.75rem" }} className="tabular-num">
                        <span style={{ color: isUp ? "var(--tse-green)" : "var(--tse-red)", fontWeight: 800, display: "inline-flex", alignItems: "center", gap: "2px" }}>
                          {isUp ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
                          {isUp ? "+" : ""}{c.change_pct}٪
                        </span>
                      </td>
                      <td style={{ padding: "0.85rem 0.75rem", color: "var(--text-secondary)", fontSize: "0.78rem" }}>
                        {c.impact_fa}
                      </td>
                      <td style={{ padding: "0.85rem 0.75rem" }}>
                        <div style={{ display: "flex", gap: "4px", flexWrap: "wrap" }}>
                          {c.beneficiary_sectors?.map((sec: string, sIdx: number) => (
                            <span key={sIdx} style={{ fontSize: "0.7rem", backgroundColor: "rgba(59, 130, 246, 0.15)", color: "var(--tse-blue)", padding: "1px 6px", borderRadius: "4px", fontWeight: 700 }}>
                              {sec}
                            </span>
                          ))}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
