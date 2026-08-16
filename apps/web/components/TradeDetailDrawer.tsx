"use client";
import React, { useState, useEffect } from "react";
import {
  X,
  TrendingUp,
  TrendingDown,
  Clock,
  Target,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Award,
  Layers,
  Activity,
  Calendar,
  DollarSign,
  PieChart,
  Sliders,
  CheckCircle2,
  AlertTriangle,
  ArrowUpRight,
  ArrowDownRight,
  Info,
  ChevronRight,
  Flame,
  Brain,
  History,
  FileText,
} from "lucide-react";
import { InteractiveStockChart } from "./InteractiveStockChart";
import {
  formatNumberFa,
  formatToman,
  formatRial,
  formatPercentFa,
  formatRFa,
  toPersianDigits,
} from "../lib/formatters";

interface TradeDetailDrawerProps {
  tradeId: string | null;
  onClose: () => void;
  onSelectSymbol?: (symbol: string) => void;
}

export const TradeDetailDrawer: React.FC<TradeDetailDrawerProps> = ({
  tradeId,
  onClose,
  onSelectSymbol,
}) => {
  const [trade, setTrade] = useState<any | null>(null);
  const [chartBars, setChartBars] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<"summary" | "timeline" | "chart" | "post_mortem">("summary");

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  useEffect(() => {
    if (!tradeId) {
      setTrade(null);
      setChartBars([]);
      return;
    }
    setLoading(true);
    fetch(`/api/v1/trade-history/trade/${tradeId}`)
      .then((r) => r.json())
      .then((data) => {
        setTrade(data);
        if (data?.symbol) {
          fetch(`/api/v1/symbols/${encodeURIComponent(data.symbol)}/chart?limit=50`)
            .then((res) => res.json())
            .then((cData) => setChartBars(cData?.bars || []))
            .catch(() => setChartBars([]));
        }
      })
      .catch((err) => {
        console.error("Error fetching trade detail:", err);
      })
      .finally(() => {
        setLoading(false);
      });
  }, [tradeId]);

  if (!tradeId) return null;

  const isWin = trade?.outcome_status === "WIN";
  const isLoss = trade?.outcome_status === "LOSS";

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: "rgba(10, 15, 29, 0.85)",
        backdropFilter: "blur(6px)",
        zIndex: 9999,
        display: "flex",
        justifyContent: "flex-end",
        animation: "fadeIn 0.2s ease-out",
      }}
      onClick={onClose}
    >
      <div
        style={{
          width: "100%",
          maxWidth: "850px",
          height: "100%",
          backgroundColor: "#0d1527",
          borderRight: "1px solid rgba(255, 255, 255, 0.1)",
          display: "flex",
          flexDirection: "column",
          boxShadow: "-10px 0 30px rgba(0,0,0,0.5)",
          overflow: "hidden",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Drawer Header */}
        <div
          style={{
            padding: "1.25rem 1.5rem",
            borderBottom: "1px solid rgba(255, 255, 255, 0.08)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            backgroundColor: "rgba(15, 23, 42, 0.95)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
            <button
              onClick={onClose}
              style={{
                background: "rgba(255, 255, 255, 0.05)",
                border: "1px solid rgba(255, 255, 255, 0.1)",
                color: "var(--text-secondary)",
                borderRadius: "8px",
                padding: "0.4rem",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
              }}
            >
              <X size={20} />
            </button>

            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
                <span style={{ fontSize: "1.3rem", fontWeight: 800, color: "#ffffff" }}>
                  {trade?.symbol || "در حال بارگذاری..."}
                </span>
                <span style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>
                  {trade?.company_name}
                </span>
                <span
                  style={{
                    fontSize: "0.75rem",
                    padding: "0.15rem 0.5rem",
                    borderRadius: "4px",
                    backgroundColor: "rgba(255, 255, 255, 0.06)",
                    color: "var(--text-secondary)",
                  }}
                >
                  {trade?.sector}
                </span>
              </div>
              <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginTop: "0.2rem" }}>
                استراتژی: <span style={{ color: "var(--tse-gold)", fontWeight: 600 }}>{trade?.strategy_name_fa}</span> ({trade?.strategy_version})
              </div>
            </div>
          </div>

          {/* Outcome Status Badge */}
          {trade && (
            <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "0.4rem",
                  padding: "0.4rem 0.8rem",
                  borderRadius: "8px",
                  fontWeight: 700,
                  fontSize: "0.88rem",
                  backgroundColor: isWin
                    ? "var(--tse-green-subtle)"
                    : isLoss
                    ? "var(--tse-red-subtle)"
                    : "rgba(255, 255, 255, 0.08)",
                  color: isWin ? "var(--tse-green)" : isLoss ? "var(--tse-red)" : "#cbd5e1",
                  border: `1px solid ${isWin ? "var(--tse-green-border)" : isLoss ? "var(--tse-red-border)" : "rgba(255, 255, 255, 0.15)"}`,
                }}
              >
                {isWin ? <ArrowUpRight size={16} /> : isLoss ? <ArrowDownRight size={16} /> : <Activity size={16} />}
                {formatPercentFa(trade.net_return_pct, 2)} ({formatRFa(trade.realized_R, 2)})
              </div>
            </div>
          )}
        </div>

        {/* Tab Navigation */}
        <div
          style={{
            display: "flex",
            borderBottom: "1px solid rgba(255, 255, 255, 0.08)",
            backgroundColor: "rgba(10, 15, 29, 0.6)",
            padding: "0 1.5rem",
          }}
        >
          {[
            { id: "summary", label: "خلاصه معامله و ریسک", icon: FileText },
            { id: "timeline", label: "تایم‌لاین اجرا و پله‌ها", icon: History },
            { id: "chart", label: "چارت بازپخش و سطوح", icon: Activity },
            { id: "post_mortem", label: "کالبدشکافی و درس‌های AI", icon: Brain },
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "0.5rem",
                  padding: "0.9rem 1.2rem",
                  fontSize: "0.85rem",
                  fontWeight: isActive ? 700 : 500,
                  color: isActive ? "var(--tse-gold)" : "var(--text-secondary)",
                  borderBottom: isActive ? "2px solid var(--tse-gold)" : "2px solid transparent",
                  background: "none",
                  borderTop: "none",
                  borderLeft: "none",
                  borderRight: "none",
                  cursor: "pointer",
                  transition: "all 0.15s ease",
                }}
              >
                <Icon size={16} />
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* Drawer Body */}
        <div style={{ flex: 1, overflowY: "auto", padding: "1.5rem" }}>
          {loading ? (
            <div style={{ textAlign: "center", padding: "4rem", color: "var(--text-secondary)" }}>
              در حال فراخوانی جزئیات و دفترکل حسابداری معامله...
            </div>
          ) : !trade ? (
            <div style={{ textAlign: "center", padding: "4rem", color: "var(--text-secondary)" }}>
              اطلاعات معامله در دسترس نیست.
            </div>
          ) : (
            <>
              {/* TAB 1: SUMMARY & FINANCIALS */}
              {activeTab === "summary" && (
                <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
                  {/* Top KPI Cards */}
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "0.85rem" }}>
                    <div className="card" style={{ padding: "0.9rem", textAlign: "center" }}>
                      <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginBottom: "0.3rem" }}>سود/زیان خالص</div>
                      <div style={{ fontSize: "1.1rem", fontWeight: 800, color: isWin ? "var(--tse-green)" : isLoss ? "var(--tse-red)" : "#ffffff" }}>
                        {trade.net_pnl_tomans ? formatToman(trade.net_pnl_tomans) : "۰"}
                      </div>
                    </div>

                    <div className="card" style={{ padding: "0.9rem", textAlign: "center" }}>
                      <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginBottom: "0.3rem" }}>ضریب سود محقق‌شده</div>
                      <div style={{ fontSize: "1.1rem", fontWeight: 800, color: "var(--tse-gold)" }}>
                        {formatRFa(trade.realized_R, 2)}
                      </div>
                    </div>

                    <div className="card" style={{ padding: "0.9rem", textAlign: "center" }}>
                      <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginBottom: "0.3rem" }}>مدت نگهداری</div>
                      <div style={{ fontSize: "1.1rem", fontWeight: 800, color: "#ffffff" }}>
                        {toPersianDigits(trade.holding_sessions)} جلسه <span style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>({toPersianDigits(trade.holding_duration_hours)} ساعت)</span>
                      </div>
                    </div>

                    <div className="card" style={{ padding: "0.9rem", textAlign: "center" }}>
                      <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginBottom: "0.3rem" }}>دلیل خروج</div>
                      <div style={{ fontSize: "0.95rem", fontWeight: 700, color: "var(--text-primary)" }}>
                        {trade.exit_reason_fa}
                      </div>
                    </div>
                  </div>

                  {/* Execution Prices & Values Table */}
                  <div className="card" style={{ padding: "1.2rem" }}>
                    <h4 style={{ fontSize: "0.9rem", fontWeight: 700, marginBottom: "1rem", color: "var(--tse-gold)", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                      <DollarSign size={16} /> تراز مالی و جزئیات قیمت‌های اجرا
                    </h4>

                    <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "1rem", fontSize: "0.85rem" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", padding: "0.4rem 0", borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                        <span style={{ color: "var(--text-secondary)" }}>قیمت برنامه ورود (Planned):</span>
                        <span style={{ fontWeight: 600 }}>{formatRial(trade.planned_entry)}</span>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between", padding: "0.4rem 0", borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                        <span style={{ color: "var(--text-secondary)" }}>قیمت میانگین ورود (Avg Entry):</span>
                        <span style={{ fontWeight: 600, color: "var(--tse-blue)" }}>{formatRial(trade.avg_entry_price)}</span>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between", padding: "0.4rem 0", borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                        <span style={{ color: "var(--text-secondary)" }}>قیمت میانگین خروج (Avg Exit):</span>
                        <span style={{ fontWeight: 600, color: isWin ? "var(--tse-green)" : "var(--tse-red)" }}>{formatRial(trade.avg_exit_price)}</span>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between", padding: "0.4rem 0", borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                        <span style={{ color: "var(--text-secondary)" }}>تعداد کل سهم:</span>
                        <span style={{ fontWeight: 600 }}>{formatNumberFa(trade.total_quantity)} برگه سهم</span>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between", padding: "0.4rem 0", borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                        <span style={{ color: "var(--text-secondary)" }}>ارزش ناخالص خرید:</span>
                        <span style={{ fontWeight: 600 }}>{formatToman(trade.gross_buy_value / 10)}</span>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between", padding: "0.4rem 0", borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                        <span style={{ color: "var(--text-secondary)" }}>ارزش ناخالص فروش:</span>
                        <span style={{ fontWeight: 600 }}>{formatToman(trade.gross_sell_value / 10)}</span>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between", padding: "0.4rem 0", borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                        <span style={{ color: "var(--text-secondary)" }}>کارمزد و مالیات کل (۱.۲۵۶۲٪):</span>
                        <span style={{ fontWeight: 600, color: "var(--tse-red)" }}>{formatToman(trade.total_cost / 10)}</span>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between", padding: "0.4rem 0", borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                        <span style={{ color: "var(--text-secondary)" }}>هزینه اسلیپیج اجرا:</span>
                        <span style={{ fontWeight: 600, color: "var(--tse-gold)" }}>{formatToman(trade.slippage_cost / 10)}</span>
                      </div>
                    </div>
                  </div>

                  {/* Excursion & Risk Limits */}
                  <div className="card" style={{ padding: "1.2rem" }}>
                    <h4 style={{ fontSize: "0.9rem", fontWeight: 700, marginBottom: "1rem", color: "var(--tse-gold)", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                      <Shield size={16} /> شاخص‌های نوسان، حد ضرر و مدیریت ریسک
                    </h4>

                    <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1rem", fontSize: "0.85rem" }}>
                      <div style={{ padding: "0.75rem", backgroundColor: "rgba(255,255,255,0.03)", borderRadius: "6px" }}>
                        <div style={{ color: "var(--text-secondary)", fontSize: "0.75rem", marginBottom: "0.3rem" }}>حداکثر نوسان مطلوب (MFE)</div>
                        <div style={{ fontSize: "1rem", fontWeight: 700, color: "var(--tse-green)" }}>{formatPercentFa(trade.MFE || 0, 1)}</div>
                      </div>
                      <div style={{ padding: "0.75rem", backgroundColor: "rgba(255,255,255,0.03)", borderRadius: "6px" }}>
                        <div style={{ color: "var(--text-secondary)", fontSize: "0.75rem", marginBottom: "0.3rem" }}>حداکثر نوسان نامطلوب (MAE)</div>
                        <div style={{ fontSize: "1rem", fontWeight: 700, color: "var(--tse-red)" }}>{formatPercentFa(-(trade.MAE || 0), 1)}</div>
                      </div>
                      <div style={{ padding: "0.75rem", backgroundColor: "rgba(255,255,255,0.03)", borderRadius: "6px" }}>
                        <div style={{ color: "var(--text-secondary)", fontSize: "0.75rem", marginBottom: "0.3rem" }}>ریسک تخصیصی از NAV</div>
                        <div style={{ fontSize: "1rem", fontWeight: 700, color: "var(--tse-gold)" }}>{formatPercentFa(trade.initial_risk_pct_nav, 1)}</div>
                      </div>
                    </div>

                    <div style={{ marginTop: "1rem", display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "0.8rem", fontSize: "0.85rem" }}>
                      <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <span style={{ color: "var(--text-secondary)" }}>حد ضرر اولیه:</span>
                        <span>{formatRial(trade.initial_stop)}</span>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <span style={{ color: "var(--text-secondary)" }}>حد ضرر نهایی (Trailing):</span>
                        <span>{formatRial(trade.final_stop)}</span>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <span style={{ color: "var(--text-secondary)" }}>تارگت اول (Target 1):</span>
                        <span>{formatRial(trade.target1)}</span>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <span style={{ color: "var(--text-secondary)" }}>تارگت دوم (Target 2):</span>
                        <span>{formatRial(trade.target2)}</span>
                      </div>
                    </div>
                  </div>

                  {/* Versioning & Audit Snapshot */}
                  <div className="card" style={{ padding: "1.2rem", backgroundColor: "rgba(15, 23, 42, 0.6)" }}>
                    <h4 style={{ fontSize: "0.85rem", fontWeight: 700, marginBottom: "0.6rem", color: "var(--text-secondary)" }}>
                      📌 متادیتای ره‌گیری و اسنپ‌شات نسخه‌ها (Audit Trail)
                    </h4>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "0.6rem", fontSize: "0.75rem" }}>
                      <span style={{ padding: "0.25rem 0.5rem", borderRadius: "4px", backgroundColor: "rgba(255,255,255,0.06)" }}>
                        نسخه استراتژی: <strong>{trade.strategy_version}</strong>
                      </span>
                      <span style={{ padding: "0.25rem 0.5rem", borderRadius: "4px", backgroundColor: "rgba(255,255,255,0.06)" }}>
                        مدل احتمالاتی: <strong>{trade.model_version}</strong>
                      </span>
                      <span style={{ padding: "0.25rem 0.5rem", borderRadius: "4px", backgroundColor: "rgba(255,255,255,0.06)" }}>
                        سند ریسک: <strong>{trade.risk_policy_version}</strong>
                      </span>
                      <span style={{ padding: "0.25rem 0.5rem", borderRadius: "4px", backgroundColor: "rgba(255,255,255,0.06)" }}>
                        دیتاست PIT: <strong>{trade.dataset_version}</strong>
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {/* TAB 2: EXECUTION TIMELINE */}
              {activeTab === "timeline" && (
                <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                  <div style={{ fontSize: "0.88rem", color: "var(--text-secondary)", marginBottom: "0.5rem" }}>
                    ره‌گیری کلیه رخدادها، پله‌های ورود (Scale-In)، انتقال استاپ و خروج‌های مرحله‌ای:
                  </div>

                  {trade.timeline && trade.timeline.length > 0 ? (
                    <div style={{ position: "relative", paddingRight: "1.5rem" }}>
                      <div
                        style={{
                          position: "absolute",
                          right: "6px",
                          top: "10px",
                          bottom: "10px",
                          width: "2px",
                          backgroundColor: "rgba(255, 255, 255, 0.15)",
                        }}
                      />

                      {trade.timeline.map((ev: any, idx: number) => {
                        const isEntry = ev.event_type.includes("ENTRY") || ev.event_type.includes("SCALE");
                        const isExit = ev.event_type.includes("EXIT") || ev.event_type.includes("TARGET");
                        const isStop = ev.event_type.includes("STOP");
                        return (
                          <div
                            key={ev.id || idx}
                            style={{
                              position: "relative",
                              marginBottom: "1.25rem",
                              display: "flex",
                              flexDirection: "column",
                              gap: "0.3rem",
                            }}
                          >
                            <div
                              style={{
                                position: "absolute",
                                right: "-1.5rem",
                                top: "4px",
                                width: "14px",
                                height: "14px",
                                borderRadius: "50%",
                                backgroundColor: isEntry ? "var(--tse-green)" : isExit ? "var(--tse-red)" : isStop ? "var(--tse-gold)" : "var(--tse-blue)",
                                border: "2px solid #0d1527",
                              }}
                            />

                            <div
                              style={{
                                backgroundColor: "rgba(255, 255, 255, 0.03)",
                                border: "1px solid rgba(255, 255, 255, 0.06)",
                                borderRadius: "8px",
                                padding: "0.85rem 1rem",
                              }}
                            >
                              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                                <span style={{ fontWeight: 700, color: "#ffffff", fontSize: "0.88rem" }}>
                                  {ev.event_description_fa}
                                </span>
                                <span style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                                  {new Date(ev.timestamp).toLocaleTimeString("fa-IR", { hour: "2-digit", minute: "2-digit" })}
                                </span>
                              </div>
                              <div style={{ display: "flex", gap: "1rem", marginTop: "0.4rem", fontSize: "0.78rem", color: "var(--text-secondary)" }}>
                                <span>قیمت: <strong style={{ color: "#ffffff" }}>{formatRial(ev.price)}</strong></span>
                                <span>حجم: <strong>{formatNumberFa(ev.quantity)} سهم</strong></span>
                                {ev.cash_flow_tomans !== 0 && (
                                  <span>گردش نقد: <strong style={{ color: ev.cash_flow_tomans > 0 ? "var(--tse-green)" : "var(--tse-red)" }}>{formatToman(ev.cash_flow_tomans)}</strong></span>
                                )}
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <div style={{ textAlign: "center", padding: "2rem", color: "var(--text-secondary)" }}>
                      رویدادی برای نمایش در تایم‌لاین ثبت نشده است.
                    </div>
                  )}
                </div>
              )}

              {/* TAB 3: CHART & LEVELS */}
              {activeTab === "chart" && (
                <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                  <InteractiveStockChart
                    symbol={trade.symbol}
                    nameFa={trade.company_name}
                    bars={chartBars}
                    plannedEntry={trade.planned_entry}
                    avgFillPrice={trade.avg_entry_price}
                    target1={trade.target1}
                    target2={trade.target2}
                    stopLoss={trade.final_stop || trade.initial_stop}
                    isGoodStock={isWin}
                  />
                </div>
              )}

              {/* TAB 4: POST-MORTEM & AI LESSONS */}
              {activeTab === "post_mortem" && (
                <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
                  <div className="card" style={{ padding: "1.35rem" }}>
                    <h4 style={{ fontSize: "0.95rem", fontWeight: 700, color: "var(--tse-gold)", marginBottom: "0.8rem", display: "flex", alignItems: "center", gap: "0.4rem" }}>
                      <Brain size={18} /> کالبدشکافی هوشمند ربات (AI Post-Mortem Analysis)
                    </h4>
                    <p style={{ fontSize: "0.85rem", color: "var(--text-primary)", lineHeight: 1.6 }}>
                      {trade.post_mortem_notes || "تحلیل ساختاریافته معامله با شواهد تکنیکال، جریان پول هوشمند و ترازنامه مالی شرکت انجام شده است."}
                    </p>
                  </div>

                  {trade.structured_lessons && trade.structured_lessons.length > 0 && (
                    <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                      <h4 style={{ fontSize: "0.9rem", fontWeight: 700, color: "#ffffff" }}>
                        درس‌های استخراج‌شده برای اصلاح استراتژی:
                      </h4>
                      {trade.structured_lessons.map((ls: any, i: number) => (
                        <div key={i} className="card" style={{ padding: "1rem", borderRight: "4px solid var(--tse-blue)" }}>
                          <div style={{ fontSize: "0.85rem", fontWeight: 700, color: "#ffffff", marginBottom: "0.3rem" }}>
                            {ls.finding_fa}
                          </div>
                          <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>
                            <strong>پیشنهاد اصلاحی:</strong> {ls.action_candidate_fa}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default TradeDetailDrawer;
