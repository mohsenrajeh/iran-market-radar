"use client";
import React, { useState, useEffect } from "react";
import { X, CheckCircle, AlertTriangle, ShoppingCart, Target, ShieldCheck, Zap, Layers, TrendingUp, Scale } from "lucide-react";
import { getStrategyFa } from "./translations";

interface DrawerProps {
  opportunity: any | null;
  onClose: () => void;
  onOrderPlaced: () => void;
}

export const OpportunityDrawer: React.FC<DrawerProps> = ({
  opportunity,
  onClose,
  onOrderPlaced,
}) => {
  const [loading, setLoading] = useState(false);
  const [feedbackMsg, setFeedbackMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Close on ESC key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  if (!opportunity) return null;

  const handlePlaceOrder = async () => {
    setLoading(true);
    setFeedbackMsg(null);
    try {
      const res = await fetch("/api/v1/paper/orders/from-signal", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ signal_id: opportunity.id }),
      });
      const data = await res.json();
      if (res.ok) {
        setFeedbackMsg({ type: "success", text: data.message || "سفارش خرید آزمایشی با موفقیت در پورتفو ثبت شد." });
        onOrderPlaced();
      } else {
        setFeedbackMsg({ type: "error", text: data.detail || "خطا در صدور سفارش خرید." });
      }
    } catch (err: any) {
      setFeedbackMsg({ type: "error", text: "عدم برقراری ارتباط با سرور." });
    } finally {
      setLoading(false);
    }
  };

  const targets = opportunity.exit_plan?.targets || [];
  const tp1 = targets[0] ?? null;
  const tp2 = targets[1] ?? null;
  const fundamentalGate = opportunity.decision_components?.fundamental_gate;
  const fundamentalMetrics = fundamentalGate?.metrics || {};
  const fundamentalSources = fundamentalGate?.provider_names || fundamentalGate?.source_keys || [];

  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: "rgba(0, 0, 0, 0.75)",
        backdropFilter: "blur(6px)",
        zIndex: 9999,
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        padding: "1rem",
      }}
    >
      {/* Modal Container */}
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: "680px",
          maxWidth: "96vw",
          maxHeight: "90vh",
          backgroundColor: "var(--bg-secondary)",
          borderRadius: "12px",
          border: "1px solid var(--border-subtle)",
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
          boxShadow: "0 20px 60px rgba(0,0,0,0.7)",
          animation: "fadeIn 0.2s ease-out",
        }}
      >
        {/* Modal Header */}
        <div
          style={{
            padding: "1.25rem 1.5rem",
            borderBottom: "1px solid var(--border-subtle)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            backgroundColor: "var(--bg-surface)",
          }}
        >
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
              <span style={{ fontSize: "1.4rem", fontWeight: 800, color: "var(--text-primary)" }}>
                {opportunity.symbol}
              </span>
              <span className={opportunity.grade === "A+" ? "grade-badge-aplus" : "grade-badge-a"}>
                رتبه {opportunity.grade}
              </span>
              <span
                style={{
                  fontSize: "0.75rem",
                  padding: "0.2rem 0.5rem",
                  borderRadius: "4px",
                  backgroundColor: "rgba(56, 139, 253, 0.15)",
                  color: "var(--tse-blue)",
                  fontWeight: 600,
                }}
              >
                {opportunity.horizon ? `افق ${opportunity.horizon.replace("d", "")} روزه` : "افق ثبت نشده"}
              </span>
            </div>
            <div style={{ fontSize: "0.82rem", color: "var(--text-muted)", marginTop: "0.3rem" }}>
              {opportunity.name_fa} • صنعت {opportunity.sector || "ثبت نشده"}
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: "var(--bg-hover)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "8px",
              color: "var(--text-secondary)",
              cursor: "pointer",
              padding: "0.45rem",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <X size={20} />
          </button>
        </div>

        {/* Modal Body */}
        <div style={{ padding: "1.5rem", display: "flex", flexDirection: "column", gap: "1.25rem", overflowY: "auto", flex: 1 }}>
          
          {/* Feedback banner */}
          {feedbackMsg && (
            <div
              style={{
                padding: "0.75rem 1rem",
                borderRadius: "var(--radius-sm)",
                backgroundColor: feedbackMsg.type === "success" ? "var(--tse-green-subtle)" : "var(--tse-red-subtle)",
                color: feedbackMsg.type === "success" ? "var(--tse-green)" : "var(--tse-red)",
                border: `1px solid ${feedbackMsg.type === "success" ? "rgba(46,160,67,0.4)" : "rgba(248,81,73,0.4)"}`,
                fontSize: "0.85rem",
                display: "flex",
                alignItems: "center",
                gap: "0.5rem",
                fontWeight: 600,
              }}
            >
              {feedbackMsg.type === "success" ? <CheckCircle size={16} /> : <AlertTriangle size={16} />}
              <span>{feedbackMsg.text}</span>
            </div>
          )}

          {/* 1. Quantitative 4-Metric Grid */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "0.75rem" }}>
            <div className="card-panel" style={{ padding: "0.85rem", backgroundColor: "var(--bg-surface)", textAlign: "center" }}>
              <div style={{ fontSize: "0.72rem", color: "var(--text-muted)", marginBottom: "0.3rem" }}>امتیاز رادار</div>
              <div style={{ fontSize: "1.3rem", fontWeight: 800, color: "var(--tse-green)" }} className="tabular-num">
                {opportunity.opportunity_score}
                <span style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>/۱۰۰</span>
              </div>
            </div>

            <div className="card-panel" style={{ padding: "0.85rem", backgroundColor: "var(--bg-surface)", textAlign: "center" }}>
              <div style={{ fontSize: "0.72rem", color: "var(--text-muted)", marginBottom: "0.3rem" }}>احتمال سوددهی</div>
              <div style={{ fontSize: "1.3rem", fontWeight: 800, color: "var(--tse-blue)" }} className="tabular-num">
                {Math.round(opportunity.p_profit * 100)}٪
              </div>
            </div>

            <div className="card-panel" style={{ padding: "0.85rem", backgroundColor: "var(--bg-surface)", textAlign: "center" }}>
              <div style={{ fontSize: "0.72rem", color: "var(--text-muted)", marginBottom: "0.3rem" }}>اطمینان تحلیل</div>
              <div style={{ fontSize: "1.3rem", fontWeight: 800, color: "var(--text-primary)" }} className="tabular-num">
                {opportunity.confidence}٪
              </div>
            </div>

            <div className="card-panel" style={{ padding: "0.85rem", backgroundColor: "var(--bg-surface)", textAlign: "center" }}>
              <div style={{ fontSize: "0.72rem", color: "var(--text-muted)", marginBottom: "0.3rem" }}>برتری نسبی سیگنال</div>
              <div style={{ fontSize: "1.1rem", fontWeight: 800, color: "var(--tse-amber)" }} className="tabular-num">
                صدک {opportunity.signal_strength}
              </div>
            </div>
          </div>

          {/* 2. Execution & Risk Levels */}
          <div className="card-panel" style={{ backgroundColor: "var(--bg-surface)", padding: "1rem" }}>
            <div style={{ fontWeight: 700, fontSize: "0.9rem", marginBottom: "0.75rem", display: "flex", alignItems: "center", gap: "0.4rem", color: "var(--text-primary)" }}>
              <Target size={16} color="var(--tse-blue)" />
              <span>محدوده ورود، حد ضرر و اهداف سود پیشنهادی</span>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem", fontSize: "0.84rem" }}>
              <div style={{ padding: "0.6rem 0.8rem", backgroundColor: "var(--bg-secondary)", borderRadius: "6px" }}>
                <div style={{ color: "var(--text-muted)", fontSize: "0.72rem", marginBottom: "0.2rem" }}>محدوده ورود پیشنهادی</div>
                <div style={{ fontWeight: 700, color: "var(--text-primary)" }} className="tabular-num">
                  {opportunity.entry_zone?.low?.toLocaleString("fa-IR")} تا {opportunity.entry_zone?.high?.toLocaleString("fa-IR")} ریال
                </div>
              </div>

              <div style={{ padding: "0.6rem 0.8rem", backgroundColor: "var(--bg-secondary)", borderRadius: "6px" }}>
                <div style={{ color: "var(--text-muted)", fontSize: "0.72rem", marginBottom: "0.2rem" }}>حد ضرر و سطح ابطال (Stop Loss)</div>
                <div style={{ fontWeight: 700, color: "var(--tse-red)" }} className="tabular-num">
                  {opportunity.invalidation?.price?.toLocaleString("fa-IR") || "-"} ریال
                </div>
              </div>

              <div style={{ padding: "0.6rem 0.8rem", backgroundColor: "var(--bg-secondary)", borderRadius: "6px" }}>
                <div style={{ color: "var(--text-muted)", fontSize: "0.72rem", marginBottom: "0.2rem" }}>تارگت اول ثبت‌شده</div>
                <div style={{ fontWeight: 700, color: "var(--tse-green)" }} className="tabular-num">
                  {tp1 ? `${tp1.toLocaleString("fa-IR")} ریال` : "-"}
                </div>
              </div>

              <div style={{ padding: "0.6rem 0.8rem", backgroundColor: "var(--bg-secondary)", borderRadius: "6px" }}>
                <div style={{ color: "var(--text-muted)", fontSize: "0.72rem", marginBottom: "0.2rem" }}>حد سود نهایی ثبت‌شده</div>
                <div style={{ fontWeight: 700, color: "var(--tse-green)" }} className="tabular-num">
                  {tp2 ? `${tp2.toLocaleString("fa-IR")} ریال` : "—"}
                </div>
              </div>
            </div>
          </div>

          {/* 3. Fundamental & Valuation Summary Card */}
          <div className="card-panel" style={{ backgroundColor: "var(--bg-surface)", padding: "1rem" }}>
            <div style={{ fontWeight: 700, fontSize: "0.9rem", marginBottom: "0.75rem", display: "flex", alignItems: "center", justifyContent: "space-between", color: "var(--text-primary)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
                <Scale size={16} color="var(--tse-green)" />
                <span>شاخص‌های ارزندگی بنیادی و سلامت مالی</span>
              </div>
              <span style={{ fontSize: "0.72rem", backgroundColor: fundamentalGate?.passed ? "var(--tse-green-subtle)" : "var(--tse-amber-subtle)", color: fundamentalGate?.passed ? "var(--tse-green)" : "var(--tse-amber)", padding: "2px 8px", borderRadius: "4px", fontWeight: 700 }}>
                {fundamentalGate?.passed ? "گیت بنیادی تأییدشده" : "گیت بنیادی تأیید نشده"}
              </span>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))", gap: "0.6rem", fontSize: "0.8rem" }}>
              <div style={{ padding: "0.5rem 0.75rem", backgroundColor: "var(--bg-secondary)", borderRadius: "6px" }}>
                <div style={{ color: "var(--text-muted)", fontSize: "0.7rem" }}>P/E سهم (گروه)</div>
                <div style={{ fontWeight: 800, color: "var(--text-primary)", marginTop: "2px" }} className="tabular-num">
                  {fundamentalMetrics.p_e_ratio ?? "—"} <span style={{ fontSize: "0.68rem", color: "var(--text-muted)" }}>({fundamentalMetrics.sector_p_e ?? "—"})</span>
                </div>
              </div>

              <div style={{ padding: "0.5rem 0.75rem", backgroundColor: "var(--bg-secondary)", borderRadius: "6px" }}>
                <div style={{ color: "var(--text-muted)", fontSize: "0.7rem" }}>رشد فروش ماهانه سالانه</div>
                <div style={{ fontWeight: 800, color: "var(--text-primary)", marginTop: "2px" }} className="tabular-num">
                  {fundamentalMetrics.monthly_sales_growth_yoy != null ? `${fundamentalMetrics.monthly_sales_growth_yoy.toLocaleString("fa-IR")}٪` : "—"}
                </div>
              </div>

              <div style={{ padding: "0.5rem 0.75rem", backgroundColor: "var(--bg-secondary)", borderRadius: "6px" }}>
                <div style={{ color: "var(--text-muted)", fontSize: "0.7rem" }}>بدهی به حقوق صاحبان سهام</div>
                <div style={{ fontWeight: 800, color: "var(--text-primary)", marginTop: "2px" }} className="tabular-num">
                  {fundamentalMetrics.debt_to_equity ?? "—"}
                </div>
              </div>

              <div style={{ padding: "0.5rem 0.75rem", backgroundColor: "var(--bg-secondary)", borderRadius: "6px" }}>
                <div style={{ color: "var(--text-muted)", fontSize: "0.7rem" }}>سلامت مالی پیوتروسکی</div>
                <div style={{ fontWeight: 800, color: "var(--tse-green)", marginTop: "2px" }} className="tabular-num">
                  {fundamentalMetrics.piotroski_f_score != null ? `${fundamentalMetrics.piotroski_f_score.toLocaleString("fa-IR")} از ۹` : "—"}
                </div>
              </div>
            </div>
            <div style={{ marginTop: "0.65rem", fontSize: "0.74rem", color: "var(--text-secondary)" }}>
              منابع ثبت‌شده: {fundamentalSources.length ? fundamentalSources.join("، ") : "هیچ منبع سالمی ثبت نشده"}
              {fundamentalGate?.as_of_utc ? ` • زمان مبنا: ${fundamentalGate.as_of_utc}` : ""}
            </div>
          </div>

          {/* 4. Strategy Voting Breakdown */}
          <div>
            <div style={{ fontWeight: 700, fontSize: "0.9rem", marginBottom: "0.6rem", display: "flex", alignItems: "center", gap: "0.4rem", color: "var(--text-primary)" }}>
              <Layers size={16} color="var(--tse-blue)" />
              <span>نتایج بررسی و آرای استراتژی‌های کمّی بازار ({opportunity.strategy_votes?.length || 0} استراتژی تأییدکننده)</span>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
              {opportunity.strategy_votes?.map((sv: any, idx: number) => {
                const sKey = sv.strategy || sv.strategy_key || "";
                return (
                  <div
                    key={idx}
                    style={{
                      backgroundColor: "var(--bg-surface)",
                      padding: "0.75rem 0.9rem",
                      borderRadius: "8px",
                      border: "1px solid var(--border-subtle)",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.3rem" }}>
                      <span style={{ fontWeight: 700, fontSize: "0.85rem", color: "var(--text-primary)" }}>
                        {getStrategyFa(sKey)}
                      </span>
                      <span
                        style={{
                          backgroundColor: "rgba(56, 139, 253, 0.15)",
                          color: "var(--tse-blue)",
                          padding: "0.15rem 0.5rem",
                          borderRadius: "4px",
                          fontSize: "0.75rem",
                          fontWeight: 700,
                        }}
                        className="tabular-num"
                      >
                        قدرت رأی: {Math.round((sv.vote || 0) * 100)}٪
                      </span>
                    </div>
                    <div style={{ fontSize: "0.78rem", color: "var(--text-secondary)", lineHeight: "1.5" }}>
                      {sv.reason_fa || "دلیل ماشینی برای این رأی ثبت نشده است."}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* 4. Top Reasons */}
          {opportunity.top_reasons_fa && opportunity.top_reasons_fa.length > 0 && (
            <div>
              <div style={{ fontWeight: 700, fontSize: "0.9rem", marginBottom: "0.5rem", color: "var(--text-primary)" }}>
                دلایل برتر در رتبه‌بندی رادار:
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.35rem" }}>
                {opportunity.top_reasons_fa.map((r: string, idx: number) => (
                  <div key={idx} style={{ fontSize: "0.82rem", color: "var(--text-secondary)", display: "flex", alignItems: "flex-start", gap: "0.4rem" }}>
                    <CheckCircle size={14} color="var(--tse-green)" style={{ marginTop: "3px", flexShrink: 0 }} />
                    <span>{r}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 5. Risk Flags */}
          {opportunity.risk_flags_fa && opportunity.risk_flags_fa.length > 0 && (
            <div>
              <div style={{ fontWeight: 700, fontSize: "0.9rem", marginBottom: "0.5rem", color: "var(--tse-amber)" }}>
                هشدارهای ریسک و حجم مبنا:
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.35rem" }}>
                {opportunity.risk_flags_fa.map((rf: string, idx: number) => (
                  <div key={idx} style={{ fontSize: "0.82rem", color: "var(--tse-amber)", display: "flex", alignItems: "flex-start", gap: "0.4rem" }}>
                    <AlertTriangle size={14} color="var(--tse-amber)" style={{ marginTop: "3px", flexShrink: 0 }} />
                    <span>{rf}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div
          style={{
            padding: "1rem 1.5rem",
            borderTop: "1px solid var(--border-subtle)",
            backgroundColor: "var(--bg-surface)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: "1rem",
          }}
        >
          <button
            className="btn-primary"
            onClick={handlePlaceOrder}
            disabled={loading || opportunity.actionable !== true}
            style={{ flex: 1, justifyContent: "center", padding: "0.75rem 1rem", fontSize: "0.88rem", fontWeight: 700 }}
          >
            <ShoppingCart size={18} />
            <span>{loading ? "در حال ثبت سفارش..." : opportunity.actionable === true ? "ثبت سفارش خرید کاغذی" : "سیگنال غیرقابل معامله"}</span>
          </button>
          <button className="btn-outline" onClick={onClose} style={{ padding: "0.75rem 1.25rem", fontSize: "0.85rem" }}>
            بستن
          </button>
        </div>
      </div>
    </div>
  );
};
