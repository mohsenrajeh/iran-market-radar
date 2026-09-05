"use client";
import React, { useState, useEffect } from "react";
import {
  Sliders,
  Activity,
  ShieldCheck,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  ShieldAlert,
  Power,
  Database,
  Server,
  Radio,
  Layers,
  Sparkles,
  TrendingDown,
  AlertTriangle,
  Lock,
  FileText,
} from "lucide-react";

export const HealthSettingsView: React.FC = () => {
  const [healthData, setHealthData] = useState<any | null>(null);
  const [settingsData, setSettingsData] = useState<any | null>(null);
  const [providerCatalog, setProviderCatalog] = useState<any | null>(null);
  const [backfillLoading, setBackfillLoading] = useState(false);
  const [backfillMsg, setBackfillMsg] = useState<string | null>(null);

  // Kill-Switch State
  const [killSwitchActive, setKillSwitchActive] = useState<boolean>(false);
  const [killSwitchLoading, setKillSwitchLoading] = useState<boolean>(false);
  const [killSwitchFeedback, setKillSwitchFeedback] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [resHealth, resSettings, resPort, resProviders] = await Promise.all([
        fetch("/api/v1/data/health"),
        fetch("/api/v1/settings"),
        fetch("/api/v1/paper/portfolio"),
        fetch("/api/v1/data/providers"),
      ]);
      if (resHealth.ok) {
        const data = await resHealth.json();
        setHealthData(data);
      }
      if (resSettings.ok) setSettingsData(await resSettings.json());
      if (resPort.ok) {
        const portData = await resPort.json();
        setKillSwitchActive(portData.kill_switch_active || false);
      }
      if (resProviders.ok) setProviderCatalog(await resProviders.json());
    } catch (e) {
      console.error(e);
    }
  };

  const handleTriggerBackfill = async () => {
    setBackfillLoading(true);
    setBackfillMsg(null);
    try {
      const res = await fetch("/api/v1/data/backfill", { method: "POST" });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(typeof data.detail === "string" ? data.detail : "همگام‌سازی رسمی متوقف شد.");
      }
      setBackfillMsg(data.message || "همگام‌سازی و بازشماری رادار با موفقیت انجام شد.");
      await fetchData();
    } catch (e: any) {
      setBackfillMsg(e?.message || "خطا در اجرای همگام‌سازی.");
    } finally {
      setBackfillLoading(false);
    }
  };

  const handleToggleKillSwitch = async () => {
    const nextState = !killSwitchActive;
    setKillSwitchLoading(true);
    setKillSwitchFeedback(null);
    try {
      const res = await fetch("/api/v1/paper/kill-switch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ active: nextState }),
      });
      const data = await res.json();
      if (res.ok) {
        setKillSwitchActive(nextState);
        setKillSwitchFeedback(
          nextState
            ? "🚨 کلید قطع اضطراری فعال شد — کلیه معاملات جدید و چرخه‌های خودکار فوراً متوقف شدند."
            : "✅ کلید قطع اضطراری غیرفعال شد — سیستم به وضعیت عادی معامله‌گری خودکار بازگشت."
        );
        setTimeout(() => setKillSwitchFeedback(null), 6000);
      }
    } catch (e) {
      setKillSwitchFeedback("خطا در تغییر وضعیت کلید قطع اضطراری.");
    } finally {
      setKillSwitchLoading(false);
    }
  };

  const sources = healthData?.sources || [];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem", direction: "rtl" }}>
      {/* ── 0. Top Header & Governance Policy Metadata ─────────────────── */}
      <div className="card-panel">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.75rem" }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <Activity size={22} color="var(--tse-green)" />
              <h2 style={{ fontSize: "1.15rem", fontWeight: 800, color: "var(--text-primary)", margin: 0 }}>
                پایش سلامت داده‌ها، تله‌متری سرویس‌ها و تنظیمات خط‌مشی ریسک
              </h2>
            </div>
            <p style={{ fontSize: "0.82rem", color: "var(--text-secondary)", marginTop: "0.3rem", marginBottom: 0 }}>
              نظارت بر تاخیر زمانی (Latency)، نسبت کامل بودن داده‌ها، کلید قطع اضطراری و انطباق با خط‌مشی ریسک واحد نهادی (Single Source of Truth).
            </p>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
            <span style={{ fontSize: "0.74rem", backgroundColor: "rgba(56, 189, 248, 0.15)", color: "#38bdf8", padding: "4px 10px", borderRadius: "6px", fontWeight: 800, border: "1px solid rgba(56, 189, 248, 0.3)" }}>
              سند ریسک: {settingsData?.risk_parameters?.policy_version || "—"}
            </span>
            <span style={{ fontSize: "0.74rem", backgroundColor: "rgba(34, 197, 94, 0.15)", color: "#22c55e", padding: "4px 10px", borderRadius: "6px", fontWeight: 800, border: "1px solid rgba(34, 197, 94, 0.3)" }}>
              حالت اجرا: {settingsData?.trading_mode || "—"}
            </span>
          </div>
        </div>
      </div>

      <div className="card-panel">
        <div style={{ fontWeight: 800, fontSize: "1rem", color: "var(--text-primary)", marginBottom: "0.35rem" }}>
          منبع یگانه دریافت بازار
        </div>
        <p style={{ fontSize: "0.78rem", color: "var(--text-secondary)", marginTop: 0 }}>
          فقط JSON عمومی CDN رسمی TSETMC فعال است؛ WebGW، API لاگین‌دار و تجمیع‌کننده‌ها از مسیر به‌روزرسانی و معامله خارج شده‌اند.
        </p>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))", gap: "0.75rem" }}>
          {(providerCatalog?.sources || []).filter((src: any) =>
            src.key === "tsetmc_public_cdn"
          ).map((src: any) => (
            <div key={src.key} style={{ background: "var(--bg-surface)", border: "1px solid var(--border-subtle)", borderRadius: "8px", padding: "0.8rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: "0.5rem" }}>
                <strong>{src.provider_name}</strong>
                <span style={{ color: src.credential_configured ? "var(--tse-green)" : "var(--tse-amber)", fontSize: "0.72rem" }}>
                  بدون توکن و نام کاربری
                </span>
              </div>
              <div style={{
                color: "var(--text-muted)",
                fontSize: "0.72rem",
                marginTop: "0.35rem",
                direction: "ltr",
                textAlign: "left",
                lineHeight: 1.35,
                overflowWrap: "anywhere",
                wordBreak: "break-word",
                minHeight: "2.7em",
              }}>
                {src.status}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── 1. Interactive Emergency Kill-Switch Panel ───────────────── */}
      <div
        className="card-panel"
        style={{
          backgroundColor: killSwitchActive ? "rgba(239, 68, 68, 0.15)" : "var(--bg-surface)",
          border: `1px solid ${killSwitchActive ? "#ef4444" : "rgba(239, 68, 68, 0.35)"}`,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "1rem",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <div
            style={{
              width: "42px",
              height: "42px",
              borderRadius: "8px",
              backgroundColor: killSwitchActive ? "#ef4444" : "rgba(239, 68, 68, 0.2)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: killSwitchActive ? "#fff" : "#ef4444",
            }}
          >
            <ShieldAlert size={22} />
          </div>
          <div>
            <div style={{ fontWeight: 800, fontSize: "0.95rem", color: killSwitchActive ? "#fca5a5" : "#f8fafc" }}>
              کلید قطع اضطراری معامله‌گری و توقف سریع سفارشات (Emergency Kill Switch)
            </div>
            <div style={{ fontSize: "0.76rem", color: "var(--text-secondary)", marginTop: "2px" }}>
              وضعیت جاری:{" "}
              <strong style={{ color: killSwitchActive ? "#ef4444" : "var(--tse-green)" }}>
                {killSwitchActive ? "🚨 فعال (کلیه سفارشات جدید مسدود هستند)" : "🟢 مسلح و آماده (سیستم در حالت امن معامله می‌کند)"}
              </strong>
            </div>
          </div>
        </div>

        <button
          onClick={handleToggleKillSwitch}
          disabled={killSwitchLoading}
          style={{
            padding: "0.6rem 1.25rem",
            borderRadius: "6px",
            border: "none",
            backgroundColor: killSwitchActive ? "#22c55e" : "#ef4444",
            color: "#fff",
            fontWeight: 800,
            fontSize: "0.84rem",
            cursor: killSwitchLoading ? "not-allowed" : "pointer",
            display: "flex",
            alignItems: "center",
            gap: "0.4rem",
            fontFamily: "inherit",
            boxShadow: "0 4px 12px rgba(0,0,0,0.3)",
          }}
        >
          <Power size={16} />
          <span>
            {killSwitchLoading
              ? "در حال اعمال فرمان..."
              : killSwitchActive
              ? "غیرفعال‌سازی کلید اضطراری (ادامه معاملات)"
              : "فعال‌سازی قطع اضطراری (توقف فوری معاملات)"}
          </span>
        </button>
      </div>

      {killSwitchFeedback && (
        <div
          style={{
            padding: "0.75rem 1.25rem",
            borderRadius: "8px",
            backgroundColor: killSwitchActive ? "rgba(239, 68, 68, 0.2)" : "var(--tse-green-subtle)",
            color: killSwitchActive ? "#fca5a5" : "var(--tse-green)",
            border: `1px solid ${killSwitchActive ? "#ef4444" : "var(--tse-green)"}`,
            fontWeight: 700,
            fontSize: "0.84rem",
          }}
        >
          {killSwitchFeedback}
        </div>
      )}

      {/* ── 2. Data Ingestion Sources Telemetry ─────────────────────── */}
      <div className="card-panel">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem", flexWrap: "wrap", gap: "0.5rem" }}>
          <div style={{ fontWeight: 800, fontSize: "1rem", color: "var(--text-primary)" }}>
            وضعیت درگاه‌های داده ({sources.length.toLocaleString("fa-IR")} receipt اندازه‌گیری‌شده)
          </div>
          <button className="btn-primary" onClick={handleTriggerBackfill} disabled={backfillLoading}>
            <RefreshCw size={14} className={backfillLoading ? "animate-spin" : ""} />
            <span>{backfillLoading ? "در حال دریافت و اسکن..." : "همگام‌سازی دستی و محاسبه مجدد رادار"}</span>
          </button>
        </div>

        {backfillMsg && (
          <div style={{ padding: "0.6rem 0.85rem", backgroundColor: "var(--tse-green-subtle)", color: "var(--tse-green)", borderRadius: "var(--radius-sm)", fontSize: "0.82rem", marginBottom: "1rem" }}>
            {backfillMsg}
          </div>
        )}

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "1rem" }}>
          {sources.map((src: any, idx: number) => (
            <div data-testid="health-source-receipt" key={idx} style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-md)", padding: "1rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.6rem", gap: "0.5rem" }}>
                <span style={{ fontWeight: 800, fontSize: "0.88rem", color: "var(--text-primary)" }}>{src.source_name || src.name_fa}</span>
                <span style={{
                  backgroundColor: src.status === "HEALTHY"
                    ? "rgba(46, 160, 67, 0.2)"
                    : src.status === "DEGRADED"
                      ? "rgba(245, 158, 11, 0.18)"
                      : "rgba(239, 68, 68, 0.18)",
                  color: src.status === "HEALTHY"
                    ? "var(--tse-green)"
                    : src.status === "DEGRADED"
                      ? "var(--tse-amber)"
                      : "#f87171",
                  padding: "0.15rem 0.5rem",
                  borderRadius: "4px",
                  fontSize: "0.7rem",
                  fontWeight: 800,
                  whiteSpace: "nowrap",
                }}>
                  {src.status || "UNAVAILABLE"}
                </span>
              </div>

              <div style={{ fontSize: "0.72rem", color: "var(--text-muted)", marginBottom: "0.6rem" }}>
                حالت: {src.mode || "نامشخص"} | schema: {src.schema_version || "unverified"}
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: "0.35rem", fontSize: "0.78rem", color: "var(--text-secondary)", borderTop: "1px solid var(--border-subtle)", paddingTop: "0.5rem" }}>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span>آخرین موفقیت:</span>
                  <span className="tabular-num" style={{ color: "var(--text-primary)", fontWeight: 700 }}>{src.last_success || "—"}</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span>تعداد رکورد آخرین دریافت:</span>
                  <span className="tabular-num" style={{ color: "var(--text-primary)", fontWeight: 700 }}>{src.record_count ?? 0}</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span>آخرین خطا:</span>
                  <span className="tabular-num" style={{ color: src.error ? "var(--tse-amber)" : "var(--tse-green)", fontWeight: 700 }}>{src.error || "—"}</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span>کامل‌بودن یونیورس:</span>
                  <span className="tabular-num" style={{ color: "var(--tse-blue)", fontWeight: 700 }}>{src.metadata?.completeness_ratio != null ? `${(src.metadata.completeness_ratio * 100).toFixed(1)}٪` : "—"}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── 3. Central Risk Limits & Drawdown Ladder (Single Source of Truth) ── */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))", gap: "1rem" }}>
        {/* Standardized Risk Policy Limits */}
        <div className="card-panel">
          <div style={{ fontWeight: 800, fontSize: "0.95rem", marginBottom: "0.75rem", display: "flex", alignItems: "center", gap: "0.4rem" }}>
            <Sliders size={18} color="var(--tse-green)" />
            <span>حدود احتیاطی و مدیریت ریسک سبد ۱۰ میلیارد تومانی (Risk Policy)</span>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "0.55rem", fontSize: "0.82rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "0.4rem" }}>
              <span style={{ color: "var(--text-secondary)" }}>ریسک مجاز در هر معامله (Risk Per Trade):</span>
              <span className="tabular-num" style={{ fontWeight: 800, color: "var(--tse-green)" }}>{settingsData?.risk_parameters?.risk_per_trade_pct_nav ?? "—"}٪ کل NAV</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "0.4rem" }}>
              <span style={{ color: "var(--text-secondary)" }}>سقف تخصیص در هر تک‌سهم (Position Cap):</span>
              <span className="tabular-num" style={{ fontWeight: 700 }}>{settingsData?.risk_parameters?.max_position_pct_nav ?? "—"}٪ NAV</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "0.4rem" }}>
              <span style={{ color: "var(--text-secondary)" }}>سقف تمرکز در هر صنعت (Sector Cap):</span>
              <span className="tabular-num" style={{ fontWeight: 800, color: "#38bdf8" }}>{settingsData?.risk_parameters?.max_sector_pct_nav ?? "—"}٪ NAV</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "0.4rem" }}>
              <span style={{ color: "var(--text-secondary)" }}>حداقل نقدینگی صیانت‌شده (Cash Floor):</span>
              <span className="tabular-num" style={{ color: "var(--tse-blue)", fontWeight: 800 }}>{settingsData?.risk_policy?.regimes?.RISK_ON?.min_cash_reserve_pct ?? "—"}٪ NAV</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "0.4rem" }}>
              <span style={{ color: "var(--text-secondary)" }}>فعال‌سازی سر‌به‌سر (Trailing Stop):</span>
              <span className="tabular-num" style={{ color: "var(--tse-green)", fontWeight: 700 }}>در policy فعلی مقدار ثابت عمومی ثبت نشده است</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", paddingTop: "0.2rem" }}>
              <span style={{ color: "var(--text-secondary)" }}>آستانه فعال‌سازی قطع اضطراری (Kill Switch):</span>
              <span className="tabular-num" style={{ fontWeight: 900, color: "var(--tse-red)" }}>{settingsData?.risk_parameters?.max_drawdown_kill_switch_pct ?? "—"}٪ افت از سقف NAV</span>
            </div>
          </div>
        </div>

        {/* Drawdown Ladder & Daily Loss Circuit Breaker */}
        <div className="card-panel">
          <div style={{ fontWeight: 800, fontSize: "0.95rem", marginBottom: "0.75rem", display: "flex", alignItems: "center", gap: "0.4rem" }}>
            <TrendingDown size={18} color="var(--tse-amber)" />
            <span>نردبان افت ارزش سرمایه (Drawdown Ladder) و مدارشکن زیان روزانه</span>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "0.55rem", fontSize: "0.8rem" }}>
            {/* Drawdown Ladder steps */}
            <div style={{ backgroundColor: "#0b101b", padding: "0.5rem 0.75rem", borderRadius: "6px", border: "1px solid #1e293b" }}>
              <div style={{ fontWeight: 700, color: "#f8fafc", marginBottom: "3px" }}>نردبان کنترل افت سرمایه از سقف (Peak-to-Trough Drawdown):</div>
              <div style={{ display: "flex", flexDirection: "column", gap: "2px", fontSize: "0.74rem", color: "#cbd5e1" }}>
                <div>🟡 <strong>افت ۴.۰٪ (هشدار):</strong> کاهش ضریب ریسک هر معامله به ۷۵٪ مقدار پایه.</div>
                <div>🟠 <strong>افت ۶.۰٪ (احتیاطی):</strong> کاهش ضریب ریسک به ۵۰٪ و کاهش سقف دارایی درگیر به ۳۵٪.</div>
                <div>🔴 <strong>افت ۸.۰٪ (تدافعی):</strong> توقف کامل کلیه خریدهای جدید و هدف‌گذاری سقف دارایی کمتر از ۲۰٪.</div>
                <div>🚨 <strong>افت ۱۲.۰٪ (قطع اضطراری):</strong> فعال‌سازی فوری Kill Switch و بستن معاملات با نظم اولویت.</div>
              </div>
            </div>

            {/* Daily Circuit Breaker */}
            <div style={{ backgroundColor: "#0b101b", padding: "0.5rem 0.75rem", borderRadius: "6px", border: "1px solid #1e293b" }}>
              <div style={{ fontWeight: 700, color: "#f8fafc", marginBottom: "3px" }}>مدارشکن زیان روزانه (Daily Loss Circuit Breaker):</div>
              <div style={{ display: "flex", flexDirection: "column", gap: "2px", fontSize: "0.74rem", color: "#cbd5e1" }}>
                <div>• <strong>زیان روزانه ۱.۰٪:</strong> کاهش حجم معاملات جدید به نصف (Risk * 0.50).</div>
                <div>• <strong>زیان روزانه ۱.۵٪:</strong> توقف کامل کلیه سفارشات خرید در آن روز معاملاتی.</div>
                <div>• <strong>زیان روزانه ۲.۰٪:</strong> لغو کلیه سفارشات لیمیت معلق و انتقال به حالت Risk Reduction.</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ── 4. Effective Market Rules & Fees Schedule ──────────────────── */}
      <div className="card-panel">
        <div style={{ fontWeight: 800, fontSize: "0.95rem", marginBottom: "0.75rem", display: "flex", alignItems: "center", gap: "0.4rem" }}>
          <ShieldCheck size={18} color="var(--tse-blue)" />
          <span>جدول کارمزد، مالیات و ساختار هزینه‌های معاملاتی (مصوب سازمان بورس و اوراق بهادار)</span>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "1rem", fontSize: "0.82rem" }}>
          <div style={{ backgroundColor: "var(--bg-surface)", padding: "0.75rem 1rem", borderRadius: "6px", border: "1px solid var(--border-subtle)" }}>
            <span style={{ color: "var(--text-secondary)", display: "block", fontSize: "0.74rem" }}>کارمزد خرید سهام (TSE Buy):</span>
            <strong style={{ fontSize: "1.1rem", color: "#f8fafc", marginTop: "2px", display: "block" }} className="tabular-num">۰.۳۷۱۲٪</strong>
          </div>

          <div style={{ backgroundColor: "var(--bg-surface)", padding: "0.75rem 1rem", borderRadius: "6px", border: "1px solid var(--border-subtle)" }}>
            <span style={{ color: "var(--text-secondary)", display: "block", fontSize: "0.74rem" }}>کارمزد فروش سهام (TSE Sell):</span>
            <strong style={{ fontSize: "1.1rem", color: "#f8fafc", marginTop: "2px", display: "block" }} className="tabular-num">۰.۳۸۵۰٪</strong>
          </div>

          <div style={{ backgroundColor: "var(--bg-surface)", padding: "0.75rem 1rem", borderRadius: "6px", border: "1px solid var(--border-subtle)" }}>
            <span style={{ color: "var(--text-secondary)", display: "block", fontSize: "0.74rem" }}>مالیات مقطوع نقل و انتقال فروش:</span>
            <strong style={{ fontSize: "1.1rem", color: "#f8fafc", marginTop: "2px", display: "block" }} className="tabular-num">۰.۵۰۰۰٪</strong>
          </div>

          <div style={{ backgroundColor: "rgba(34, 197, 94, 0.12)", padding: "0.75rem 1rem", borderRadius: "6px", border: "1px solid rgba(34, 197, 94, 0.3)" }}>
            <span style={{ color: "var(--tse-green)", display: "block", fontSize: "0.74rem", fontWeight: 700 }}>مجموع هزینه چرخه کامل (Round-trip):</span>
            <strong style={{ fontSize: "1.15rem", color: "var(--tse-green)", marginTop: "2px", display: "block", fontWeight: 900 }} className="tabular-num">۱.۲۵۶۲٪ (دقیق)</strong>
          </div>
        </div>
      </div>
    </div>
  );
};
