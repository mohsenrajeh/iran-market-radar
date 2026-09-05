"use client";
import React, { useState, useEffect } from "react";
import {
  TrendingUp,
  ArrowUpRight,
  ArrowDownRight,
  Layers,
  ShieldCheck,
  Flame,
  Briefcase,
  Target,
  Sparkles,
  PieChart,
  Activity,
  Coins,
  Eye,
  Award,
  CheckCircle2,
  Wallet,
  Lock,
} from "lucide-react";
import {
  formatNumberFa,
  formatToman,
  formatRial,
  formatPercentFa,
  toPersianDigits,
} from "../lib/formatters";

interface OverviewProps {
  overviewData: any;
  portfolioData?: any;
  topOpportunities: any[];
  sectors: any[];
  onSelectOpportunity: (opp: any) => void;
  onSelectSymbol?: (symbol: string) => void;
  onNavigateTab: (tab: any) => void;
}

export const OverviewView: React.FC<OverviewProps> = ({
  overviewData,
  portfolioData,
  topOpportunities,
  sectors,
  onSelectOpportunity,
  onSelectSymbol,
  onNavigateTab,
}) => {
  const indices = Array.isArray(overviewData?.indices) ? overviewData.indices : [];

  const totalBreadth = (overviewData?.breadth_advancers ?? 0) + (overviewData?.breadth_decliners ?? 0) + (overviewData?.breadth_unchanged ?? 0);
  const advPct = totalBreadth > 0 ? Math.round(((overviewData?.breadth_advancers ?? 0) / totalBreadth) * 100) : 0;

  // Synchronized Portfolio KPIs. The API owns the campaign capital baseline.
  const initialCapRials = portfolioData?.initial_cash ?? 100_000_000_000;
  const totalNavRials = portfolioData?.total_equity ?? initialCapRials;
  const totalNavTomans = totalNavRials / 10;
  const cashRials = portfolioData?.cash ?? initialCapRials;
  const cashTomans = cashRials / 10;
  const totalReturnPct = ((totalNavRials - initialCapRials) / initialCapRials) * 100;
  const openPositions = portfolioData?.positions?.filter((p: any) => p.is_open) || [];
  const openCount = portfolioData?.open_positions_count ?? openPositions.length;

  // Attractive Sectors Data
  const attractiveSectors = (sectors || []).slice(0, 4).map((sector: any) => ({
    name_fa: sector.name_fa,
    attractiveness_score: sector.breadth_pct ?? null,
    money_inflow_toman: formatToman((sector.net_real_inflow_rials ?? 0) / 10),
    top_symbols: [] as string[],
    catalyst: `مومنتوم ۲۰روزه ${formatPercentFa(sector.momentum_20d_pct ?? 0, 1)}، پهنای صعودی ${formatPercentFa(sector.breadth_pct ?? 0, 1)}، رتبه قدرت نسبی ${toPersianDigits(sector.relative_strength_rank ?? "—")}`,
  }));

  const handleStockClick = (symbolOrOpp: any) => {
    if (typeof symbolOrOpp === "string") {
      if (onSelectSymbol) onSelectSymbol(symbolOrOpp);
    } else if (symbolOrOpp && symbolOrOpp.symbol) {
      onSelectOpportunity(symbolOrOpp);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
      {/* ── 0. Market Indices Ribbon ─────────────────────────────────── */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "0.85rem" }}>
        {indices.map((idx: any, i: number) => {
          const isPos = idx.change_pct >= 0;
          return (
            <div
              key={i}
              className="card-panel"
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                padding: "0.9rem 1.2rem",
                backgroundColor: "var(--bg-surface)",
                border: "1px solid var(--border-subtle)",
              }}
            >
              <div>
                <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", fontWeight: 600 }}>{idx.name_fa}</div>
                <div style={{ fontSize: "1.2rem", fontWeight: 800, color: "#ffffff", marginTop: "2px" }}>
                  {formatNumberFa(idx.value)}
                </div>
              </div>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "0.2rem",
                  color: isPos ? "var(--tse-green)" : "var(--tse-red)",
                  backgroundColor: isPos ? "var(--tse-green-subtle)" : "var(--tse-red-subtle)",
                  padding: "0.3rem 0.6rem",
                  borderRadius: "var(--radius-sm)",
                  fontSize: "0.82rem",
                  fontWeight: 800,
                  border: isPos ? "1px solid var(--tse-green-border)" : "1px solid var(--tse-red-border)",
                }}
              >
                {isPos ? <ArrowUpRight size={15} /> : <ArrowDownRight size={15} />}
                <span>{formatPercentFa(idx.change_pct, 2)}</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* ── 1. Portfolio & Performance Executive Banner ───────────────── */}
      <div
        className="kpi-card"
        style={{
          padding: "1.35rem 1.6rem",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "1.25rem",
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <Award size={22} color="var(--tse-green)" />
            <h2 style={{ fontSize: "1.2rem", fontWeight: 900, color: "#f8fafc", margin: 0 }}>
              داشبورد عملکرد سرمایه‌گذاری و وضعیت کل دارایی‌ها
            </h2>
          </div>
          <p style={{ fontSize: "0.84rem", color: "var(--text-secondary)", marginTop: "0.4rem", marginBottom: 0 }}>
            سرمایه پایه: {formatToman(initialCapRials / 10)} • ارزش روز کل دارایی‌ها: {formatToman(totalNavTomans)}
          </p>
        </div>

        {/* Quick KPI Cluster */}
        <div style={{ display: "flex", alignItems: "center", gap: "1.8rem", flexWrap: "wrap" }}>
          <div>
            <div style={{ fontSize: "0.74rem", color: "var(--text-secondary)" }}>ارزش کل دارایی‌ها (Total NAV)</div>
            <div style={{ fontSize: "1.35rem", fontWeight: 900, color: "#f8fafc", marginTop: "2px" }}>
              {formatToman(totalNavTomans)}
            </div>
            <div style={{ fontSize: "0.76rem", color: totalReturnPct >= 0 ? "var(--tse-green)" : "var(--tse-red)", fontWeight: 800 }}>
              {formatPercentFa(totalReturnPct, 2)} سود کل پورتفو
            </div>
          </div>

          <div>
            <div style={{ fontSize: "0.74rem", color: "var(--text-secondary)" }}>نقدینگی آزاد در دسترس</div>
            <div style={{ fontSize: "1.35rem", fontWeight: 800, color: "var(--tse-gold)", marginTop: "2px" }}>
              {formatToman(cashTomans)}
            </div>
            <div style={{ fontSize: "0.74rem", color: "var(--text-secondary)" }}>
              {toPersianDigits(openCount)} معامله فعال در سبد
            </div>
          </div>

          <button
            onClick={() => onNavigateTab("open_positions")}
            className="btn-primary"
            style={{
              padding: "0.65rem 1.25rem",
              fontSize: "0.85rem",
            }}
          >
            <span>میزکار معاملات باز</span>
            <ArrowUpRight size={15} />
          </button>
        </div>
      </div>

      {/* ── 2. Active Holdings Direct Widget ───── */}
      <div className="card-panel">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem", flexWrap: "wrap", gap: "0.5rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <Briefcase size={18} color="var(--tse-green)" />
            <h3 style={{ margin: 0, fontWeight: 800, fontSize: "1.05rem", color: "var(--text-primary)" }}>
              موقعیت‌های معاملاتی باز در سبد (کلیه دارایی‌های فعال)
            </h3>
            <span style={{ fontSize: "0.75rem", color: "var(--tse-green)", fontWeight: 700, backgroundColor: "var(--tse-green-subtle)", padding: "2px 8px", borderRadius: "10px" }}>
              {toPersianDigits(openPositions.length)} سهم تحت مدیریت هوشمند
            </span>
          </div>

          <span style={{ fontSize: "0.76rem", color: "var(--text-secondary)" }}>
            پایش لحظه‌ای سود/زیان، نقاط ورود و اهداف قیمتی تمام موقعیت‌های زنده
          </span>
        </div>

        {openPositions.length === 0 ? (
          <div style={{ textAlign: "center", padding: "2rem", color: "var(--text-secondary)", backgroundColor: "var(--bg-surface)", borderRadius: "8px" }}>
            در حال حاضر معامله بازی وجود ندارد. ورود فقط پس از دریافت داده تازه و عبور کامل از گیت‌های تکنیکال، بنیادی و ریسک انجام می‌شود.
          </div>
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "0.85rem" }}>
            {openPositions.map((pos: any) => {
              const pnlToman = (pos.unrealized_pnl ?? ((pos.current_price - pos.average_entry_price) * pos.quantity)) / 10;
              const pnlPct = pos.unrealized_pnl_pct !== undefined ? pos.unrealized_pnl_pct : (((pos.current_price - pos.average_entry_price) / pos.average_entry_price) * 100);
              const isP = pnlPct >= 0;

              return (
                <div
                  key={pos.id || pos.symbol}
                  onClick={() => handleStockClick(pos.symbol)}
                  style={{
                    backgroundColor: "var(--bg-surface)",
                    padding: "0.9rem 1.1rem",
                    borderRadius: "8px",
                    border: "1px solid var(--border-subtle)",
                    borderRight: `4px solid ${isP ? "var(--tse-green)" : "var(--tse-red)"}`,
                    cursor: "pointer",
                    display: "flex",
                    flexDirection: "column",
                    gap: "0.55rem",
                    transition: "all 0.15s ease",
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.borderColor = "var(--border-active)")}
                  onMouseLeave={(e) => (e.currentTarget.style.borderColor = "var(--border-subtle)")}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
                      <span style={{ fontSize: "1.15rem", fontWeight: 900, color: "var(--text-primary)" }}>{pos.symbol}</span>
                      <span style={{ fontSize: "0.72rem", color: isP ? "var(--tse-green)" : "var(--tse-red)", backgroundColor: isP ? "var(--tse-green-subtle)" : "var(--tse-red-subtle)", padding: "2px 6px", borderRadius: "4px", fontWeight: 700 }}>
                        {isP ? "در سود" : "در اصلاح"}
                      </span>
                    </div>
                    <span style={{ fontSize: "0.82rem", fontWeight: 800, color: isP ? "var(--tse-green)" : "var(--tse-red)" }}>
                      {formatToman(pnlToman)} ({formatPercentFa(pnlPct, 2)})
                    </span>
                  </div>

                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.76rem", color: "var(--text-secondary)" }}>
                    <span>قیمت خرید: <strong>{formatRial(pos.average_entry_price)}</strong></span>
                    <span>قیمت روز: <strong style={{ color: "#ffffff" }}>{formatRial(pos.current_price)}</strong></span>
                  </div>

                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: "0.2rem", fontSize: "0.74rem", color: "var(--tse-blue)" }}>
                    <span style={{ fontWeight: 600 }}>مشاهده تحلیل و نمودار ←</span>
                    <span style={{ color: "var(--text-secondary)" }}>
                      هدف: {pos.target_price ? formatRial(pos.target_price) : "—"}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* ── 3. Attractive Sectors ────── */}
      <div className="card-panel">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem", flexWrap: "wrap", gap: "0.5rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <Sparkles size={20} color="var(--tse-blue)" />
            <h3 style={{ margin: 0, fontWeight: 800, fontSize: "1.05rem", color: "var(--text-primary)" }}>
              صنایع و بازارهای جذاب امروز (Attractive Market Sectors)
            </h3>
          </div>
          <span style={{ fontSize: "0.78rem", color: "var(--text-secondary)" }}>
            رتبه‌بندی بر اساس ورود پول هوشمند، رشد فروش کالا و امتیاز ارزش‌گذاری بنیادی
          </span>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "1rem" }}>
          {attractiveSectors.map((sec, idx) => (
            <div
              key={idx}
              style={{
                backgroundColor: "var(--bg-surface)",
                padding: "1rem 1.15rem",
                borderRadius: "8px",
                border: "1px solid var(--border-subtle)",
                display: "flex",
                flexDirection: "column",
                gap: "0.6rem",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontWeight: 800, fontSize: "1rem", color: "var(--text-primary)" }}>{sec.name_fa}</span>
                <span
                  style={{
                    backgroundColor: "rgba(59, 130, 246, 0.15)",
                    color: "var(--tse-blue)",
                    padding: "2px 8px",
                    borderRadius: "4px",
                    fontSize: "0.75rem",
                    fontWeight: 800,
                  }}
                >
                  پهنای صعودی {formatPercentFa(sec.attractiveness_score, 1)}
                </span>
              </div>

              <div style={{ fontSize: "0.78rem", color: "var(--text-secondary)", lineHeight: 1.4 }}>
                {sec.catalyst}
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderTop: "1px solid var(--border-subtle)", paddingTop: "0.5rem", fontSize: "0.75rem" }}>
                <div style={{ color: "var(--tse-green)", fontWeight: 700 }}>
                  ورود پول: {sec.money_inflow_toman}
                </div>
                <div style={{ display: "flex", gap: "0.3rem" }}>
                  {sec.top_symbols.map((sym, si) => (
                    <span
                      key={si}
                      onClick={() => handleStockClick(sym)}
                      style={{
                        backgroundColor: "rgba(255, 255, 255, 0.05)",
                        padding: "2px 7px",
                        borderRadius: "4px",
                        fontWeight: 700,
                        color: "var(--text-primary)",
                        cursor: "pointer",
                        border: "1px solid var(--border-subtle)",
                      }}
                    >
                      {sym}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── 4. Opportunities Preview ─────────────────── */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))", gap: "1.25rem" }}>
        <div className="card-panel">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.85rem" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
              <Flame size={18} color="var(--tse-green)" />
              <h3 style={{ margin: 0, fontWeight: 800, fontSize: "0.95rem", color: "var(--text-primary)" }}>
                فرصت‌های قابل اقدام برای ورود
              </h3>
            </div>
            <button
              onClick={() => onNavigateTab("opportunities")}
              style={{
                background: "none",
                border: "none",
                color: "var(--tse-blue)",
                fontSize: "0.78rem",
                fontWeight: 700,
                cursor: "pointer",
                fontFamily: "inherit",
              }}
            >
              مشاهده همه ←
            </button>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
            {topOpportunities.length === 0 ? (
              <div style={{ padding: "1.25rem", backgroundColor: "var(--bg-surface)", borderRadius: "6px", border: "1px solid var(--border-subtle)", textAlign: "center", color: "var(--text-secondary)", fontSize: "0.8rem" }}>
                <div style={{ fontWeight: 700, color: "#f8fafc", marginBottom: "0.3rem" }}>
                  🔍 هیچ نمادی در فیلترهای سخت‌گیرانه فعلی تایید نهایی نشد
                </div>
                <p style={{ margin: 0, fontSize: "0.74rem", color: "var(--text-secondary)", lineHeight: 1.4 }}>
                  موتور مدیریت ریسک جهت حفاظت از سرمایه، ورود را مشروط به نسبت سود به زیان بالای ۱:۱.۸ و تاییدیه همزمان کدال کرده است.
                </p>
              </div>
            ) : (
              topOpportunities.slice(0, 4).map((opp: any, idx: number) => {
                return (
                  <div
                    key={idx}
                    onClick={() => handleStockClick(opp)}
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      padding: "0.8rem 1rem",
                      backgroundColor: "var(--bg-surface)",
                      borderRadius: "6px",
                      border: "1px solid var(--border-subtle)",
                      cursor: "pointer",
                    }}
                  >
                    <div>
                      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                        <span style={{ fontWeight: 800, fontSize: "0.95rem", color: "#ffffff" }}>{opp.symbol}</span>
                        <span style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>{opp.name_fa}</span>
                      </div>
                      <div style={{ fontSize: "0.72rem", color: "var(--tse-gold)", marginTop: "2px" }}>
                        امتیاز: {toPersianDigits(opp.opportunity_score)} • رتبه {opp.grade || "—"}
                      </div>
                    </div>

                    <div style={{ textAlign: "left" }}>
                      <div style={{ fontSize: "0.82rem", fontWeight: 700, color: "var(--tse-blue)" }}>
                        {formatRial(opp.current_price ?? opp.entry_zone?.low ?? opp.entry_price ?? opp.cur_price)}
                      </div>
                      <div style={{ fontSize: "0.72rem", color: "var(--tse-green)", fontWeight: 600 }}>
                        بازده مورد انتظار: {formatPercentFa(opp.expected_return_pct ?? opp.target_pct, 1)}
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
