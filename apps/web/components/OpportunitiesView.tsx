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
  referenceSymbols?: any;
  onSelectOpportunity: (opp: any) => void;
  onSelectSymbol?: (symbol: string) => void;
}

export const OpportunitiesView: React.FC<OpportunitiesProps> = ({
  opportunities,
  referenceSymbols,
  onSelectOpportunity,
  onSelectSymbol,
}) => {
  // The market feed is the primary content of this screen. Strategy results are
  // separate derived views and can legitimately be empty while the feed is full.
  const [activeCategory, setActiveCategory] = useState<"hot" | "watchlist" | "rejected" | "all">("all");
  const [searchTerm, setSearchTerm] = useState("");
  const [sectorFilter, setSectorFilter] = useState("ALL");
  const [marketFilter, setMarketFilter] = useState<"ALL" | "TSE" | "IFB">("ALL");
  const [currentPage, setCurrentPage] = useState(1);
  const [referencePage, setReferencePage] = useState(1);
  const ITEMS_PER_PAGE = 6;
  const REFERENCE_ITEMS_PER_PAGE = 25;

  const handleSymbolClick = (opp: any) => {
    if (onSelectSymbol && opp.symbol) {
      onSelectSymbol(opp.symbol);
    } else {
      onSelectOpportunity(opp);
    }
  };

  const dynamicOpportunities = Array.isArray(opportunities) ? opportunities : [];
  const referenceRows = Array.isArray(referenceSymbols?.rows) ? referenceSymbols.rows : [];
  const referenceMeta = referenceSymbols?.meta || {};
  const referenceProvider = String(referenceSymbols?.provider || "TSETMC Public CDN");
  const referenceTradeEligible = Boolean(referenceSymbols?.trade_eligible);
  const referenceIsStale = Boolean(referenceMeta.stale);
  const referenceStatus = String(referenceMeta.status || "UNAVAILABLE");
  const referenceDisplayState = String(referenceMeta.display_state || "NO_DATA");
  const referenceIsLastClose = referenceDisplayState === "LAST_CLOSE";
  const referenceLastUpdate = referenceMeta.last_success_at
    ? new Date(referenceMeta.last_success_at).toLocaleString("fa-IR", {
        timeZone: "Asia/Tehran",
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      })
    : "ثبت نشده";
  const marketClass = (value: unknown): "TSE" | "IFB" | "UNKNOWN" => {
    const normalized = String(value || "").toUpperCase();
    if (normalized === "IFB" || normalized.includes("فرابورس")) return "IFB";
    if (normalized === "TSE" || normalized.includes("بورس")) return "TSE";
    return "UNKNOWN";
  };
  const filteredReferenceRows = referenceRows.filter((row: any) => {
    const matchesText = !searchTerm
      || String(row.ticker || "").includes(searchTerm)
      || String(row.name_fa || "").includes(searchTerm);
    const matchesMarket = marketFilter === "ALL" || marketClass(row.market) === marketFilter;
    return matchesText && matchesMarket;
  });
  const referenceTotalPages = Math.max(1, Math.ceil(filteredReferenceRows.length / REFERENCE_ITEMS_PER_PAGE));
  const safeReferencePage = Math.min(referencePage, referenceTotalPages);
  const visibleReferenceRows = filteredReferenceRows.slice(
    (safeReferencePage - 1) * REFERENCE_ITEMS_PER_PAGE,
    safeReferencePage * REFERENCE_ITEMS_PER_PAGE,
  );

  const hotList = dynamicOpportunities.filter((x) => x.actionable === true);
  const watchlistList = dynamicOpportunities.filter((x) => x.actionable !== true);
  const rejectedList = dynamicOpportunities.filter((x) => x.actionable !== true && Array.isArray(x.risk_flags_fa) && x.risk_flags_fa.length > 0);

  let displayedList = dynamicOpportunities;
  if (activeCategory === "hot") displayedList = hotList;
  else if (activeCategory === "watchlist") displayedList = watchlistList;
  else if (activeCategory === "rejected") displayedList = rejectedList;

  const filteredList = displayedList.filter((item: any) => {
    const matchesSearch =
      !searchTerm ||
      item.symbol.includes(searchTerm) ||
      (item.name_fa && item.name_fa.includes(searchTerm));
    const matchesSector =
      sectorFilter === "ALL" ||
      item.sector === sectorFilter ||
      (activeCategory === "rejected");
    const matchesMarket = marketFilter === "ALL" || marketClass(item.market) === marketFilter;
    return matchesSearch && matchesSector && matchesMarket;
  });

  const totalPages = Math.ceil(filteredList.length / ITEMS_PER_PAGE);
  const safePage = Math.min(currentPage, totalPages || 1);
  const currentList = filteredList.slice((safePage - 1) * ITEMS_PER_PAGE, safePage * ITEMS_PER_PAGE);

  const handleCategoryChange = (cat: "hot" | "watchlist" | "rejected" | "all") => {
    setActiveCategory(cat);
    setCurrentPage(1);
    setReferencePage(1);
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
            <span>سیگنال‌های ردشده با دلیل ثبت‌شده ({toPersianDigits(rejectedList.length)})</span>
          </button>

          <button
            onClick={() => handleCategoryChange("all")}
            data-testid="reference-market-tab"
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
            <span>{referenceTradeEligible ? "کل بازار دریافت‌شده" : "نمادهای مرجع دریافت‌شده"} ({toPersianDigits(referenceMeta.collected || 0)})</span>
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
          <span>
            سیگنال‌های همین اجرای رسمی؛ دیده‌بان {referenceProvider} از نتیجهٔ استراتژی و گیت بنیادی جداست.
          </span>
        </div>
        <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap", color: "var(--text-secondary)" }}>
          <span>خرید مجاز: <strong style={{ color: "var(--tse-green)" }}>{toPersianDigits(hotList.length)} نماد</strong></span>
          <span>تحت نظر: <strong style={{ color: "var(--tse-blue)" }}>{toPersianDigits(watchlistList.length)} نماد</strong></span>
          <span>ردشده با دلیل: <strong style={{ color: "var(--tse-red)" }}>{toPersianDigits(rejectedList.length)} نماد</strong></span>
          <span>مرجع جمع‌آوری‌شده: <strong style={{ color: "var(--tse-gold)" }}>{toPersianDigits(referenceMeta.collected || 0)} از {toPersianDigits(referenceMeta.provider_total || 0)}</strong></span>
        </div>
      </div>

      {activeCategory === "all" && (
        <div data-testid="reference-market-panel" className="card" style={{ padding: "1rem 1.25rem", borderColor: "rgba(245,158,11,0.35)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", gap: "0.75rem", flexWrap: "wrap", marginBottom: "0.8rem" }}>
            <div>
              <div style={{ color: "var(--tse-gold)", fontWeight: 800 }}>دیده‌بان {referenceProvider} — {referenceTradeEligible ? "داده رسمی بازار" : "منبع رسمی؛ فعلاً غیرقابل استفاده"}</div>
              <div style={{ color: "var(--text-secondary)", fontSize: "0.78rem", marginTop: "0.2rem" }}>
                این ردیف‌ها خودِ سیگنال خرید نیستند؛ خرید فقط پس از همگرایی استراتژی‌ها، تاریخچه کافی و گیت بنیادی انجام می‌شود.
              </div>
            </div>
            <div style={{ color: "var(--text-secondary)", fontSize: "0.78rem" }}>
              نمایش صفحه {toPersianDigits(safeReferencePage)} از {toPersianDigits(referenceTotalPages)} • {toPersianDigits(filteredReferenceRows.length)} نماد قابل مرور • کل provider: {toPersianDigits(referenceMeta.provider_total || 0)}
              {referenceMeta.completed ? " • تکمیل شده" : " • در حال تکمیل مرحله‌ای"}
              <span style={{ color: referenceIsLastClose ? "var(--tse-gold)" : referenceIsStale || referenceStatus !== "HEALTHY" ? "var(--tse-red)" : "var(--tse-green)", fontWeight: 800 }}>
                {referenceIsLastClose
                  ? ` • بازار بسته • آخرین ثبت: ${referenceLastUpdate}`
                  : ` • سلامت: ${referenceStatus} • ${referenceIsStale ? "کهنه/نامعتبر برای تصمیم" : `تازه (${toPersianDigits(referenceMeta.age_seconds ?? 0)} ثانیه)`}`}
              </span>
            </div>
          </div>
          {referenceIsLastClose ? (
            <div data-testid="last-close-market-banner" style={{ marginBottom: "0.8rem", padding: "0.65rem 0.8rem", borderRadius: "7px", background: "var(--tse-amber-subtle)", color: "var(--tse-gold)", fontSize: "0.8rem", fontWeight: 700 }}>
              بازار بسته است؛ این قیمت‌ها آخرین snapshot ثبت‌شده‌اند و فقط نمایش داده می‌شوند. هیچ درخواست جدیدی تا بازگشایی بعدی ({new Date(referenceMeta.next_open_at_tehran).toLocaleString("fa-IR", { timeZone: "Asia/Tehran", weekday: "long", hour: "2-digit", minute: "2-digit" })}) ارسال نمی‌شود.
            </div>
          ) : (referenceIsStale || referenceStatus !== "HEALTHY") && (
            <div style={{ marginBottom: "0.8rem", padding: "0.65rem 0.8rem", borderRadius: "7px", background: "var(--tse-red-subtle)", color: "var(--tse-red)", fontSize: "0.8rem", fontWeight: 700 }}>
              آخرین batch رسمی سالم و تازه نیست؛ ردیف قبلی برای تحلیل یا معامله قابل استفاده نیست.
            </div>
          )}
          {filteredReferenceRows.length === 0 ? (
            <div style={{ color: "var(--text-muted)", fontSize: "0.82rem", padding: "0.75rem 0" }}>
              JSON API رسمی TSETMC هنوز هیچ batch معتبر بازار برنگردانده است؛ تا رفع دسترسی شبکه، قیمت یا سیگنال ساخته نمی‌شود.
            </div>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8rem" }}>
                <thead><tr style={{ color: "var(--text-muted)", borderBottom: "1px solid var(--border-subtle)" }}>
                  <th style={{ textAlign: "right", padding: "0.6rem" }}>نماد</th>
                  <th style={{ textAlign: "right", padding: "0.6rem" }}>نام</th>
                  <th style={{ textAlign: "left", padding: "0.6rem" }}>آخرین قیمت (ریال)</th>
                  <th style={{ textAlign: "left", padding: "0.6rem" }}>تغییر</th>
                  <th style={{ textAlign: "right", padding: "0.6rem" }}>وضعیت</th>
                </tr></thead>
                <tbody>{visibleReferenceRows.map((row: any) => (
                  <tr key={row.slug} data-testid="reference-market-row" style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                    <td style={{ padding: "0.6rem", color: "#fff", fontWeight: 800 }}>{row.ticker}</td>
                    <td style={{ padding: "0.6rem", color: "var(--text-secondary)" }}>{row.name_fa}</td>
                    <td style={{ padding: "0.6rem", textAlign: "left" }} className="tabular-num">{formatNumberFa(row.last_price_rials)}</td>
                    <td style={{ padding: "0.6rem", textAlign: "left", color: Number(row.change_pct) >= 0 ? "var(--tse-green)" : "var(--tse-red)" }}>{formatPercentFa(row.change_pct)}</td>
                    <td style={{ padding: "0.6rem", color: referenceTradeEligible ? "var(--tse-green)" : "var(--tse-gold)" }}>{referenceTradeEligible ? "رسمی؛ منتظر گیت تحلیل" : referenceIsLastClose ? "قیمت پایانی؛ فقط نمایش" : "مرجع؛ غیرقابل اجرا"}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          )}
          {filteredReferenceRows.length > REFERENCE_ITEMS_PER_PAGE && (
            <div style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: "0.75rem", marginTop: "0.9rem" }}>
              <button
                onClick={() => setReferencePage((value) => Math.max(1, value - 1))}
                disabled={safeReferencePage === 1}
                style={{ padding: "0.4rem 0.8rem", borderRadius: "6px", border: "1px solid var(--border-subtle)", background: "var(--bg-surface)", color: "var(--text-primary)", opacity: safeReferencePage === 1 ? 0.45 : 1, cursor: safeReferencePage === 1 ? "not-allowed" : "pointer" }}
              >صفحه قبل</button>
              <span style={{ color: "var(--text-secondary)", fontSize: "0.8rem" }}>{toPersianDigits(safeReferencePage)} / {toPersianDigits(referenceTotalPages)}</span>
              <button
                onClick={() => setReferencePage((value) => Math.min(referenceTotalPages, value + 1))}
                disabled={safeReferencePage === referenceTotalPages}
                style={{ padding: "0.4rem 0.8rem", borderRadius: "6px", border: "1px solid var(--border-subtle)", background: "var(--bg-surface)", color: "var(--text-primary)", opacity: safeReferencePage === referenceTotalPages ? 0.45 : 1, cursor: safeReferencePage === referenceTotalPages ? "not-allowed" : "pointer" }}
              >صفحه بعد</button>
            </div>
          )}
        </div>
      )}

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
            onChange={(e) => { setSearchTerm(e.target.value); setCurrentPage(1); setReferencePage(1); }}
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
          <span style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>بازار:</span>
          <select
            value={marketFilter}
            onChange={(e) => { setMarketFilter(e.target.value as "ALL" | "TSE" | "IFB"); setCurrentPage(1); setReferencePage(1); }}
            aria-label="فیلتر طبقه‌بندی بازار"
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
            <option value="ALL">همه بازارها</option>
            <option value="TSE">بورس تهران</option>
            <option value="IFB">فرابورس ایران</option>
          </select>
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
          <span data-testid="visible-market-count">{toPersianDigits(activeCategory === "all" ? filteredReferenceRows.length : filteredList.length)} نماد یافت شد</span>
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
            const score = item.opportunity_score ?? 0;
            const isTopGrade = score >= 85;
            const scoreColor = isTopGrade ? "var(--tse-green)" : "var(--tse-blue)";
            
            const tech_power = item.confidence || item.tech_power || 0;
            const tape_power = item.signal_strength || item.tape_power || 0;
            const fundamentalGate = item.decision_components?.fundamental_gate;
            const calibrationGate = item.decision_components?.calibration_gate;
            const fund_power = Number(fundamentalGate?.score || 0);
            const p_profit = item.p_profit !== undefined ? item.p_profit * 100 : 0;
            
            const entry_price = item.entry_zone?.low || item.entry_price || 0;
            const target_price = item.exit_plan?.targets?.[0] || item.target_price || 0;
            const stop_price = item.invalidation?.price || item.stop_price || 0;
            const target_pct = item.expected_return_pct || item.target_pct || 0;
            const stop_pct = item.expected_drawdown_pct || item.stop_pct || 0;
            
            const executionQuality = item.fill_probability_score !== undefined
              ? formatPercentFa(item.fill_probability_score, 0)
              : "محاسبه نشده";
            const invalidationRule = item.invalidation?.type || "ثبت نشده";
            const fundamentalStatus = fundamentalGate?.passed ? "تأییدشده" : "تأیید نشده";
            const fundamentalReason = fundamentalGate?.reasons_fa?.[0]
              || "صورت مالی نقطه‌زمانی و دو منبع مستقل برای این نماد کامل نیست.";
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
                    <span style={{ color: "var(--text-secondary)", display: "block", fontSize: "0.68rem" }}>همگرایی</span>
                    <strong style={{ color: "var(--tse-green)" }}>{formatPercentFa(tape_power, 0)}</strong>
                  </div>
                  <div style={{ borderRight: "1px solid rgba(255,255,255,0.06)" }}>
                    <span style={{ color: "var(--text-secondary)", display: "block", fontSize: "0.68rem" }}>بنیادی</span>
                    <strong style={{ color: "var(--tse-gold)" }}>{formatPercentFa(fund_power, 0)}</strong>
                  </div>
                  <div style={{ borderRight: "1px solid rgba(255,255,255,0.06)" }}>
                    <span style={{ color: "var(--text-secondary)", display: "block", fontSize: "0.68rem" }}>شانس سود</span>
                    <strong style={{ color: "#f59e0b" }}>
                      {calibrationGate?.passed ? formatPercentFa(Math.round(p_profit), 0) : "کالیبره‌نشده"}
                    </strong>
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

                  {item.actionable === true ? (
                    <>
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
                    </>
                  ) : (
                    <div style={{ gridColumn: "span 3", borderRight: "1px solid rgba(255,255,255,0.06)", display: "flex", alignItems: "center", justifyContent: "center", padding: "0 0.5rem" }}>
                      <span style={{ fontSize: "0.7rem", color: "var(--tse-gold)", fontWeight: 700 }}>
                        تحلیل پژوهشی؛ بدون مجوز ورود و بدون سطوح اجرایی
                      </span>
                    </div>
                  )}
                </div>

                {/* 4. Dual Technical & Fundamental KPIs */}
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.6rem", fontSize: "0.76rem" }}>
                  <div style={{ backgroundColor: "rgba(15, 23, 42, 0.7)", padding: "0.65rem 0.8rem", borderRadius: "6px", border: "1px solid rgba(255,255,255,0.06)" }}>
                    <div style={{ color: "var(--tse-blue)", fontWeight: 800, marginBottom: "0.3rem", display: "flex", alignItems: "center", gap: "0.3rem" }}>
                      <TrendingUp size={14} /> <span>تکنیکال و تابلو:</span>
                    </div>
                    <div style={{ color: "var(--text-secondary)", lineHeight: 1.45 }}>
                      <div>• کیفیت اجرای فرضی: <strong style={{ color: "var(--tse-green)" }}>{executionQuality}</strong></div>
                      <div>• قاعده ابطال: <span style={{ color: "#ffffff" }}>{invalidationRule}</span></div>
                    </div>
                  </div>

                  <div style={{ backgroundColor: "rgba(15, 23, 42, 0.7)", padding: "0.65rem 0.8rem", borderRadius: "6px", border: "1px solid rgba(255,255,255,0.06)" }}>
                    <div style={{ color: "var(--tse-gold)", fontWeight: 800, marginBottom: "0.3rem", display: "flex", alignItems: "center", gap: "0.3rem" }}>
                      <FileText size={14} /> <span>بنیادی و کدال:</span>
                    </div>
                    <div style={{ color: "var(--text-secondary)", lineHeight: 1.45 }}>
                      <div>• گیت بنیادی: <strong style={{ color: fundamentalGate?.passed ? "var(--tse-green)" : "var(--tse-red)" }}>{fundamentalStatus}</strong></div>
                      <div title={fundamentalReason}>• شواهد: <span style={{ color: "#ffffff" }}>{fundamentalGate?.passed ? "کافی" : "ناکافی"}</span></div>
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
