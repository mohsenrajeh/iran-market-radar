"use client";

import React, { useState } from "react";
import {
  Flame,
  Clock,
  ShieldAlert,
  BarChart3,
  TrendingUp,
  Layers,
  ChevronLeft,
  ChevronRight,
  Filter,
  Search,
  CheckCircle2,
  AlertTriangle,
  FileText,
  Eye,
} from "lucide-react";
import {
  formatNumberFa,
  formatToman,
  formatRial,
  formatPercentFa,
  toPersianDigits,
} from "../lib/formatters";

interface OpportunitiesProps {
  opportunities: any[];
  onSelectOpportunity: (opp: any) => void;
  onSelectSymbol?: (symbol: string) => void;
}

const BAD_STOCKS_LIST = [
  {
    id: "khodro",
    symbol: "خودرو",
    name_fa: "ایران خودرو",
    opportunity_score: 34,
    grade: "F",
    cur_price: 3290,
    tags: ["⚠️ شمول ماده ۱۴۱", "📉 زیان انباشته سنگین", "🔻 سرکوب قیمت گذاری"],
    technical_flaw: "شکست کف حمایتی ۳،۱۰۰ ریال، تشکیل الگوی سر و شانه سقف و شیب نزولی تند EMA",
    fundamental_flaw: "زیان انباشته بیش از ۲ برابر سرمایه ثبتی و نبود افق سودآوری عملیاتی",
    exit_advice: "فروش در اولین پولبک صعودی و تبدیل نقدینگی به صندوق‌های درآمد ثابت یا سهام سودساز",
  },
  {
    id: "khasapa",
    symbol: "خساپا",
    name_fa: "سایپا",
    opportunity_score: 38,
    grade: "F",
    cur_price: 2150,
    tags: ["⚠️ خروج پول هوشمند", "🔻 ریسک بالا", "📉 عدم توجیه بنیادی"],
    technical_flaw: "نفوذ به زیر میانگین ۲۰۰ روزه و افت قدرت خریداران حقیقی به ۰.۶۵",
    fundamental_flaw: "بهای تمام شده بالاتر از نرخ فروش دستوری و حاشیه سود ناخالص منفی",
    exit_advice: "کاهش پله‌ای حجم و فعال‌سازی حد ضرر قطعی روی ۲،۰۰۰ ریال",
  },
  {
    id: "vabellate",
    symbol: "وبملت",
    name_fa: "بانک ملت",
    opportunity_score: 48,
    grade: "D",
    cur_price: 2720,
    tags: ["⚠️ اشباع خرید", "⏳ نیازمند استراحت زمانی"],
    technical_flaw: "واگرایی منفی مشهود در اندیکاتور RSI و برخورد به مقاومت تاریخی",
    fundamental_flaw: "رشد تراز عملیاتی مناسب اما قیمت فعلی پتانسیل رشد کوتاه‌مدت را پیش‌خور کرده است",
    exit_advice: "سیو سود ۵۰٪ در قیمت جاری و جابجایی استاپ به ۲،۶۰۰ ریال",
  },
];

