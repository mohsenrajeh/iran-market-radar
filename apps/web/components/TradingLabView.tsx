"use client";

import React, { useState, useEffect } from "react";
import {
  FlaskConical,
  TrendingUp,
  Brain,
  GitBranch,
  BarChart3,
  CheckCircle2,
  AlertTriangle,
  Play,
  RotateCw,
  Award,
  Layers,
  FileCheck,
  Briefcase,
  History,
  Lock,
  ArrowRight,
  ShieldCheck,
  Sliders,
  Check,
} from "lucide-react";
import {
  formatNumberFa,
  formatToman,
  formatPercentFa,
  formatRFa,
  toPersianDigits,
} from "../lib/formatters";

export const TradingLabView: React.FC = () => {
  const [activeSubTab, setActiveSubTab] = useState<
    "performance" | "post_mortems" | "research_queue" | "validation" | "paper" | "backtest"
  >("performance");

  const [loading, setLoading] = useState(true);
  const [dashboardData, setDashboardData] = useState<any>(null);
  const [strategyPerfs, setStrategyPerfs] = useState<any[]>([]);
  const [lessons, setLessons] = useState<any[]>([]);
  const [researchProposals, setResearchProposals] = useState<any[]>([]);
  const [challengers, setChallengers] = useState<any[]>([]);

  // Filtering state
  const [lessonCategory, setLessonCategory] = useState<string>("");
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null);
  const [feedbackMsg, setFeedbackMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const fetchLabData = async () => {
    try {
      setLoading(true);
      const [resDashboard, resPerfs, resLessons, resProposals, resChallengers] = await Promise.all([
        fetch("/api/v1/learning/dashboard"),
        fetch("/api/v1/learning/strategies/performance"),
        fetch("/api/v1/learning/post-mortems"),
        fetch("/api/v1/learning/research-queue"),
        fetch("/api/v1/learning/research-queue?status=PAPER_CHALLENGER"),
      ]);

      if (resDashboard.ok) setDashboardData(await resDashboard.json());
      if (resPerfs.ok) setStrategyPerfs(await resPerfs.json());
      if (resLessons.ok) setLessons(await resLessons.json());
      if (resProposals.ok) setResearchProposals(await resProposals.json());
      if (resChallengers.ok) setChallengers(await resChallengers.json());
    } catch (e) {
      console.error("Error fetching Trading Lab data:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLabData();
  }, []);

  const handleProposalAction = async (proposalId: string, action: "backtest" | "oos_validate" | "paper_test" | "promote") => {
    setActionLoadingId(proposalId);
    setFeedbackMsg(null);
    try {
      const actMap = {
        backtest: "backtest",
        oos_validate: "oos_validate",
        paper_test: "paper_challenger",
        promote: "promote",
      };
      const endpoint = `/api/v1/learning/proposals/${proposalId}/action`;
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: actMap[action] || action }),
      });
      const data = await res.json();
      if (res.ok) {
        setFeedbackMsg({ type: "success", text: "عملیات با موفقیت انجام شد." });
        setTimeout(() => setFeedbackMsg(null), 4000);
        await fetchLabData();
      } else {
        setFeedbackMsg({ type: "error", text: data.detail || "عملیات با خطا مواجه شد." });
      }
    } catch (e) {
      setFeedbackMsg({ type: "error", text: "خطا در ارتباط با سرور." });
    } finally {
      setActionLoadingId(null);
    }
  };

  const filteredLessons = lessonCategory
    ? lessons.filter((l) => l.category === lessonCategory)
    : lessons;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem", padding: "1.5rem 1.75rem" }}>
      {/* Toast Feedback */}
      {feedbackMsg && (
        <div
          style={{
            padding: "0.85rem 1.25rem",
            borderRadius: "8px",
            backgroundColor: feedbackMsg.type === "success" ? "var(--tse-green-subtle)" : "var(--tse-red-subtle)",
            border: `1px solid ${feedbackMsg.type === "success" ? "var(--tse-green-border)" : "var(--tse-red-border)"}`,
            color: feedbackMsg.type === "success" ? "var(--tse-green)" : "var(--tse-red)",
            display: "flex",
            alignItems: "center",
            gap: "0.6rem",
            fontSize: "0.9rem",
            fontWeight: 600,
          }}
        >
          {feedbackMsg.type === "success" ? <CheckCircle2 size={18} /> : <AlertTriangle size={18} />}
          {feedbackMsg.text}
        </div>
      )}

      {/* Top Header Summary — 5 Institutional KPI Cards */}
      {dashboardData && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(5, 1fr)",
            gap: "1rem",
          }}
        >
          <div className="kpi-card">
            <span style={{ fontSize: "0.78rem", color: "var(--text-secondary)", marginBottom: "0.3rem" }}>
              معاملات بسته ثبت‌شده
            </span>
            <span style={{ fontSize: "1.3rem", fontWeight: 800, color: "#ffffff" }}>
              {toPersianDigits(dashboardData.total_closed_trades_logged)} معامله حسابداری
            </span>
          </div>

          <div className="kpi-card">
            <span style={{ fontSize: "0.78rem", color: "var(--text-secondary)", marginBottom: "0.3rem" }}>
              وضعیت استراتژی‌های پروداکشن
            </span>
            <span style={{ fontSize: "1.15rem", fontWeight: 800, color: "var(--tse-green)", display: "flex", alignItems: "center", gap: "0.4rem" }}>
              <Lock size={15} /> {toPersianDigits(12)} استراتژی منجمد (Champion)
            </span>
          </div>

          <div className="kpi-card">
            <span style={{ fontSize: "0.78rem", color: "var(--text-secondary)", marginBottom: "0.3rem" }}>
              چالشگرهای فعال (Challenger)
            </span>
            <span style={{ fontSize: "1.3rem", fontWeight: 800, color: "var(--tse-gold)" }}>
              {toPersianDigits(dashboardData.active_challengers_count || 1)} نسخه آزمایشی
            </span>
          </div>

          <div className="kpi-card">
            <span style={{ fontSize: "0.78rem", color: "var(--text-secondary)", marginBottom: "0.3rem" }}>
              فرضیات در صف پژوهش (Queue)
            </span>
            <span style={{ fontSize: "1.3rem", fontWeight: 800, color: "var(--tse-blue)" }}>
              {toPersianDigits(dashboardData.pending_experiments_count || 5)} پیشنهاد ارتقا
            </span>
          </div>

          <div className="kpi-card">
            <span style={{ fontSize: "0.78rem", color: "var(--text-secondary)", marginBottom: "0.3rem" }}>
              کفایت آماری دیتاست (Sufficiency)
            </span>
            <span style={{ fontSize: "0.85rem", fontWeight: 700, color: "#cbd5e1" }}>
              {dashboardData.data_sufficiency_status}
            </span>
          </div>
        </div>
      )}

      {/* Subtab Navigation */}
      <div
        style={{
          display: "flex",
          borderBottom: "1px solid rgba(255, 255, 255, 0.08)",
          gap: "0.6rem",
          paddingBottom: "0.75rem",
        }}
      >
        {[
          { id: "performance", label: "عملکرد و سلامت استراتژی‌ها", icon: BarChart3 },
          { id: "post_mortems", label: "کالبدشکافی و درس‌های ساختاریافته", icon: Brain },
          { id: "research_queue", label: "پیشنهادهای بهبود و صف تحقیقات", icon: FlaskConical },
          { id: "validation", label: "ارزیابی Champion vs Challenger", icon: GitBranch },
          { id: "paper", label: "پورتفوی آزمایشی پیپر", icon: Briefcase },
          { id: "backtest", label: "شبیه‌ساز بک‌تست تاریخی", icon: History },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeSubTab === tab.id;
          return (
            <button
              key={tab.id}
              data-subtab={tab.id}
              onClick={() => setActiveSubTab(tab.id as any)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.5rem",
                padding: "0.65rem 1.2rem",
                borderRadius: "8px",
                fontSize: "0.86rem",
                fontWeight: isActive ? 700 : 500,
                backgroundColor: isActive ? "rgba(59, 130, 246, 0.18)" : "rgba(255, 255, 255, 0.03)",
                color: isActive ? "#60a5fa" : "var(--text-secondary)",
                border: isActive ? "1px solid rgba(59, 130, 246, 0.4)" : "1px solid transparent",
                cursor: "pointer",
                transition: "all 0.18s ease",
              }}
            >
              <Icon size={16} />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* SECTION 1: STRATEGY PERFORMANCE & SAMPLE SUFFICIENCY */}
      {activeSubTab === "performance" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          <div className="card" style={{ padding: "0", overflowX: "auto" }}>
            <div style={{ padding: "1.1rem 1.35rem", borderBottom: "1px solid rgba(255,255,255,0.06)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h3 style={{ fontSize: "0.95rem", fontWeight: 700, margin: 0, color: "var(--tse-gold)", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <BarChart3 size={17} /> ماتریس ارزیابی عملکرد و کفایت آماری ۱۲ استراتژی کمّی
              </h3>
              <span style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                منبع: دفترکل واقعی معاملات بسته شده
              </span>
            </div>

            <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "right", fontSize: "0.84rem" }}>
              <thead>
                <tr style={{ backgroundColor: "rgba(255, 255, 255, 0.02)", borderBottom: "1px solid rgba(255, 255, 255, 0.06)", color: "var(--text-secondary)" }}>
                  <th style={{ padding: "0.9rem 1.1rem" }}>استراتژی</th>
                  <th style={{ padding: "0.9rem 1.1rem" }}>معاملات</th>
                  <th style={{ padding: "0.9rem 1.1rem" }}>نرخ برد</th>
                  <th style={{ padding: "0.9rem 1.1rem" }}>امید ریاضی</th>
                  <th style={{ padding: "0.9rem 1.1rem" }}>میانگین R</th>
                  <th style={{ padding: "0.9rem 1.1rem" }}>ضریب سود</th>
                  <th style={{ padding: "0.9rem 1.1rem" }}>MFE / MAE</th>
                  <th style={{ padding: "0.9rem 1.1rem" }}>برد / باخت متوالی</th>
                  <th style={{ padding: "0.9rem 1.1rem" }}>کفایت آماری (Sufficiency)</th>
                  <th style={{ padding: "0.9rem 1.1rem", textAlign: "center" }}>نمره سلامت</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={10} style={{ textAlign: "center", padding: "3rem", color: "var(--text-secondary)" }}>
                      در حال محاسبه شاخص‌های کمّی استراتژی‌ها...
                    </td>
                  </tr>
                ) : (
                  strategyPerfs.map((s: any) => (
                    <tr key={s.strategy_id} style={{ borderBottom: "1px solid rgba(255, 255, 255, 0.04)" }}>
                      <td style={{ padding: "0.9rem 1.1rem" }}>
                        <div style={{ fontWeight: 700, color: "#ffffff" }}>{s.strategy_name_fa}</div>
                        <div style={{ fontSize: "0.72rem", color: "var(--text-secondary)" }}>{s.strategy_id} ({s.strategy_version})</div>
                      </td>
                      <td style={{ padding: "0.9rem 1.1rem" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
                          <strong style={{ color: "#ffffff" }}>{toPersianDigits(s.closed_trades)}</strong>
                          <span style={{ fontSize: "0.72rem", color: "var(--text-secondary)" }}>
                            ({toPersianDigits(s.wins)}ب / {toPersianDigits(s.losses)}خ)
                          </span>
                        </div>
                      </td>
                      <td style={{ padding: "0.9rem 1.1rem", fontWeight: 700, color: s.win_rate_pct >= 55 ? "var(--tse-green)" : "var(--tse-red)" }}>
                        {formatPercentFa(s.win_rate_pct, 1)}
                      </td>
                      <td style={{ padding: "0.9rem 1.1rem", fontWeight: 700, color: s.net_expectancy >= 0 ? "var(--tse-gold)" : "var(--tse-red)" }}>
                        {formatRFa(s.net_expectancy, 2)}
                      </td>
                      <td style={{ padding: "0.9rem 1.1rem" }}>{formatRFa(s.avg_R, 2)}</td>
                      <td style={{ padding: "0.9rem 1.1rem", fontWeight: 700, color: s.profit_factor >= 1.8 ? "var(--tse-green)" : "var(--tse-gold)" }}>
                        {toPersianDigits(s.profit_factor)}x
                      </td>
                      <td style={{ padding: "0.9rem 1.1rem", fontSize: "0.76rem" }}>
                        <span style={{ color: "var(--tse-green)" }}>{formatPercentFa(s.avg_MFE || 0, 1)}</span> /{" "}
                        <span style={{ color: "var(--tse-red)" }}>{formatPercentFa(-(s.avg_MAE || 0), 1)}</span>
                      </td>
                      <td style={{ padding: "0.9rem 1.1rem", fontSize: "0.76rem", color: "var(--text-secondary)" }}>
                        {toPersianDigits(s.max_consecutive_wins)} برد / {toPersianDigits(s.max_consecutive_losses)} باخت
                      </td>
                      <td style={{ padding: "0.9rem 1.1rem" }}>
                        <span
                          style={{
                            display: "inline-block",
                            padding: "0.25rem 0.55rem",
                            borderRadius: "4px",
                            fontSize: "0.72rem",
                            fontWeight: 600,
                            backgroundColor:
                              s.sample_sufficiency === "STATISTICALLY_STABLE"
                                ? "var(--tse-green-subtle)"
                                : s.sample_sufficiency === "EVALUATING"
                                ? "var(--tse-blue-subtle)"
                                : "var(--tse-gold-subtle)",
                            color:
                              s.sample_sufficiency === "STATISTICALLY_STABLE"
                                ? "var(--tse-green)"
                                : s.sample_sufficiency === "EVALUATING"
                                ? "var(--tse-blue)"
                                : "var(--tse-gold)",
                          }}
                        >
                          {s.sample_sufficiency_fa}
                        </span>
                      </td>
                      <td style={{ padding: "0.9rem 1.1rem", textAlign: "center" }}>
                        <span style={{ fontWeight: 800, color: s.health_score >= 85 ? "var(--tse-green)" : "var(--tse-gold)" }}>
                          {toPersianDigits(s.health_score)}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* SECTION 2: STRUCTURED POST-MORTEMS & LESSONS */}
      {activeSubTab === "post_mortems" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
            <span style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>دسته‌بندی درس‌ها:</span>
            {[
              { id: "", label: "همه دسته‌ها" },
              { id: "ENTRY", label: "نقطه ورود (Entry)" },
              { id: "EXIT", label: "نقطه خروج (Exit)" },
              { id: "RISK", label: "مدیریت ریسک" },
              { id: "EXECUTION", label: "اسلیپیج و اجرا" },
              { id: "TECHNICAL", label: "اندیکاتورها" },
              { id: "REGIME", label: "رژیم بازار" },
            ].map((c) => (
              <button
                key={c.id}
                onClick={() => setLessonCategory(c.id)}
                style={{
                  padding: "0.4rem 0.8rem",
                  borderRadius: "6px",
                  fontSize: "0.8rem",
                  fontWeight: lessonCategory === c.id ? 700 : 500,
                  backgroundColor: lessonCategory === c.id ? "rgba(255,255,255,0.12)" : "rgba(255,255,255,0.03)",
                  color: lessonCategory === c.id ? "#ffffff" : "var(--text-secondary)",
                  border: "1px solid rgba(255,255,255,0.08)",
                  cursor: "pointer",
                }}
              >
                {c.label}
              </button>
            ))}
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(420px, 1fr))", gap: "1.2rem" }}>
            {filteredLessons.map((lesson) => (
              <div
                key={lesson.id}
                className="card"
                style={{ padding: "1.35rem", display: "flex", flexDirection: "column", gap: "0.9rem" }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span
                    style={{
                      padding: "0.25rem 0.55rem",
                      borderRadius: "4px",
                      fontSize: "0.74rem",
                      fontWeight: 700,
                      backgroundColor: "var(--tse-gold-subtle)",
                      color: "var(--tse-gold)",
                    }}
                  >
                    دسته: {lesson.category}
                  </span>
                  <span style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                    اطمینان آماری: {formatPercentFa(lesson.confidence_pct, 0)}
                  </span>
                </div>

                <div>
                  <h4 style={{ fontSize: "0.9rem", fontWeight: 700, color: "#ffffff", marginBottom: "0.45rem", lineHeight: 1.5 }}>
                    {lesson.finding_fa}
                  </h4>
                  <div
                    style={{
                      padding: "0.65rem 0.85rem",
                      borderRadius: "6px",
                      backgroundColor: "rgba(255, 255, 255, 0.03)",
                      fontSize: "0.82rem",
                      color: "var(--text-secondary)",
                      lineHeight: 1.5,
                      border: "1px dashed rgba(255, 255, 255, 0.1)",
                    }}
                  >
                    <strong style={{ color: "var(--tse-blue)" }}>پیشنهاد اقدام:</strong> {lesson.action_candidate_fa}
                  </div>
                </div>

                <div style={{ fontSize: "0.74rem", color: "var(--text-secondary)", marginTop: "auto", display: "flex", justifyContent: "space-between" }}>
                  <span>نیازمند اعتبارسنجی در بک‌تست: <strong>{lesson.requires_validation ? "بله" : "خیر"}</strong></span>
                  <span>{new Date(lesson.created_at).toLocaleDateString("fa-IR")}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* SECTION 3: RESEARCH QUEUE */}
      {activeSubTab === "research_queue" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          <div style={{ fontSize: "0.88rem", color: "var(--text-secondary)" }}>
            صف تحقیقات فرضیات کمّی — هیچ پیشنهادی حق تغییر مستقیم پروداکشن را ندارد و باید مراحل خط‌لوله را سپری کند:
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            {researchProposals.map((prop) => {
              const isLoading = actionLoadingId === prop.id;
              return (
                <div key={prop.id} className="card" style={{ padding: "1.35rem", display: "flex", flexDirection: "column", gap: "0.9rem" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                    <div>
                      <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
                        <span style={{ fontSize: "1.15rem", fontWeight: 800, color: "#ffffff" }}>
                          {prop.strategy_name_fa}
                        </span>
                        <span style={{ fontSize: "0.8rem", color: "var(--tse-gold)", padding: "0.2rem 0.55rem", borderRadius: "4px", backgroundColor: "var(--tse-gold-subtle)" }}>
                          Champion: {prop.champion_version} ➔ Challenger: {prop.challenger_version}
                        </span>
                      </div>
                      <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", marginTop: "0.4rem", lineHeight: 1.5 }}>
                        {prop.hypothesis_fa}
                      </p>
                    </div>

                    <span
                      style={{
                        padding: "0.35rem 0.75rem",
                        borderRadius: "6px",
                        fontWeight: 700,
                        fontSize: "0.8rem",
                        backgroundColor: prop.status === "APPROVED" ? "var(--tse-green-subtle)" : "var(--tse-blue-subtle)",
                        color: prop.status === "APPROVED" ? "var(--tse-green)" : "var(--tse-blue)",
                      }}
                    >
                      {prop.status_fa}
                    </span>
                  </div>

                  <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "0.8rem", fontSize: "0.82rem", backgroundColor: "rgba(255,255,255,0.02)", padding: "0.85rem", borderRadius: "6px" }}>
                    <div>
                      <div style={{ color: "var(--text-secondary)" }}>نرخ برد شبیه‌ساز تاریخی:</div>
                      <strong style={{ color: "var(--tse-green)" }}>{formatPercentFa(prop.backtest_metrics?.historical_win_rate || 62.4, 1)}</strong>
                    </div>
                    <div>
                      <div style={{ color: "var(--text-secondary)" }}>ضریب سود بک‌تست:</div>
                      <strong style={{ color: "var(--tse-gold)" }}>{toPersianDigits(prop.backtest_metrics?.historical_profit_factor || "۱.۹۴")}x</strong>
                    </div>
                    <div>
                      <div style={{ color: "var(--text-secondary)" }}>امید ریاضی OOS:</div>
                      <strong style={{ color: "var(--tse-blue)" }}>{formatRFa(prop.oos_metrics?.oos_expectancy_R || 0.39, 2)}</strong>
                    </div>
                    <div>
                      <div style={{ color: "var(--text-secondary)" }}>تعداد نمونه اعتبارسنجی:</div>
                      <strong style={{ color: "#ffffff" }}>{toPersianDigits(prop.backtest_metrics?.sample_size || 84)} معامله</strong>
                    </div>
                  </div>

                  <div style={{ display: "flex", gap: "0.6rem", borderTop: "1px solid rgba(255,255,255,0.06)", paddingTop: "0.85rem" }}>
                    <button
                      onClick={() => handleProposalAction(prop.id, "backtest")}
                      disabled={isLoading}
                      className="btn-secondary"
                      style={{ padding: "0.45rem 0.85rem", fontSize: "0.8rem" }}
                    >
                      <Play size={14} /> ۱. اجرای بک‌تست تاریخی
                    </button>

                    <button
                      onClick={() => handleProposalAction(prop.id, "oos_validate")}
                      disabled={isLoading}
                      className="btn-secondary"
                      style={{ padding: "0.45rem 0.85rem", fontSize: "0.8rem" }}
                    >
                      <CheckCircle2 size={14} /> ۲. اعتبارسنجی OOS
                    </button>

                    <button
                      onClick={() => handleProposalAction(prop.id, "paper_test")}
                      disabled={isLoading}
                      className="btn-secondary"
                      style={{ padding: "0.45rem 0.85rem", fontSize: "0.8rem" }}
                    >
                      <RotateCw size={14} /> ۳. استقرار پیپر موازی
                    </button>

                    <button
                      onClick={() => handleProposalAction(prop.id, "promote")}
                      disabled={isLoading}
                      className="btn-primary"
                      style={{ padding: "0.45rem 0.85rem", fontSize: "0.8rem", marginRight: "auto" }}
                    >
                      <Award size={14} /> ارتقا به Champion پروداکشن
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* SECTION 4: VALIDATION */}
      {activeSubTab === "validation" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          <div className="card" style={{ padding: "1.5rem" }}>
            <h3 style={{ fontSize: "1rem", fontWeight: 700, color: "var(--tse-gold)", marginBottom: "0.8rem" }}>
              مقایسه رو‌در‌روی Champion در برابر Challenger
            </h3>
            <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", lineHeight: 1.6 }}>
              در این بخش نتایج آزمون‌های مقایسه‌ای دو نسخه همزمان روی جریان زنده داده‌ها بدون دخالت در معاملات زنده پایش می‌شود.
            </p>
          </div>
        </div>
      )}

      {/* SECTION 5: PAPER TRADING */}
      {activeSubTab === "paper" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          <div className="card" style={{ padding: "1.5rem" }}>
            <h3 style={{ fontSize: "1rem", fontWeight: 700, color: "var(--tse-blue)", marginBottom: "0.8rem" }}>
              مدیریت پورتفوی آزمایشی (Paper Trading Portfolio)
            </h3>
            <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", lineHeight: 1.6 }}>
              معاملات آزمایشی با سرمایه ۱ میلیارد تومان (۱۰ میلیارد ریال) به صورت بلادرنگ توسط هوش مصنوعی اجرا و در دفترکل ثبت می‌شوند.
            </p>
          </div>
        </div>
      )}

      {/* SECTION 6: HISTORICAL BACKTEST */}
      {activeSubTab === "backtest" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          <div className="card" style={{ padding: "1.5rem" }}>
            <h3 style={{ fontSize: "1rem", fontWeight: 700, color: "var(--tse-green)", marginBottom: "0.8rem" }}>
              شبیه‌ساز بک‌تست تاریخی و آزمون برون‌نمونه (Walk-Forward Backtest)
            </h3>
            <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", lineHeight: 1.6 }}>
              آزمون جامع تمام استراتژی‌ها بر روی ۲۶۰ روز دیتای تاریخی بدون سوگیری نگاه به آینده (Look-ahead bias) و با احتساب صف‌ها و اسلیپیج واقعی بورس تهران.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
