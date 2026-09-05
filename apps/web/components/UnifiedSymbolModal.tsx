"use client";
import React, { useState, useEffect } from "react";
import {
  X,
  TrendingUp,
  TrendingDown,
  BarChart3,
  Scale,
  Activity,
  FileText,
  Brain,
  Target,
  ShieldCheck,
  ShoppingCart,
  CheckCircle2,
  AlertTriangle,
  ArrowUpRight,
  ArrowDownRight,
  Layers,
  Sparkles,
  Award,
  Clock,
  Coins,
  Check,
  Briefcase,
  LogOut,
  Sliders,
  Flame,
  CheckCheck,
  PlusCircle,
  Scissors,
  Newspaper,
  Tag,
  Gauge,
} from "lucide-react";
import { InteractiveStockChart } from "./InteractiveStockChart";
import PreTradeRiskModal from "./PreTradeRiskModal";
import {
  formatNumberFa,
  formatToman,
  formatRial,
  formatPercentFa,
  formatRFa,
  toPersianDigits,
} from "../lib/formatters";

interface UnifiedSymbolModalProps {
  symbol: string | null;
  onClose: () => void;
  onOrderPlaced?: () => void;
}

export const UnifiedSymbolModal: React.FC<UnifiedSymbolModalProps> = ({
  symbol,
  onClose,
  onOrderPlaced,
}) => {
  const [chartData, setChartData] = useState<any | null>(null);
  const [fundamentalData, setFundamentalData] = useState<any | null>(null);
  const [opportunityData, setOpportunityData] = useState<any | null>(null);
  const [codalFilings, setCodalFilings] = useState<any[]>([]);
  const [portfolioData, setPortfolioData] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [dataError, setDataError] = useState<string | null>(null);

  // Order & Management action state
  const [ordering, setOrdering] = useState(false);
  const [scalingIn, setScalingIn] = useState(false);
  const [trimming, setTrimming] = useState(false);
  const [closing, setClosing] = useState(false);
  const [isRiskModalOpen, setIsRiskModalOpen] = useState(false);
  const [orderFeedback, setOrderFeedback] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Close on ESC key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  useEffect(() => {
    if (!symbol) return;
    fetchAllSymbolData(symbol);
  }, [symbol]);

  const fetchAllSymbolData = async (sym: string) => {
    setLoading(true);
    setDataError(null);
    setChartData(null);
    setFundamentalData(null);
    setOpportunityData(null);
    setCodalFilings([]);
    setOrderFeedback(null);
    try {
      const [cRes, fRes, oRes, dRes, pRes] = await Promise.allSettled([
        fetch(`/api/v1/symbols/${encodeURIComponent(sym)}/chart?limit=50`),
        fetch(`/api/v1/fundamentals/summary/${encodeURIComponent(sym)}`),
        fetch(`/api/v1/opportunities?actionable_only=false`),
        fetch(`/api/v1/fundamentals/codal-feed?symbol=${encodeURIComponent(sym)}&limit=10`),
        fetch(`/api/v1/paper/portfolio`),
      ]);

      if (cRes.status === "fulfilled" && cRes.value.ok) {
        setChartData(await cRes.value.json());
      } else {
        const detail = cRes.status === "fulfilled" ? await cRes.value.text() : "ارتباط با API برقرار نشد";
        setDataError(`نمودار رسمی در دسترس نیست: ${detail}`);
      }
      if (fRes.status === "fulfilled" && fRes.value.ok) setFundamentalData(await fRes.value.json());
      if (dRes.status === "fulfilled" && dRes.value.ok) {
        const filingsData = await dRes.value.json();
        setCodalFilings(Array.isArray(filingsData) ? filingsData : []);
      }
      if (pRes.status === "fulfilled" && pRes.value.ok) setPortfolioData(await pRes.value.json());

      if (oRes.status === "fulfilled" && oRes.value.ok) {
        const opps = await oRes.value.json();
        const matched = opps.find((o: any) => o.symbol === sym);
        setOpportunityData(matched || null);
      }
    } catch (e) {
      console.error("Error fetching unified symbol data:", e);
    } finally {
      setLoading(false);
    }
  };

  if (!symbol) return null;

  if (loading || dataError || !Array.isArray(chartData?.bars) || chartData.bars.length === 0) {
    return (
      <div
        role="dialog"
        aria-modal="true"
        aria-label={`وضعیت داده نماد ${symbol}`}
        onClick={onClose}
        style={{ position: "fixed", inset: 0, zIndex: 9999, backgroundColor: "rgba(0,0,0,0.85)", display: "flex", alignItems: "center", justifyContent: "center", padding: "1rem" }}
      >
        <div onClick={(event) => event.stopPropagation()} className="card-panel" style={{ width: "min(560px, 94vw)", padding: "1.25rem", display: "flex", flexDirection: "column", gap: "0.9rem" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <strong>{symbol}</strong>
            <button onClick={onClose} className="btn-secondary"><X size={16} /></button>
          </div>
          {loading ? (
            <span style={{ color: "var(--text-secondary)" }}>در حال دریافت دادهٔ رسمی و بررسی provenance…</span>
          ) : (
            <div style={{ color: "var(--tse-amber)", lineHeight: 1.8 }}>
              {dataError || "هیچ کندل رسمی معتبر برای این نماد ثبت نشده است."}
              <div style={{ color: "var(--text-secondary)", fontSize: "0.8rem" }}>هیچ قیمت، امتیاز یا توصیهٔ جایگزین ساخته نمی‌شود.</div>
            </div>
          )}
        </div>
      </div>
    );
  }

  const ownedPosition = portfolioData?.positions?.find(
    (p: any) => p.symbol === symbol && p.is_open
  );

  const handlePlacePaperOrder = async () => {
    if (!opportunityData) return;
    setOrdering(true);
    setOrderFeedback(null);
    try {
      const res = await fetch("/api/v1/paper/orders/from-signal", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ signal_id: opportunityData.id }),
      });
      const data = await res.json();
      if (res.ok) {
        setOrderFeedback({ type: "success", text: data.message || "سفارش خرید با موفقیت در سبد دارایی ثبت شد." });
        if (onOrderPlaced) onOrderPlaced();
        fetchAllSymbolData(symbol);
      } else {
        setOrderFeedback({ type: "error", text: data.detail || "خطا در ثبت سفارش خرید." });
      }
    } catch (e) {
      setOrderFeedback({ type: "error", text: "عدم برقراری ارتباط با سرور معاملاتی." });
    } finally {
      setOrdering(false);
    }
  };

  // Price & Scoring derivations
  const bars = chartData?.bars || [];
  const latestBar = bars[bars.length - 1] || {};
  const curPrice = latestBar.close ?? null;
  const yesterdayPrice = latestBar.yesterday_price ?? latestBar.open ?? null;
  const returnPct = curPrice != null && yesterdayPrice != null && yesterdayPrice > 0 ? (((curPrice - yesterdayPrice) / yesterdayPrice) * 100) : null;
  const isPos = returnPct != null && returnPct >= 0;

  const isGoodStock = opportunityData?.actionable === true;
  const compositeScore = opportunityData?.opportunity_score ?? fundamentalData?.fundamental_score ?? null;

  // Analysis Power Percentages
  const techPowerPct = opportunityData?.confidence != null ? Math.round(opportunityData.confidence) : null;
  const tapePowerPct = opportunityData?.signal_strength != null ? Math.round(opportunityData.signal_strength) : null;
  const fundPowerPct = fundamentalData?.fundamental_score != null ? Math.round(fundamentalData.fundamental_score) : null;
  const probProfitPct = opportunityData?.p_profit != null ? Math.round(opportunityData.p_profit * 100) : null;

  // Dynamic tags
  const tags: Array<{ label: string; color: string; bg: string }> = (
    Array.isArray(opportunityData?.top_reasons_fa) ? opportunityData.top_reasons_fa : []
  ).slice(0, 4).map((label: string, index: number) => ({
    label,
    color: ["#c084fc", "#22c55e", "#38bdf8", "#f59e0b"][index],
    bg: ["rgba(192, 132, 252, 0.15)", "rgba(34, 197, 94, 0.15)", "rgba(56, 189, 248, 0.15)", "rgba(245, 158, 11, 0.15)"][index],
  }));

  // Price targets
  const entryPrice = opportunityData?.entry_zone?.low ?? ownedPosition?.average_entry_price;
  const target1 = opportunityData?.exit_plan?.targets?.[0] ?? ownedPosition?.target_price;
  const target2 = opportunityData?.exit_plan?.targets?.[1];
  const stopLoss = opportunityData?.invalidation?.price ?? ownedPosition?.stop_loss;
  const sellAdvicePrice = undefined;

  // Position financials
  const posValueTomans = ownedPosition && curPrice != null ? Math.round((ownedPosition.quantity * curPrice) / 10) : 0;
  const posPnlTomans = ownedPosition ? Math.round(ownedPosition.unrealized_pnl / 10) : 0;
  const posPnlPct = ownedPosition && curPrice != null && ownedPosition.average_entry_price > 0
    ? (((curPrice - ownedPosition.average_entry_price) / ownedPosition.average_entry_price) * 100)
    : 0;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={`تحلیل ۳۶۰ درجه نماد ${symbol}`}
      style={{
        position: "fixed",
        inset: 0,
        backgroundColor: "rgba(0, 0, 0, 0.85)",
        backdropFilter: "blur(8px)",
        zIndex: 9999,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "1rem",
      }}
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: "1320px",
          maxWidth: "97vw",
          maxHeight: "94vh",
          backgroundColor: "#0d131f",
          borderRadius: "16px",
          border: "1px solid #1e293b",
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
          boxShadow: "0 25px 70px rgba(0,0,0,0.9)",
        }}
      >
        {/* ── 1. Top Master Header ───────────────────────────────────────── */}
        <div
          style={{
            padding: "0.85rem 1.5rem",
            backgroundColor: "#131b2e",
            borderBottom: "1px solid #1e293b",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: "1rem",
          }}
        >
          {/* Symbol Info & Tags */}
          <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
            <div
              style={{
                width: "44px",
                height: "44px",
                borderRadius: "10px",
                backgroundColor: isGoodStock ? "rgba(34, 197, 94, 0.15)" : "rgba(239, 68, 68, 0.15)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: isGoodStock ? "#22c55e" : "#ef4444",
                fontWeight: 900,
                fontSize: "1.1rem",
                border: `1px solid ${isGoodStock ? "rgba(34, 197, 94, 0.3)" : "rgba(239, 68, 68, 0.3)"}`,
              }}
            >
              {isGoodStock ? <TrendingUp size={24} /> : <TrendingDown size={24} />}
            </div>

            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", flexWrap: "wrap" }}>
                <span style={{ fontSize: "1.35rem", fontWeight: 900, color: "#f8fafc" }}>
                  {symbol}
                </span>
                <span style={{ fontSize: "0.85rem", color: "#94a3b8" }}>
                  {chartData?.name_fa || fundamentalData?.name_fa || symbol}
                </span>

                {ownedPosition ? (
                  <span style={{ fontSize: "0.72rem", padding: "2px 8px", borderRadius: "10px", backgroundColor: "rgba(34, 197, 94, 0.2)", color: "#22c55e", fontWeight: 800 }}>
                    موجود در سبد دارایی ({formatNumberFa(ownedPosition.quantity)} سهم)
                  </span>
                ) : isGoodStock ? (
                  <span style={{ fontSize: "0.72rem", padding: "2px 8px", borderRadius: "10px", backgroundColor: "rgba(34, 197, 94, 0.2)", color: "#22c55e", fontWeight: 800 }}>
                    سیگنال کاغذی قابل اقدام (نمره {toPersianDigits(compositeScore)})
                  </span>
                ) : (
                  <span style={{ fontSize: "0.72rem", padding: "2px 8px", borderRadius: "10px", backgroundColor: "rgba(239, 68, 68, 0.2)", color: "#ef4444", fontWeight: 800 }}>
                    بدون سیگنال قابل معامله
                  </span>
                )}
              </div>

              {/* Tags Row */}
              <div style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap", marginTop: "4px" }}>
                {tags.map((t, idx) => (
                  <span
                    key={idx}
                    style={{
                      fontSize: "0.68rem",
                      padding: "1px 7px",
                      borderRadius: "4px",
                      backgroundColor: t.bg,
                      color: t.color,
                      fontWeight: 700,
                    }}
                  >
                    {t.label}
                  </span>
                ))}
              </div>
            </div>
          </div>

          {/* Current Market Price & Analysis Power & Close */}
          <div style={{ display: "flex", alignItems: "center", gap: "1.5rem" }}>
            {/* Analysis Power Percentages Strip */}
            <div style={{ display: "flex", gap: "0.75rem", backgroundColor: "#0b101b", padding: "0.4rem 0.85rem", borderRadius: "8px", border: "1px solid #1e293b", fontSize: "0.72rem" }}>
              <div>
                <span style={{ color: "#94a3b8" }}>قدرت تکنیکال: </span>
                <strong style={{ color: "var(--tse-blue)" }}>{formatPercentFa(techPowerPct, 0)}</strong>
              </div>
              <div style={{ borderRight: "1px solid #1e293b", paddingRight: "0.75rem" }}>
                <span style={{ color: "#94a3b8" }}>قدرت تابلو: </span>
                <strong style={{ color: "var(--tse-green)" }}>{formatPercentFa(tapePowerPct, 0)}</strong>
              </div>
              <div style={{ borderRight: "1px solid #1e293b", paddingRight: "0.75rem" }}>
                <span style={{ color: "#94a3b8" }}>قدرت کدال: </span>
                <strong style={{ color: "var(--tse-gold)" }}>{formatPercentFa(fundPowerPct, 0)}</strong>
              </div>
              <div style={{ borderRight: "1px solid #1e293b", paddingRight: "0.75rem" }}>
                <span style={{ color: "#94a3b8" }}>احتمال سود: </span>
                <strong style={{ color: "#f59e0b" }}>{formatPercentFa(probProfitPct, 0)}</strong>
              </div>
            </div>

            <div style={{ textAlign: "left" }}>
              <div style={{ fontSize: "1.3rem", fontWeight: 900, color: "#f8fafc" }}>
                {formatRial(curPrice)}
              </div>
              <div
                style={{
                  fontSize: "0.78rem",
                  fontWeight: 800,
                  color: returnPct == null ? "var(--text-muted)" : (isPos ? "var(--tse-green)" : "var(--tse-red)"),
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "flex-end",
                  gap: "2px",
                }}
              >
                {returnPct == null ? null : (isPos ? <ArrowUpRight size={13} /> : <ArrowDownRight size={13} />)}
                <span>{formatPercentFa(returnPct, 2)}</span>
              </div>
            </div>

            <button
              onClick={onClose}
              style={{
                width: "32px",
                height: "32px",
                borderRadius: "6px",
                border: "1px solid #334155",
                backgroundColor: "#1e293b",
                color: "#94a3b8",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <X size={16} />
            </button>
          </div>
        </div>

        {/* ── 2. Ownership & Money Management Bar (if owned) ──────── */}
        {ownedPosition && (
          <div
            style={{
              backgroundColor: "rgba(30, 41, 59, 0.95)",
              borderBottom: "1px solid #334155",
              padding: "0.75rem 1.5rem",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              flexWrap: "wrap",
              gap: "1rem",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "1.75rem", flexWrap: "wrap" }}>
              <div>
                <span style={{ fontSize: "0.72rem", color: "#94a3b8" }}>میانگین خرید:</span>
                <div style={{ fontWeight: 800, fontSize: "0.92rem", color: "#f8fafc" }}>
                  {formatRial(ownedPosition.average_entry_price)}
                </div>
              </div>

              <div>
                <span style={{ fontSize: "0.72rem", color: "#94a3b8" }}>سود شما تا این لحظه:</span>
                <div style={{ fontWeight: 900, fontSize: "1rem", color: posPnlPct >= 0 ? "var(--tse-green)" : "var(--tse-red)" }}>
                  {formatToman(posPnlTomans)} ({formatPercentFa(posPnlPct, 2)})
                </div>
              </div>

              <div>
                <span style={{ fontSize: "0.72rem", color: "#94a3b8" }}>ارزش درگیر (سقف ۱۰٪):</span>
                <div style={{ fontWeight: 800, fontSize: "0.92rem", color: "var(--tse-blue)" }}>
                  {formatToman(posValueTomans)}
                </div>
              </div>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", backgroundColor: "rgba(192, 132, 252, 0.15)", padding: "0.6rem 1rem", borderRadius: "8px", border: "1px solid rgba(192, 132, 252, 0.3)" }}>
                <Brain size={18} color="#c084fc" />
                <div>
                  <div style={{ fontSize: "0.82rem", fontWeight: 800, color: "#c084fc" }}>
                    مدیریت خودکار کاغذی تحت کنترل گیت‌ها
                  </div>
                  <div style={{ fontSize: "0.72rem", color: "#94a3b8", marginTop: "2px" }}>
                    وضعیت واقعی از scheduler، kill-switch و freshness داده تعیین می‌شود.
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ── 3. Main Unified 360° Scrollable Cockpit ── */}
        <div style={{ padding: "1.25rem", overflowY: "auto", flex: 1, display: "flex", flexDirection: "column", gap: "1.1rem" }}>
          {orderFeedback && (
            <div
              style={{
                padding: "0.65rem 1rem",
                borderRadius: "6px",
                fontSize: "0.82rem",
                fontWeight: 700,
                display: "flex",
                alignItems: "center",
                gap: "0.5rem",
                backgroundColor: orderFeedback.type === "success" ? "var(--tse-green-subtle)" : "var(--tse-red-subtle)",
                color: orderFeedback.type === "success" ? "var(--tse-green)" : "var(--tse-red)",
                border: `1px solid ${orderFeedback.type === "success" ? "var(--tse-green-border)" : "var(--tse-red-border)"}`,
              }}
            >
              {orderFeedback.type === "success" ? <Check size={16} /> : <AlertTriangle size={16} />}
              <span>{orderFeedback.text}</span>
            </div>
          )}

          {/* 1. Full-Width Interactive Stock Chart */}
          <InteractiveStockChart
            symbol={symbol}
            nameFa={chartData?.name_fa}
            bars={bars}
            plannedEntry={isGoodStock ? entryPrice : undefined}
            avgFillPrice={ownedPosition ? ownedPosition.average_entry_price : undefined}
            orderLimit={isGoodStock ? entryPrice : undefined}
            target1={isGoodStock ? target1 : undefined}
            target2={isGoodStock ? target2 : undefined}
            stopLoss={isGoodStock ? stopLoss : undefined}
            isGoodStock={isGoodStock}
            sellAdvicePrice={sellAdvicePrice}
            rsiValue={latestBar.rsi_14 != null ? Math.round(latestBar.rsi_14) : undefined}
            marketRegime={opportunityData?.regime || "unknown"}
          />

          {/* 2. Key Action Strip */}
          {(ownedPosition || opportunityData?.actionable === true) ? <div
            style={{
              backgroundColor: "#131b2e",
              padding: "0.85rem 1.25rem",
              borderRadius: "10px",
              border: "1px solid #1e293b",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              flexWrap: "wrap",
              gap: "1rem",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "1.5rem", flexWrap: "wrap" }}>
              <div>
                <span style={{ fontSize: "0.72rem", color: "#64748b" }}>نقطه ورود پیشنهادی:</span>
                <div style={{ fontWeight: 800, color: "var(--tse-blue)", fontSize: "0.95rem" }}>
                  {formatRial(entryPrice)}
                </div>
              </div>

              <div>
                <span style={{ fontSize: "0.72rem", color: "#64748b" }}>🎯 هدف اول ثبت‌شده:</span>
                <div style={{ fontWeight: 800, color: "var(--tse-green)", fontSize: "0.95rem" }}>
                  {formatRial(target1)}
                </div>
              </div>

              <div>
                <span style={{ fontSize: "0.72rem", color: "#64748b" }}>🏆 هدف دوم ثبت‌شده:</span>
                <div style={{ fontWeight: 800, color: "var(--tse-purple)", fontSize: "0.95rem" }}>
                  {formatRial(target2)}
                </div>
              </div>

              <div>
                <span style={{ fontSize: "0.72rem", color: "#64748b" }}>🛑 حد ضرر ثبت‌شده:</span>
                <div style={{ fontWeight: 800, color: "var(--tse-red)", fontSize: "0.95rem" }}>
                  {formatRial(stopLoss)}
                </div>
              </div>
            </div>

            {!ownedPosition && opportunityData?.actionable === true && (
              <div style={{ display: "flex", gap: "0.5rem" }}>
                <button
                  onClick={() => setIsRiskModalOpen(true)}
                  className="btn-secondary"
                  style={{
                    padding: "0.6rem 1.15rem",
                    fontWeight: 700,
                    fontSize: "0.85rem",
                  }}
                >
                  <ShieldCheck size={16} />
                  <span>تیکت مدیریت ریسک و ورود پله‌ای</span>
                </button>
                <button
                  onClick={handlePlacePaperOrder}
                  disabled={ordering}
                  className="btn-primary"
                  style={{
                    padding: "0.6rem 1.25rem",
                    fontWeight: 700,
                    fontSize: "0.85rem",
                    opacity: ordering ? 0.6 : 1,
                  }}
                >
                  <ShoppingCart size={15} />
                  <span>{ordering ? "در حال ثبت..." : "ورود سریع آزمایشی"}</span>
                </button>
              </div>
            )}
          </div> : (
            <div style={{
              backgroundColor: "rgba(148, 163, 184, 0.08)",
              padding: "0.85rem 1.25rem",
              borderRadius: "10px",
              border: "1px solid #334155",
              color: "#cbd5e1",
              fontSize: "0.85rem",
              fontWeight: 700,
            }}>
              این تحلیل فقط پژوهشی است؛ تا عبور از کالیبراسیون، داده بنیادی و گیت‌های ریسک هیچ نقطه ورود، هدف یا حد ضرر اجرایی صادر نشده است.
            </div>
          )}

          {/* Render Pre-Trade Risk Modal */}
          {isRiskModalOpen && (
            <PreTradeRiskModal
              isOpen={isRiskModalOpen}
              onClose={() => setIsRiskModalOpen(false)}
              signalId={opportunityData?.id || null}
              symbol={symbol || ""}
              onOrderSuccess={(msg) => {
                setOrderFeedback({ type: "success", text: msg });
                if (onOrderPlaced) onOrderPlaced();
              }}
            />
          )}

          {/* 3. Side-by-Side Technical vs Fundamental Analysis */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
            {/* Technical Pillar */}
            <div
              style={{
                backgroundColor: "#131b2e",
                padding: "1rem 1.15rem",
                borderRadius: "10px",
                border: "1px solid #1e293b",
                display: "flex",
                flexDirection: "column",
                gap: "0.65rem",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
                  <BarChart3 size={17} color="var(--tse-blue)" />
                  <h4 style={{ margin: 0, fontWeight: 800, fontSize: "0.9rem", color: "#f8fafc" }}>
                    تحلیل تکنیکال و جریان سفارشات (قدرت {formatPercentFa(techPowerPct, 0)})
                  </h4>
                </div>
                <span style={{ fontSize: "0.78rem", fontWeight: 800, color: "var(--tse-blue)", backgroundColor: "var(--tse-blue-subtle)", padding: "2px 7px", borderRadius: "4px" }}>
                  {opportunityData?.actionable === true ? "سیگنال معتبر" : "غیرقابل معامله"}
                </span>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.75rem", marginBottom: "2px" }}>
                    <span style={{ color: "#94a3b8" }}>قدرت خریدار حقیقی (پول هوشمند):</span>
                    <strong style={{ color: "var(--tse-green)" }}>{latestBar.real_buy_power_ratio != null ? `${toPersianDigits(latestBar.real_buy_power_ratio.toFixed(2))} برابر فروشنده` : "—"}</strong>
                  </div>
                  <div style={{ height: "5px", backgroundColor: "#0b101b", borderRadius: "3px", overflow: "hidden" }}>
                    <div style={{ width: `${tapePowerPct}%`, height: "100%", backgroundColor: "var(--tse-green)" }} />
                  </div>
                </div>

                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.75rem", marginBottom: "2px" }}>
                    <span style={{ color: "#94a3b8" }}>موقعیت نسبت به میانگین‌های EMA:</span>
                    <strong style={{ color: "var(--tse-blue)" }}>{chartData?.technical_analysis?.trend_badge || "—"}</strong>
                  </div>
                  <div style={{ height: "5px", backgroundColor: "#0b101b", borderRadius: "3px", overflow: "hidden" }}>
                    <div style={{ width: `${techPowerPct ?? 0}%`, height: "100%", backgroundColor: "var(--tse-blue)" }} />
                  </div>
                </div>

                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.75rem", marginBottom: "2px" }}>
                    <span style={{ color: "#94a3b8" }}>نوسان‌نما و قدرت RSI:</span>
                    <strong style={{ color: "var(--tse-gold)" }}>{latestBar.rsi_14 != null ? toPersianDigits(Math.round(latestBar.rsi_14)) : "—"}</strong>
                  </div>
                  <div style={{ height: "5px", backgroundColor: "#0b101b", borderRadius: "3px", overflow: "hidden" }}>
                    <div style={{ width: `${latestBar.rsi_14 ?? 0}%`, height: "100%", backgroundColor: "var(--tse-gold)" }} />
                  </div>
                </div>
              </div>
            </div>

            {/* Fundamental Pillar */}
            <div
              style={{
                backgroundColor: "#131b2e",
                padding: "1rem 1.15rem",
                borderRadius: "10px",
                border: "1px solid #1e293b",
                display: "flex",
                flexDirection: "column",
                gap: "0.65rem",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
                  <Scale size={17} color="var(--tse-green)" />
                  <h4 style={{ margin: 0, fontWeight: 800, fontSize: "0.9rem", color: "#f8fafc" }}>
                    تحلیل بنیادی و ارزش‌گذاری (قدرت {formatPercentFa(fundPowerPct, 0)})
                  </h4>
                </div>
                <span style={{ fontSize: "0.78rem", fontWeight: 800, color: "var(--tse-green)", backgroundColor: "var(--tse-green-subtle)", padding: "2px 7px", borderRadius: "4px" }}>
                  {fundamentalData ? fundamentalData.valuation_status_fa : "بدون snapshot معتبر"}
                </span>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.75rem", marginBottom: "2px" }}>
                    <span style={{ color: "#94a3b8" }}>رشد سالانه فروش در کدال:</span>
                    <strong style={{ color: "var(--tse-green)" }}>{formatPercentFa(fundamentalData?.monthly_sales_growth_yoy, 0)}</strong>
                  </div>
                  <div style={{ height: "5px", backgroundColor: "#0b101b", borderRadius: "3px", overflow: "hidden" }}>
                    <div style={{ width: `${fundamentalData?.monthly_sales_growth_yoy != null ? Math.max(0, Math.min(100, fundamentalData.monthly_sales_growth_yoy)) : 0}%`, height: "100%", backgroundColor: "var(--tse-green)" }} />
                  </div>
                </div>

                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.75rem", marginBottom: "2px" }}>
                    <span style={{ color: "#94a3b8" }}>نسبت P/E سهم به صنعت:</span>
                    <strong style={{ color: "var(--tse-blue)" }}>{fundamentalData?.p_e_ratio != null ? `${toPersianDigits(fundamentalData.p_e_ratio.toFixed(1))} (گروه: ${toPersianDigits(fundamentalData.sector_p_e?.toFixed?.(1))})` : "—"}</strong>
                  </div>
                  <div style={{ height: "5px", backgroundColor: "#0b101b", borderRadius: "3px", overflow: "hidden" }}>
                    <div style={{ width: `${fundPowerPct ?? 0}%`, height: "100%", backgroundColor: "var(--tse-blue)" }} />
                  </div>
                </div>

                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.75rem", marginBottom: "2px" }}>
                    <span style={{ color: "#94a3b8" }}>سلامت ترازنامه (امتیاز پیوتروسکی):</span>
                    <strong style={{ color: "var(--tse-green)" }}>{fundamentalData?.piotroski_f_score != null ? `${toPersianDigits(fundamentalData.piotroski_f_score)} از ۹` : "—"}</strong>
                  </div>
                  <div style={{ height: "5px", backgroundColor: "#0b101b", borderRadius: "3px", overflow: "hidden" }}>
                    <div style={{ width: `${fundamentalData?.piotroski_f_score != null ? (fundamentalData.piotroski_f_score / 9) * 100 : 0}%`, height: "100%", backgroundColor: "var(--tse-green)" }} />
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* ── 4. INTEGRATED CODAL FEED ── */}
          <div
            style={{
              backgroundColor: "#131b2e",
              borderRadius: "10px",
              border: "1px solid rgba(192, 132, 252, 0.3)",
              padding: "1.1rem 1.25rem",
              display: "flex",
              flexDirection: "column",
              gap: "0.75rem",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.45rem" }}>
                <Newspaper size={18} color="#c084fc" />
                <h4 style={{ margin: 0, fontSize: "0.95rem", fontWeight: 800, color: "#f8fafc" }}>
                  اطلاعیه‌ها، اخبار و افشاهای رسمی کدال ({symbol})
                </h4>
              </div>
              <span style={{ fontSize: "0.72rem", color: "#c084fc", backgroundColor: "rgba(192, 132, 252, 0.15)", padding: "2px 8px", borderRadius: "4px", fontWeight: 700 }}>
                {toPersianDigits(codalFilings.length)} اطلاعیه دارای provenance
              </span>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "0.55rem" }}>
              {(!codalFilings || !Array.isArray(codalFilings) || codalFilings.length === 0) ? (
                <div style={{ backgroundColor: "#0b101b", padding: "0.75rem 1rem", borderRadius: "6px", fontSize: "0.78rem", color: "#94a3b8" }}>
                  هیچ اطلاعیهٔ کدال دارای receipt معتبر برای این نماد ثبت نشده است.
                </div>
              ) : (
                (Array.isArray(codalFilings) ? codalFilings : []).slice(0, 3).map((filing: any) => (
                  <div
                    key={filing.id}
                    style={{
                      backgroundColor: "#0b101b",
                      padding: "0.75rem 1rem",
                      borderRadius: "6px",
                      border: "1px solid #1e293b",
                      display: "flex",
                      flexDirection: "column",
                      gap: "0.3rem",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span style={{ fontWeight: 800, fontSize: "0.82rem", color: "#f8fafc" }}>
                        {filing.title}
                      </span>
                      <span
                        style={{
                          fontSize: "0.7rem",
                          fontWeight: 700,
                          padding: "2px 7px",
                          borderRadius: "4px",
                          backgroundColor: filing.sentiment === "positive" ? "rgba(34, 197, 94, 0.15)" : "rgba(56, 189, 248, 0.15)",
                          color: filing.sentiment === "positive" ? "#22c55e" : "#38bdf8",
                        }}
                      >
                        {filing.sentiment_fa || "نامشخص"} (اثر: {toPersianDigits(filing.impact_score)}/۱۰)
                      </span>
                    </div>
                    <p style={{ margin: 0, fontSize: "0.75rem", color: "#94a3b8", lineHeight: 1.45 }}>
                      {filing.summary_fa || "خلاصهٔ تحلیلی ثبت نشده است."}
                    </p>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* 5. 4 AI Plain-Language Reasoning Cards */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "0.85rem" }}>
            <div style={{ backgroundColor: "#131b2e", padding: "0.85rem 1rem", borderRadius: "8px", border: "1px solid #1e293b" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.4rem", color: "var(--tse-green)", fontWeight: 800, fontSize: "0.82rem" }}>
                <Flame size={15} />
                <span>۱. وضعیت پول هوشمند و تابلو</span>
              </div>
              <p style={{ margin: "0.35rem 0 0", fontSize: "0.76rem", color: "#94a3b8", lineHeight: 1.45 }}>
                {latestBar.real_buy_power_ratio != null
                  ? `نسبت قدرت خریدار حقیقی ثبت‌شده ${toPersianDigits(latestBar.real_buy_power_ratio.toFixed(2))} است.`
                  : "دادهٔ معتبر حقیقی/حقوقی برای این کندل موجود نیست."}
              </p>
            </div>

            <div style={{ backgroundColor: "#131b2e", padding: "0.85rem 1rem", borderRadius: "8px", border: "1px solid #1e293b" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.4rem", color: "var(--tse-blue)", fontWeight: 800, fontSize: "0.82rem" }}>
                <FileText size={15} />
                <span>۲. صورت‌های مالی و کدال</span>
              </div>
              <p style={{ margin: "0.35rem 0 0", fontSize: "0.76rem", color: "#94a3b8", lineHeight: 1.45 }}>
                {fundamentalData?.monthly_sales_growth_yoy != null
                  ? `تغییر سالانهٔ فروش ماهانه ${formatPercentFa(fundamentalData.monthly_sales_growth_yoy, 0)} ثبت شده است.`
                  : "snapshot بنیادی معتبر در دسترس نیست."}
              </p>
            </div>

            <div style={{ backgroundColor: "#131b2e", padding: "0.85rem 1rem", borderRadius: "8px", border: "1px solid #1e293b" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.4rem", color: "var(--tse-gold)", fontWeight: 800, fontSize: "0.82rem" }}>
                <BarChart3 size={15} />
                <span>۳. چارت و میانگین متحرک</span>
              </div>
              <p style={{ margin: "0.35rem 0 0", fontSize: "0.76rem", color: "#94a3b8", lineHeight: 1.45 }}>
                {chartData?.technical_analysis?.trend_badge || "روند تکنیکال با دادهٔ موجود قابل ارزیابی نیست."}
              </p>
            </div>

            <div style={{ backgroundColor: "#131b2e", padding: "0.85rem 1rem", borderRadius: "8px", border: "1px solid #1e293b" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.4rem", color: "var(--tse-purple)", fontWeight: 800, fontSize: "0.82rem" }}>
                <Scale size={15} />
                <span>۴. ارزندگی نسبت به صنعت</span>
              </div>
              <p style={{ margin: "0.35rem 0 0", fontSize: "0.76rem", color: "#94a3b8", lineHeight: 1.45 }}>
                {fundamentalData?.p_e_ratio != null
                  ? `P/E ثبت‌شده ${toPersianDigits(fundamentalData.p_e_ratio.toFixed(1))} و P/E گروه ${toPersianDigits(fundamentalData.sector_p_e?.toFixed?.(1))} است؛ نتیجهٔ ارزندگی در snapshot: ${fundamentalData.valuation_status_fa || "نامشخص"}.`
                  : "نسبت‌های ارزش‌گذاری معتبر در دسترس نیست."}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