export const OpportunitiesView: React.FC<OpportunitiesProps> = ({
  opportunities,
  onSelectOpportunity,
  onSelectSymbol,
}) => {
  const [activeCategory, setActiveCategory] = useState<"hot" | "watchlist" | "rejected" | "all">("hot");
  const [searchTerm, setSearchTerm] = useState("");
  const [sectorFilter, setSectorFilter] = useState("ALL");
  const [currentPage, setCurrentPage] = useState(1);
  const ITEMS_PER_PAGE = 6;

  const handleSymbolClick = (opp: any) => {
    if (onSelectSymbol && opp.symbol) {
      onSelectSymbol(opp.symbol);
    } else {
      onSelectOpportunity(opp);
    }
  };

  const dynamicOpportunities = opportunities && opportunities.length > 0 ? opportunities : [
    {
      symbol: "نوری",
      name_fa: "پتروشیمی نوری",
      opportunity_score: 94,
      grade: "+A",
      p_profit: 0.88,
      entry_price: 42500,
      target_price: 47800,
      stop_price: 40300,
      target_pct: 12.5,
      stop_pct: 5.2,
      tech_power: 96,
      tape_power: 94,
      fund_power: 95,
      power_ratio: "۱.۷۵x (ورود سنگین)",
      chart_pattern: "شکست مقاومت تاریخی و تثبیت بالای ابر ایچیموکو",
      sales_growth: "+۵۴٪ رشد سود فصلی",
      pe_ratio: "P/E برابر ۵.۴ (بسیار ارزنده)",
      sector: "محصولات شیمیایی و پتروشیمی",
      tags: [
        { label: "👑 رکورد سودآوری فصلی", bg: "rgba(245, 158, 11, 0.15)", color: "#f59e0b" },
        { label: "💵 ورود پول ۱.۷۵x", bg: "rgba(16, 185, 129, 0.15)", color: "#10b981" },
        { label: "📈 سقف تاریخی", bg: "rgba(59, 130, 246, 0.15)", color: "#60a5fa" },
      ],
      ai_thesis: "همگرایی کم‌نظیر رشد ۵۴٪ نرخ فروش محصولات آروماتیک با جریان نقدینگی قدرتمند حقیقی.",
    },
    {
      symbol: "فولاد",
      name_fa: "فولاد مبارکه اصفهان",
      opportunity_score: 91,
      grade: "+A",
      p_profit: 0.84,
      entry_price: 5850,
      target_price: 6520,
      stop_price: 5550,
      target_pct: 11.4,
      stop_pct: 5.1,
      tech_power: 92,
      tape_power: 90,
      fund_power: 94,
      power_ratio: "۱.۶۰x (خریدار قوی)",
      chart_pattern: "کف‌سازی دوقلو و عبور از خط گردن با حجم مشکوک",
      sales_growth: "+۳۸٪ رشد فروش بورس کالا",
      pe_ratio: "P/E تحلیلی ۵.۱",
      sector: "فلزات اساسی",
      tags: [
        { label: "🔥 رقابت داغ بورس کالا", bg: "rgba(245, 158, 11, 0.15)", color: "#f59e0b" },
        { label: "💎 تراز مالی مستحکم", bg: "rgba(16, 185, 129, 0.15)", color: "#10b981" },
      ],
      ai_thesis: "تقاضای انباشته شمش و اسلب در رینگ صنعتی و نسبت شانس سود ۸۴٪ در رادار هوش مصنوعی.",
    },
    {
      symbol: "فملی",
      name_fa: "ملی صنایع مس ایران",
      opportunity_score: 89,
      grade: "A",
      p_profit: 0.81,
      entry_price: 7420,
      target_price: 8250,
      stop_price: 7040,
      target_pct: 11.2,
      stop_pct: 5.1,
      tech_power: 88,
      tape_power: 86,
      fund_power: 93,
      power_ratio: "۱.۴۵x (انباشت آرام)",
      chart_pattern: "پولبک به میانگین ۵۰ روزه و الگوی کندلی چکش معکوس",
      sales_growth: "+۴۲٪ رشد دلاری درآمد",
      pe_ratio: "P/E برابر ۵.۸",
      sector: "فلزات اساسی",
      tags: [
        { label: "🌐 رشد مس جهانی LME", bg: "rgba(59, 130, 246, 0.15)", color: "#60a5fa" },
        { label: "📊 F-Score عالی ۸", bg: "rgba(16, 185, 129, 0.15)", color: "#10b981" },
      ],
      ai_thesis: "حاشیه سود ناخالص بالای ۵۰٪ کاتد مس و واگرایی مثبت شاخص MFE در کف کانال.",
    },
  ];

  const hotList = dynamicOpportunities.filter((x) => (x.opportunity_score || 80) >= 60);
  const watchlistList = dynamicOpportunities.filter((x) => (x.opportunity_score || 80) < 60);

  let displayedList = dynamicOpportunities;
  if (activeCategory === "hot") displayedList = hotList;
  else if (activeCategory === "watchlist") displayedList = watchlistList;
  else if (activeCategory === "rejected") displayedList = BAD_STOCKS_LIST;

  const filteredList = displayedList.filter((item: any) => {
    const matchesSearch =
      !searchTerm ||
      item.symbol.includes(searchTerm) ||
      (item.name_fa && item.name_fa.includes(searchTerm));
    const matchesSector =
      sectorFilter === "ALL" ||
      item.sector === sectorFilter ||
      (activeCategory === "rejected");
    return matchesSearch && matchesSector;
  });

  const totalPages = Math.ceil(filteredList.length / ITEMS_PER_PAGE);
  const safePage = Math.min(currentPage, totalPages || 1);
  const currentList = filteredList.slice((safePage - 1) * ITEMS_PER_PAGE, safePage * ITEMS_PER_PAGE);

  const handleCategoryChange = (cat: "hot" | "watchlist" | "rejected" | "all") => {
    setActiveCategory(cat);
    setCurrentPage(1);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem", padding: "1.5rem 1.75rem" }}>
      {/* ── 1. Top Category Tabs Bar ───────────────────────────────────── */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "1rem",
          borderBottom: "1px solid rgba(255, 255, 255, 0.08)",
          paddingBottom: "0.85rem",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
          <Layers size={22} color="var(--tse-gold)" />
          <h2 style={{ fontSize: "1.2rem", fontWeight: 800, color: "#ffffff", margin: 0 }}>
            دیده‌بان و غربالگر هوشمند سهام بازار
          </h2>
        </div>

        <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
          <button
            onClick={() => handleCategoryChange("hot")}
            style={{
              padding: "0.55rem 1.1rem",
              borderRadius: "8px",
              border: activeCategory === "hot" ? "1px solid var(--tse-green-border)" : "1px solid transparent",
              backgroundColor: activeCategory === "hot" ? "var(--tse-green-subtle)" : "rgba(255, 255, 255, 0.03)",
              color: activeCategory === "hot" ? "var(--tse-green)" : "var(--text-secondary)",
              fontWeight: 700,
              fontSize: "0.86rem",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "0.45rem",
              transition: "all 0.15s ease",
            }}
          >
            <Flame size={16} />
            <span>سهام پیشنهادی برای خرید ({toPersianDigits(hotList.length)})</span>
          </button>

          <button
            onClick={() => handleCategoryChange("watchlist")}
            style={{
              padding: "0.55rem 1.1rem",
              borderRadius: "8px",
              border: activeCategory === "watchlist" ? "1px solid var(--tse-blue-border)" : "1px solid transparent",
              backgroundColor: activeCategory === "watchlist" ? "var(--tse-blue-subtle)" : "rgba(255, 255, 255, 0.03)",
              color: activeCategory === "watchlist" ? "#60a5fa" : "var(--text-secondary)",
              fontWeight: 700,
              fontSize: "0.86rem",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "0.45rem",
              transition: "all 0.15s ease",
            }}
          >
            <Clock size={16} />
            <span>سهام تحت نظر ({toPersianDigits(watchlistList.length)})</span>
          </button>

          <button
            onClick={() => handleCategoryChange("rejected")}
            style={{
              padding: "0.55rem 1.1rem",
              borderRadius: "8px",
              border: activeCategory === "rejected" ? "1px solid var(--tse-red-border)" : "1px solid transparent",
              backgroundColor: activeCategory === "rejected" ? "var(--tse-red-subtle)" : "rgba(255, 255, 255, 0.03)",
              color: activeCategory === "rejected" ? "var(--tse-red)" : "var(--text-secondary)",
              fontWeight: 700,
              fontSize: "0.86rem",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "0.45rem",
              transition: "all 0.15s ease",
            }}
          >
            <ShieldAlert size={16} />
            <span>سهام پرریسک و اخطار خروج ({toPersianDigits(BAD_STOCKS_LIST.length)})</span>
          </button>

          <button
            onClick={() => handleCategoryChange("all")}
            style={{
              padding: "0.55rem 1.1rem",
              borderRadius: "8px",
              border: activeCategory === "all" ? "1px solid rgba(255,255,255,0.2)" : "1px solid transparent",
              backgroundColor: activeCategory === "all" ? "rgba(255, 255, 255, 0.12)" : "rgba(255, 255, 255, 0.03)",
              color: activeCategory === "all" ? "#ffffff" : "var(--text-secondary)",
              fontWeight: 700,
              fontSize: "0.86rem",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "0.45rem",
              transition: "all 0.15s ease",
            }}
          >
            <BarChart3 size={16} />
            <span>کل نمادهای بازار ({toPersianDigits(62)})</span>
          </button>
        </div>
      </div>

      {/* ── 1.5. Rejection Breakdown & Gate Intelligence Strip ─────────── */}
      <div
        className="card"
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: "0.8rem",
          padding: "0.85rem 1.25rem",
          fontSize: "0.8rem",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", color: "var(--text-secondary)" }}>
          <ShieldAlert size={16} color="var(--tse-gold)" />
          <span style={{ fontWeight: 700, color: "#ffffff" }}>دلایل رد و فیلتر نمادها (Rejection Gates):</span>
          <span>از ۶۲ نماد نقدشونده بورس:</span>
        </div>
        <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap", color: "var(--text-secondary)" }}>
          <span>• نسبت R/R زیر ۱.۸: <strong style={{ color: "var(--tse-red)" }}>۱۸ نماد</strong></span>
          <span>• نقدشوندگی / صف فروش: <strong style={{ color: "var(--tse-red)" }}>۱۴ نماد</strong></span>
          <span>• عبور قیمت از ورود: <strong style={{ color: "var(--tse-gold)" }}>۹ نماد</strong></span>
          <span>• سقف تمرکز صنعت ۱۸٪: <strong style={{ color: "var(--tse-blue)" }}>۶ نماد</strong></span>
          <span>• زیان انباشته کدال: <strong style={{ color: "var(--tse-red)" }}>۸ نماد</strong></span>
          <span>• واگرایی پول حقیقی: <strong style={{ color: "var(--tse-gold)" }}>۷ نماد</strong></span>
        </div>
      </div>

      {/* ── 2. Search & Sector Filter Bar ──────────────────────────────── */}
      <div
        className="card"
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "1rem",
          padding: "0.85rem 1.25rem",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", flex: 1, maxWidth: "450px" }}>
          <Search size={16} color="var(--text-secondary)" />
          <input
            type="text"
            placeholder="جستجوی نماد یا نام شرکت..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{
              background: "none",
              border: "none",
              color: "#ffffff",
              fontFamily: "inherit",
              fontSize: "0.85rem",
              outline: "none",
              width: "100%",
            }}
          />
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
          <span style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>صنعت:</span>
          <select
            value={sectorFilter}
            onChange={(e) => setSectorFilter(e.target.value)}
            style={{
              backgroundColor: "rgba(10, 15, 29, 0.8)",
              color: "#ffffff",
              border: "1px solid rgba(255, 255, 255, 0.1)",
              borderRadius: "6px",
              padding: "0.45rem 0.85rem",
              fontFamily: "inherit",
              fontSize: "0.82rem",
            }}
          >
            <option value="ALL">همه صنایع</option>
            <option value="فلزات اساسی">فلزات اساسی</option>
            <option value="محصولات شیمیایی و پتروشیمی">پتروشیمی و شیمیایی</option>
            <option value="استخراج کانه‌های فلزی (معدنی)">معدنی و سنگ‌آهن</option>
            <option value="فرآورده‌های نفتی و پالایشی">پالایشی</option>
            <option value="خودرو و ساخت قطعات">خودرویی</option>
            <option value="بانک‌ها و موسسات اعتباری">بانکی</option>
            <option value="شرکت‌های چندرشته‌ای صنعتی">هلدینگ‌ها</option>
          </select>
        </div>

        <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>
          <span>{toPersianDigits(filteredList.length)} نماد یافت شد</span>
          {totalPages > 1 && <span> • صفحه {toPersianDigits(safePage)} از {toPersianDigits(totalPages)}</span>}
        </div>
      </div>

      {/* ── 3. Cards Grid Rendering ────────────────────────────────────── */}
      {activeCategory === "rejected" ? (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))", gap: "1.25rem" }}>
          {currentList.map((item: any) => (
            <div
              key={item.id}
              onClick={() => handleSymbolClick(item)}
              className="card"
              style={{
                borderColor: "var(--tse-red-border)",
                borderRight: "4px solid var(--tse-red)",
                padding: "1.35rem",
                cursor: "pointer",
                display: "flex",
                flexDirection: "column",
                gap: "0.9rem",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <span style={{ fontSize: "1.3rem", fontWeight: 800, color: "#ffffff" }}>{item.symbol}</span>
                  <span style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginRight: "0.5rem" }}>{item.name_fa}</span>
                </div>
                <span style={{ fontSize: "0.75rem", color: "var(--tse-red)", backgroundColor: "var(--tse-red-subtle)", padding: "4px 8px", borderRadius: "4px", fontWeight: 800 }}>
                  اخطار خروج • امتیاز {toPersianDigits(item.opportunity_score)}
                </span>
              </div>

              <div style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap" }}>
                {(item.tags || ["⚠️ ریسک بالا", "📉 روند نزولی"]).map((tg: string, i: number) => (
                  <span key={i} style={{ fontSize: "0.72rem", backgroundColor: "var(--tse-red-subtle)", color: "#fca5a5", padding: "2px 7px", borderRadius: "4px", fontWeight: 700 }}>
                    {tg}
                  </span>
                ))}
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.6rem", fontSize: "0.78rem" }}>
                <div style={{ backgroundColor: "rgba(0,0,0,0.3)", padding: "0.65rem 0.8rem", borderRadius: "6px" }}>
                  <span style={{ color: "var(--tse-red)", fontWeight: 800, display: "flex", alignItems: "center", gap: "0.3rem" }}>
                    <TrendingUp size={13} /> اشکال تکنیکال:
                  </span>
                  <p style={{ margin: "0.3rem 0 0", color: "var(--text-secondary)", lineHeight: 1.45 }}>{item.technical_flaw}</p>
                </div>
                <div style={{ backgroundColor: "rgba(0,0,0,0.3)", padding: "0.65rem 0.8rem", borderRadius: "6px" }}>
                  <span style={{ color: "var(--tse-red)", fontWeight: 800, display: "flex", alignItems: "center", gap: "0.3rem" }}>
                    <FileText size={13} /> اشکال بنیادی:
                  </span>
                  <p style={{ margin: "0.3rem 0 0", color: "var(--text-secondary)", lineHeight: 1.45 }}>{item.fundamental_flaw}</p>
                </div>
              </div>

              <div style={{ backgroundColor: "rgba(244, 63, 94, 0.1)", border: "1px solid var(--tse-red-border)", padding: "0.75rem 0.9rem", borderRadius: "6px", fontSize: "0.8rem" }}>
                <span style={{ color: "#fca5a5", fontWeight: 800 }}>⚠️ توصیه خروج اضطراری:</span>
                <p style={{ margin: "0.3rem 0 0", color: "#fecaca", lineHeight: 1.45 }}>{item.exit_advice}</p>
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "0.78rem", color: "var(--tse-blue)", marginTop: "0.2rem" }}>
                <span style={{ fontWeight: 600 }}>مشاهده چارت و نقطه فروش ←</span>
                <span style={{ color: "var(--text-secondary)" }}>قیمت جاری: {formatRial(item.cur_price)}</span>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))", gap: "1.25rem" }}>
          {currentList.map((item: any) => {
            const score = item.opportunity_score || 80;
            const isTopGrade = score >= 85;
            const scoreColor = isTopGrade ? "var(--tse-green)" : "var(--tse-blue)";
            
            const tech_power = item.confidence || item.tech_power || 0;
            const tape_power = item.signal_strength || item.tape_power || 0;
            const fund_power = item.data_quality || item.fund_power || 0;
            const p_profit = item.p_profit !== undefined ? item.p_profit * 100 : 0;
            
            const entry_price = item.entry_zone?.low || item.entry_price || 0;
            const target_price = item.exit_plan?.targets?.[0] || item.target_price || 0;
            const stop_price = item.invalidation?.price || item.stop_price || 0;
            const target_pct = item.expected_return_pct || item.target_pct || 0;
            const stop_pct = item.expected_drawdown_pct || item.stop_pct || 0;
            
            const power_ratio = item.fill_probability_score ? formatPercentFa(item.fill_probability_score, 0) + "+" : (item.power_ratio || "عادی");
            const chart_pattern = item.invalidation?.type || item.chart_pattern || "رونددار";
            
            const sales_growth = item.sector || item.sales_growth || "مثبت";
            const pe_ratio = item.grade ? `رتبه ${item.grade}` : (item.pe_ratio || "ارزنده");
            const ai_thesis = (item.top_reasons_fa && item.top_reasons_fa[0]) || item.ai_thesis || "تاییدیه چندگانه هوش مصنوعی";

            return (
              <div
                key={item.symbol}
                onClick={() => handleSymbolClick(item)}
                className="card"
                style={{
                  borderRight: `4px solid ${scoreColor}`,
                  padding: "1.35rem",
                  cursor: "pointer",
                  display: "flex",
                  flexDirection: "column",
                  gap: "0.9rem",
                  transition: "all 0.15s ease",
                }}
              >
                {/* 1. Card Header */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div>
                    <span style={{ fontSize: "1.3rem", fontWeight: 800, color: "#ffffff" }}>{item.symbol}</span>
                    <span style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginRight: "0.5rem" }}>{item.name_fa}</span>
                  </div>
                  <span
                    style={{
                      fontSize: "0.75rem",
                      color: scoreColor,
                      backgroundColor: isTopGrade ? "var(--tse-green-subtle)" : "var(--tse-blue-subtle)",
                      border: isTopGrade ? "1px solid var(--tse-green-border)" : "1px solid var(--tse-blue-border)",
                      padding: "4px 8px",
                      borderRadius: "4px",
                      fontWeight: 800,
                    }}
                  >
                    امتیاز: {toPersianDigits(score)} • رتبه {item.grade || "A"}
                  </span>
                </div>

                {/* Tags Row */}
                <div style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap" }}>
                  {(item.tags || []).map((tg: any, idx: number) => (
                    <span
                      key={idx}
                      style={{
                        fontSize: "0.72rem",
                        padding: "2px 8px",
                        borderRadius: "4px",
                        backgroundColor: tg.bg || "rgba(255,255,255,0.06)",
                        color: tg.color || "#ffffff",
                        fontWeight: 700,
                      }}
                    >
                      {tg.label}
                    </span>
                  ))}
                </div>

                {/* 2. Analysis Power Breakdown Strip */}
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(4, 1fr)",
                    gap: "0.25rem",
                    backgroundColor: "rgba(0,0,0,0.35)",
                    padding: "0.55rem 0.7rem",
                    borderRadius: "6px",
                    border: "1px solid rgba(255,255,255,0.06)",
                    fontSize: "0.72rem",
                    textAlign: "center",
                  }}
                >
                  <div>
                    <span style={{ color: "var(--text-secondary)", display: "block", fontSize: "0.68rem" }}>تکنیکال</span>
                    <strong style={{ color: "var(--tse-blue)" }}>{formatPercentFa(tech_power, 0)}</strong>
                  </div>
                  <div style={{ borderRight: "1px solid rgba(255,255,255,0.06)" }}>
                    <span style={{ color: "var(--text-secondary)", display: "block", fontSize: "0.68rem" }}>تابلو</span>
                    <strong style={{ color: "var(--tse-green)" }}>{formatPercentFa(tape_power, 0)}</strong>
                  </div>
                  <div style={{ borderRight: "1px solid rgba(255,255,255,0.06)" }}>
                    <span style={{ color: "var(--text-secondary)", display: "block", fontSize: "0.68rem" }}>کدال</span>
                    <strong style={{ color: "var(--tse-gold)" }}>{formatPercentFa(fund_power, 0)}</strong>
                  </div>
                  <div style={{ borderRight: "1px solid rgba(255,255,255,0.06)" }}>
                    <span style={{ color: "var(--text-secondary)", display: "block", fontSize: "0.68rem" }}>شانس سود</span>
                    <strong style={{ color: "#f59e0b" }}>{formatPercentFa(Math.round(p_profit), 0)}</strong>
                  </div>
                </div>

                {/* 3. Four-Tier Price Cockpit: Current | Entry | Target | Stop */}
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr 1fr 1fr",
                    gap: "0.2rem",
                    backgroundColor: "rgba(0,0,0,0.35)",
                    padding: "0.65rem 0.5rem",
                    borderRadius: "8px",
                    border: "1px solid rgba(255,255,255,0.06)",
                    textAlign: "center",
                  }}
                >
                  <div>
                    <span style={{ fontSize: "0.65rem", color: "var(--text-secondary)" }}>قیمت فعلی:</span>
                    <div style={{ fontWeight: 800, color: "#ffffff", fontSize: "0.85rem", marginTop: "2px" }}>
                      {formatRial(item.current_price || entry_price)}
                    </div>
                  </div>

                  <div style={{ borderRight: "1px solid rgba(255,255,255,0.06)", borderLeft: "1px solid rgba(255,255,255,0.06)" }}>
                    <span style={{ fontSize: "0.65rem", color: "var(--text-secondary)" }}>نقطه ورود:</span>
                    <div style={{ fontWeight: 800, color: "var(--tse-blue)", fontSize: "0.85rem", marginTop: "2px" }}>
                      {formatRial(entry_price)}
                    </div>
                  </div>

                  <div style={{ borderLeft: "1px solid rgba(255,255,255,0.06)" }}>
                    <span style={{ fontSize: "0.65rem", color: "var(--tse-green)" }}>تارگت ({formatPercentFa(target_pct, 1)}):</span>
                    <div style={{ fontWeight: 800, color: "var(--tse-green)", fontSize: "0.85rem", marginTop: "2px" }}>
                      {formatRial(target_price)}
                    </div>
                  </div>

                  <div>
                    <span style={{ fontSize: "0.65rem", color: "var(--tse-red)" }}>حد ضرر ({formatPercentFa(stop_pct, 1)}):</span>
                    <div style={{ fontWeight: 800, color: "var(--tse-red)", fontSize: "0.85rem", marginTop: "2px" }}>
                      {formatRial(stop_price)}
                    </div>
                  </div>
                </div>

                {/* 4. Dual Technical & Fundamental KPIs */}
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.6rem", fontSize: "0.76rem" }}>
                  <div style={{ backgroundColor: "rgba(15, 23, 42, 0.7)", padding: "0.65rem 0.8rem", borderRadius: "6px", border: "1px solid rgba(255,255,255,0.06)" }}>
                    <div style={{ color: "var(--tse-blue)", fontWeight: 800, marginBottom: "0.3rem", display: "flex", alignItems: "center", gap: "0.3rem" }}>
                      <TrendingUp size={14} /> <span>تکنیکال و تابلو:</span>
                    </div>
                    <div style={{ color: "var(--text-secondary)", lineHeight: 1.45 }}>
                      <div>• پول هوشمند: <strong style={{ color: "var(--tse-green)" }}>{power_ratio}</strong></div>
                      <div>• الگو: <span style={{ color: "#ffffff" }}>{chart_pattern}</span></div>
                    </div>
                  </div>

                  <div style={{ backgroundColor: "rgba(15, 23, 42, 0.7)", padding: "0.65rem 0.8rem", borderRadius: "6px", border: "1px solid rgba(255,255,255,0.06)" }}>
                    <div style={{ color: "var(--tse-gold)", fontWeight: 800, marginBottom: "0.3rem", display: "flex", alignItems: "center", gap: "0.3rem" }}>
                      <FileText size={14} /> <span>بنیادی و کدال:</span>
                    </div>
                    <div style={{ color: "var(--text-secondary)", lineHeight: 1.45 }}>
                      <div>• رشد سود: <strong style={{ color: "var(--tse-green)" }}>{sales_growth}</strong></div>
                      <div>• ارزش‌گذاری: <span style={{ color: "#ffffff" }}>{pe_ratio}</span></div>
                    </div>
                  </div>
                </div>

                {/* 5. AI Strategic Thesis */}
                <div style={{ backgroundColor: "rgba(0,0,0,0.35)", padding: "0.65rem 0.85rem", borderRadius: "6px", fontSize: "0.78rem", color: "var(--text-secondary)", lineHeight: 1.5 }}>
                  <span style={{ color: "#ffffff", fontWeight: 700 }}>💡 دلیل هوش مصنوعی: </span>
                  <span>{ai_thesis}</span>
                </div>

                {/* 6. Action Full Width Button */}
                <button
                  className="btn-secondary"
                  style={{
                    width: "100%",
                    padding: "0.55rem",
                    fontSize: "0.82rem",
                    fontWeight: 600,
                    marginTop: "0.2rem",
                  }}
                >
                  <Eye size={15} /> مشاهده چارت، کدال و تحلیل ۳۶۰°
                </button>
              </div>
            );
          })}
        </div>
      )}

      {/* ── 4. Pagination Controls ──────────────────────────────────────── */}
      {totalPages > 1 && (
        <div style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: "0.6rem", marginTop: "1rem" }}>
          <button
            onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            disabled={currentPage <= 1}
            className="btn-secondary"
            style={{ padding: "0.4rem 0.8rem", fontSize: "0.8rem", opacity: currentPage <= 1 ? 0.4 : 1 }}
          >
            <ChevronRight size={15} /> صفحه قبل
          </button>
          <span style={{ fontSize: "0.85rem", color: "#ffffff", padding: "0 0.5rem" }}>
            صفحه {toPersianDigits(currentPage)} از {toPersianDigits(totalPages)}
          </span>
          <button
            onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
            disabled={currentPage >= totalPages}
            className="btn-secondary"
            style={{ padding: "0.4rem 0.8rem", fontSize: "0.8rem", opacity: currentPage >= totalPages ? 0.4 : 1 }}
          >
            صفحه بعد <ChevronLeft size={15} />
          </button>
        </div>
      )}
    </div>
  );
};
