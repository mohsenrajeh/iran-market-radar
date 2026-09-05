"use client";
import React, { useState, useEffect, useCallback } from "react";
import {
  Briefcase,
  AlertOctagon,
  TrendingUp,
  TrendingDown,
  RefreshCw,
  Play,
  Clock,
  Target,
  ShieldAlert,
  ShieldCheck,
  Brain,
  Activity,
  Layers,
  Zap,
  BarChart3,
  CheckCircle2,
  XCircle,
  Sparkles,
  Award,
  HelpCircle,
  X,
  ArrowUpRight,
  ArrowDownRight,
  Scale,
  LogOut,
  Maximize2,
  DollarSign,
  Eye,
  Check,
} from "lucide-react";
import { getStrategyFa, getStrategyShortFa, getIndicatorFa, getRegimeFa, getExitReasonFa } from "./translations";
import { formatDecimalFa, formatNumberFa, formatPercentFa, formatRatioFa, formatToman, toPersianDigits } from "../lib/formatters";

interface PositionItem {
  id: string;
  symbol: string;
  quantity: number;
  average_entry_price: number;
  current_price: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  stop_loss: number | null;
  target_price: number | null;
  total_invested_rials: number;
  total_invested_tomans: number;
  risk_pct: number | null;
  risk_reward_ratio: number | string | null;
  expected_days_to_target: number | null;
  days_open: number;
  market_regime: string;
  market_regime_fa: string;
  decision_method: string | null;
  entry_reason_fa: string | null;
  distance_to_target_pct: number;
  distance_to_stop_pct: number;
  client_power_ratio: number | null;
  risk_flags_fa: string[];
  opened_at: string;
  is_open: boolean;
}

interface PortfolioData {
  id: string;
  name: string;
  campaign_id: string | null;
  campaign_status: string | null;
  campaign_started_at: string | null;
  campaign_ends_at: string | null;
  initial_cash: number;
  cash: number;
  total_equity: number;
  realized_pnl: number;
  unrealized_pnl: number;
  open_positions_count: number;
  kill_switch_active: boolean;
  positions: PositionItem[];
}

interface TradeLogItem {
  id: string;
  symbol: string;
  side: string;
  entry_price: number;
  exit_price: number | null;
  quantity: number;
  total_invested_rials: number;
  total_invested_tomans: number;
  entry_at: string;
  exit_at: string | null;
  holding_hours: number;
  holding_days: number;
  expected_days_to_target: number | null;
  market_regime: string;
  market_regime_fa: string;
  gross_pnl: number;
  net_pnl: number;
  return_pct: number;
  risk_pct: number | null;
  risk_reward_ratio: number | string | null;
  decision_method: string | null;
  exit_reason: string;
  reason_fa: string;
  lesson_fa: string;
  is_closed: boolean;
  strategy_votes_at_entry: { strategy: string; vote: number; reason_fa: string }[];
  indicator_scores: Record<string, number>;
}

interface IndicatorPerfItem {
  indicator_name: string;
  display_name_fa: string;
  total_signals: number;
  profitable_signals: number;
  loss_signals: number;
  precision: number;
  avg_return_when_bullish: number;
  avg_return_when_bearish: number | null;
  cumulative_pnl: number;
}

interface PortfolioHistoryItem {
  snapshot_at: string;
  cash: number;
  positions_value: number;
  total_equity: number;
  open_positions_count: number;
  realized_pnl: number;
  unrealized_pnl: number;
  drawdown_pct: number;
}

interface AutoTradingStatus {
  is_running: boolean;
  total_cycles: number;
  total_trades: number;
  last_run_at: string | null;
  last_error: string | null;
}

export const PaperTradingView: React.FC = () => {
  const [portfolio, setPortfolio] = useState<PortfolioData | null>(null);
  const [history, setHistory] = useState<PortfolioHistoryItem[]>([]);
  const [trades, setTrades] = useState<TradeLogItem[]>([]);
  const [attribution, setAttribution] = useState<IndicatorPerfItem[]>([]);
  const [status, setStatus] = useState<AutoTradingStatus | null>(null);
  const [fillCount, setFillCount] = useState(0);
  const [fillLedgerLoaded, setFillLedgerLoaded] = useState(false);
  const [riskPolicy, setRiskPolicy] = useState<any | null>(null);
  const [dataError, setDataError] = useState<string | null>(null);

  const [activeSubTab, setActiveSubTab] = useState<"positions" | "strategies" | "equity" | "trades" | "indicators">("positions");
  const [opportunities, setOpportunities] = useState<any[]>([]);
  const [selectedTrade, setSelectedTrade] = useState<TradeLogItem | null>(null);
  const [selectedPosition, setSelectedPosition] = useState<PositionItem | null>(null);
  const [positionDetail, setPositionDetail] = useState<any | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [closingPositionId, setClosingPositionId] = useState<string | null>(null);
  const [closeSuccessMsg, setCloseSuccessMsg] = useState<string | null>(null);

  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);
  const [cycleMessage, setCycleMessage] = useState<string | null>(null);
  const [killSwitchLoading, setKillSwitchLoading] = useState(false);

  const fetchAllData = useCallback(async () => {
    setLoading(true);
    try {
      const [pRes, hRes, tRes, aRes, sRes, oRes, fRes, rRes] = await Promise.allSettled([
        fetch("/api/v1/paper/portfolio"),
        fetch("/api/v1/auto-trading/portfolio-history?limit=100"),
        fetch("/api/v1/auto-trading/trade-log?limit=100"),
        fetch("/api/v1/auto-trading/attribution"),
        fetch("/api/v1/auto-trading/status"),
        fetch("/api/v1/opportunities?actionable_only=true"),
        fetch("/api/v1/paper/ledger/fills"),
        fetch("/api/v1/paper/risk-policy"),
      ]);

      const portfolioOk = pRes.status === "fulfilled" && pRes.value.ok;
      const fillsOk = fRes.status === "fulfilled" && fRes.value.ok;
      if (!portfolioOk || !fillsOk) {
        const unauthorized = (
          (pRes.status === "fulfilled" && pRes.value.status === 401)
          || (fRes.status === "fulfilled" && fRes.value.status === 401)
        );
        setPortfolio(null);
        setFillLedgerLoaded(false);
        setDataError(
          unauthorized
            ? "نشست مالک معتبر نیست؛ اعداد کمپین تا ورود دوباره نمایش داده نمی‌شوند."
            : "پاسخ پورتفو یا دفترکل اجرا تأیید نشد؛ برای جلوگیری از نمایش عدد ساختگی، وضعیت مالی پنهان ماند."
        );
        if (unauthorized && typeof window !== "undefined") {
          window.dispatchEvent(new Event("radar:auth-required"));
        }
        return;
      }
      setPortfolio(await pRes.value.json());
      if (hRes.status === "fulfilled" && hRes.value.ok) setHistory(await hRes.value.json());
      if (tRes.status === "fulfilled" && tRes.value.ok) setTrades(await tRes.value.json());
      if (aRes.status === "fulfilled" && aRes.value.ok) setAttribution(await aRes.value.json());
      if (sRes.status === "fulfilled" && sRes.value.ok) setStatus(await sRes.value.json());
      if (oRes.status === "fulfilled" && oRes.value.ok) setOpportunities(await oRes.value.json());
      const fillPayload = await fRes.value.json();
      setFillCount(fillPayload.fill_count || 0);
      setFillLedgerLoaded(true);
      setDataError(null);
      if (rRes.status === "fulfilled" && rRes.value.ok) setRiskPolicy(await rRes.value.json());
    } catch (e) {
      console.error("PaperTradingView fetch error:", e);
      setPortfolio(null);
      setFillLedgerLoaded(false);
      setDataError("ارتباط با پورتفو یا دفترکل برقرار نشد؛ هیچ عدد نمونه‌ای نمایش داده نمی‌شود.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAllData();
    const timer = setInterval(fetchAllData, 20000);
    return () => clearInterval(timer);
  }, [fetchAllData]);

  // When a position is selected, fetch its deep detail
  useEffect(() => {
    if (!selectedPosition) {
      setPositionDetail(null);
      return;
    }

    const fetchDetail = async () => {
      setDetailLoading(true);
      try {
        const res = await fetch(`/api/v1/paper/position-detail/${selectedPosition.id}`);
        if (res.ok) {
          setPositionDetail(await res.json());
        }
      } catch (e) {
        console.error("Failed to load position detail:", e);
      } finally {
        setDetailLoading(false);
      }
    };

    fetchDetail();
  }, [selectedPosition]);

  const triggerCycleNow = async () => {
    if (portfolio?.kill_switch_active || !status?.is_running) {
      setCycleMessage(
        portfolio?.kill_switch_active
          ? "کلید قطع اضطراری فعال است؛ چرخه معاملاتی و خرید جدید مسدود است."
          : "موتور معاملاتی غیرفعال است؛ فقط بروزرسانی تحلیلی داشبورد قابل استفاده است."
      );
      return;
    }
    setTriggering(true);
    setCycleMessage(null);
    try {
      const res = await fetch("/api/v1/auto-trading/trigger", { method: "POST" });
      if (res.ok) {
        await fetchAllData();
        setCycleMessage("چرخه بررسی شد؛ نتیجه از دفترکل تازه خوانده شد.");
      } else {
        const payload = await res.json().catch(() => null);
        const detail = payload?.detail;
        setCycleMessage(
          detail?.reason || detail?.message || "چرخه متوقف شد؛ داده رسمی تازه یا مجوز ریسک موجود نیست."
        );
      }
    } catch (e) {
      console.error(e);
      setCycleMessage("ارتباط با چرخه تحلیلی برقرار نشد؛ هیچ معامله‌ای ثبت نشد.");
    } finally {
      setTriggering(false);
    }
  };

  const toggleKillSwitch = async () => {
    if (!portfolio) return;
    setKillSwitchLoading(true);
    try {
      const nextState = !portfolio.kill_switch_active;
      const res = await fetch("/api/v1/paper/kill-switch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ active: nextState }),
      });
      if (res.ok) {
        await fetchAllData();
      }
    } catch (e) {
      console.error(e);
    } finally {
      setKillSwitchLoading(false);
    }
  };

  const handleManualClosePosition = async (posId: string) => {
    setClosingPositionId(posId);
    try {
      const res = await fetch(`/api/v1/paper/close-position/${posId}`, { method: "POST" });
      if (res.ok) {
        const data = await res.json();
        setCloseSuccessMsg(data.message);
        setTimeout(() => {
          setCloseSuccessMsg(null);
          setSelectedPosition(null);
        }, 1800);
        await fetchAllData();
      }
    } catch (e) {
      console.error("Error closing position:", e);
    } finally {
      setClosingPositionId(null);
    }
  };

  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null);

  const handleScaleInPosition = async (posId: string) => {
    setActionLoadingId(posId);
    try {
      const res = await fetch(`/api/v1/paper/scale-in/${posId}`, { method: "POST" });
      const data = await res.json();
      if (res.ok) {
        setCloseSuccessMsg(data.message);
        setTimeout(() => setCloseSuccessMsg(null), 2500);
        await fetchAllData();
      } else {
        alert(data.detail || "امکان افزایش پله‌ای وجود ندارد.");
      }
    } catch (e) {
      console.error("Scale in error:", e);
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleTrimPosition = async (posId: string) => {
    setActionLoadingId(posId);
    try {
      const res = await fetch(`/api/v1/paper/trim/${posId}?ratio=0.50`, { method: "POST" });
      const data = await res.json();
      if (res.ok) {
        setCloseSuccessMsg(data.message);
        setTimeout(() => setCloseSuccessMsg(null), 2500);
        await fetchAllData();
      } else {
        alert(data.detail || "امکان کاهش حجم وجود ندارد.");
      }
    } catch (e) {
      console.error("Trim error:", e);
    } finally {
      setActionLoadingId(null);
    }
  };

  const parseRR = (rr: unknown): number | null => {
    if (typeof rr === "number" && Number.isFinite(rr)) return rr;
    if (typeof rr === "string") {
      const parts = rr.split(":");
      const parsed = Number.parseFloat(parts.length > 1 ? parts[1] : rr);
      return Number.isFinite(parsed) ? parsed : null;
    }
    return null;
  };

  if (loading && !portfolio) {
    return (
      <div className="card-panel" role="status" style={{ padding: "2rem", textAlign: "center", color: "var(--text-secondary)" }}>
        در حال تأیید پورتفو و دفترکل اجرای کمپین…
      </div>
    );
  }

  if (dataError || !portfolio || !fillLedgerLoaded) {
    return (
      <div className="card-panel" role="alert" style={{ padding: "2rem", textAlign: "center", borderColor: "var(--tse-red-border)" }}>
        <ShieldAlert size={34} color="var(--tse-red)" style={{ margin: "0 auto 0.8rem" }} />
        <h2 style={{ margin: 0, color: "var(--text-primary)", fontSize: "1.05rem" }}>وضعیت مالی کمپین تأیید نشده است</h2>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.88rem", margin: "0.6rem auto 1rem", maxWidth: 620 }}>
          {dataError || "پورتفو یا دفترکل اجرا در دسترس نیست؛ هیچ عددی به‌صورت پیش‌فرض ساخته نمی‌شود."}
        </p>
        <a href="/" style={{ color: "var(--tse-blue)", fontWeight: 800 }}>بازگشت به داشبورد و ورود مالک</a>
      </div>
    );
  }

  const initialCapitalRials = portfolio.initial_cash;
  const totalEquityRials = portfolio.total_equity;
  const totalEquityTomans = totalEquityRials / 10;
  const totalReturnPct = ((totalEquityRials - initialCapitalRials) / initialCapitalRials) * 100;
  const positions = portfolio?.positions || [];
  const openPositionsCount = positions.filter((p) => p.is_open).length;

  const closedTrades = trades.filter((t) => t.is_closed);
  const winTrades = closedTrades.filter((t) => t.net_pnl > 0);
  const lossTrades = closedTrades.filter((t) => t.net_pnl <= 0);
  const winRatePct = closedTrades.length > 0 ? (winTrades.length / closedTrades.length) * 100 : null;

  const totalInvestedInPositionsRials = positions
    .filter((p) => p.is_open)
    .reduce((acc, p) => acc + (p.current_price * p.quantity), 0);
  const totalInvestedInPositionsTomans = totalInvestedInPositionsRials / 10;
  const portfolioExposurePct = totalEquityRials > 0 ? (totalInvestedInPositionsRials / totalEquityRials) * 100 : 0;
  const rrValues = positions.map((p) => parseRR(p.risk_reward_ratio)).filter((value): value is number => value != null);
  const avgRRRatio = rrValues.length > 0
    ? rrValues.reduce((acc, value) => acc + value, 0) / rrValues.length
    : null;
  const cycleBlocked = Boolean(portfolio?.kill_switch_active || !status?.is_running);
  const equityValues = [initialCapitalRials, ...history.map((item) => item.total_equity)];
  const observedMinEquity = Math.min(...equityValues);
  const observedMaxEquity = Math.max(...equityValues);
  const equityPadding = Math.max(
    initialCapitalRials * 0.01,
    (observedMaxEquity - observedMinEquity) * 0.1,
  );
  const equityChartMin = observedMinEquity - equityPadding;
  const equityChartMax = observedMaxEquity + equityPadding;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
      {/* ── 1. Top Header Controller ──────────────────────────────────────── */}
      <div
        className="card-panel"
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "1rem",
          background: "linear-gradient(135deg, rgba(15,23,42,0.95) 0%, rgba(30,41,59,0.95) 100%)",
          borderColor: "rgba(255,255,255,0.08)",
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
            <Briefcase size={22} color="var(--tse-blue)" />
            <h2 style={{ fontSize: "1.2rem", fontWeight: 800, color: "#f8fafc", margin: 0 }}>
              موتور معاملات کاغذی و بازخورد آماری قابل حسابرسی
            </h2>
            <span
              style={{
                fontSize: "0.72rem",
                padding: "2px 8px",
                borderRadius: "12px",
                backgroundColor: status?.is_running ? "rgba(34, 197, 94, 0.18)" : "rgba(239, 68, 68, 0.18)",
                color: status?.is_running ? "var(--tse-green)" : "var(--tse-red)",
                fontWeight: 700,
                display: "inline-flex",
                alignItems: "center",
                gap: "4px",
              }}
            >
              <span
                style={{
                  width: 6,
                  height: 6,
                  borderRadius: "50%",
                  backgroundColor: status?.is_running ? "var(--tse-green)" : "var(--tse-red)",
                }}
              />
              {status?.is_running ? "پایش دقیقه‌ای داده: فعال" : "پایش داده: غیرفعال"}
            </span>
          </div>
          <p style={{ fontSize: "0.82rem", color: "#94a3b8", marginTop: "0.35rem", marginBottom: 0 }}>
            سرمایه اولیه/وجه نقد کمپین: <strong style={{ color: "#f1f5f9" }}>{formatToman(initialCapitalRials / 10)}</strong> • این عدد معامله نیست؛ تعداد اجرای ثبت‌شده: <strong style={{ color: fillCount === 0 ? "var(--tse-green)" : "var(--tse-blue)" }}>{formatNumberFa(fillCount)}</strong>
          </p>
          <p style={{ fontSize: "0.74rem", color: "#94a3b8", marginTop: "0.3rem", marginBottom: 0 }}>
            کمپین ثابت: <b style={{ direction: "ltr", unicodeBidi: "isolate", color: "#cbd5e1" }}>{portfolio.campaign_id || portfolio.id}</b>
            {portfolio.campaign_started_at ? ` • شروع: ${new Date(portfolio.campaign_started_at).toLocaleString("fa-IR")}` : ""}
          </p>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", flexWrap: "wrap" }}>
          {/* Manual Run Cycle Button */}
          <button
            onClick={triggerCycleNow}
            disabled={triggering || cycleBlocked}
            style={{
              backgroundColor: "var(--tse-blue)",
              color: "#fff",
              border: "none",
              padding: "0.5rem 1rem",
              borderRadius: "var(--radius-sm)",
              fontWeight: 700,
              fontSize: "0.84rem",
              cursor: triggering || cycleBlocked ? "not-allowed" : "pointer",
              display: "flex",
              alignItems: "center",
              gap: "0.4rem",
              fontFamily: "inherit",
              opacity: triggering || cycleBlocked ? 0.55 : 1,
              transition: "all 0.15s ease",
            }}
          >
            <Play size={15} className={triggering ? "animate-spin" : ""} />
            <span>{triggering ? "در حال اجرای اسکن..." : cycleBlocked ? "چرخه معاملاتی مسدود" : "اجرای دستی چرخه الان"}</span>
          </button>

          {/* Emergency Kill-Switch */}
          <button
            onClick={toggleKillSwitch}
            disabled={killSwitchLoading}
            style={{
              backgroundColor: portfolio?.kill_switch_active ? "var(--tse-red)" : "transparent",
              color: portfolio?.kill_switch_active ? "#fff" : "var(--tse-red)",
              border: `1px solid var(--tse-red)`,
              padding: "0.5rem 1rem",
              borderRadius: "var(--radius-sm)",
              fontWeight: 700,
              fontSize: "0.84rem",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "0.4rem",
              fontFamily: "inherit",
              transition: "all 0.15s ease",
            }}
          >
            <AlertOctagon size={16} />
            <span>{portfolio?.kill_switch_active ? "قطع اضطراری فعال (توقف معاملات)" : "کلید قطع اضطراری (Kill-Switch)"}</span>
          </button>
        </div>
      </div>

      {cycleMessage && (
        <div role="status" style={{ padding: "0.75rem 1rem", borderRadius: "8px", backgroundColor: "rgba(245,158,11,0.10)", border: "1px solid rgba(245,158,11,0.35)", color: "var(--tse-amber)", fontSize: "0.84rem", fontWeight: 700 }}>
          {cycleMessage}
        </div>
      )}

      {/* ── 1.5 Money Management & Capital Safety Cockpit ────────────────── */}
      <div
        className="card-panel"
        style={{
          background: "linear-gradient(135deg, rgba(15,23,42,0.9) 0%, rgba(30,41,59,0.7) 100%)",
          border: "1px solid rgba(59, 130, 246, 0.3)",
          padding: "1rem 1.25rem",
          display: "flex",
          flexDirection: "column",
          gap: "0.75rem",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.5rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <ShieldCheck size={19} color="var(--tse-blue)" />
            <h3 style={{ fontSize: "0.98rem", fontWeight: 800, color: "var(--text-primary)", margin: 0 }}>
              چارچوب هوشمند مدیریت سرمایه و کنترل درگیری دارایی (Money Management Rules)
            </h3>
          </div>
          <span style={{ fontSize: "0.74rem", fontWeight: 800, color: "var(--tse-green)", backgroundColor: "rgba(34,197,94,0.15)", padding: "2px 10px", borderRadius: "10px", border: "1px solid rgba(34,197,94,0.3)" }}>
            ✅ انضباط مالی و مهار ریسک فعال است
          </span>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "0.85rem" }}>
          <div style={{ backgroundColor: "rgba(30, 41, 59, 0.6)", padding: "0.65rem 0.85rem", borderRadius: "8px", border: "1px solid rgba(255,255,255,0.05)" }}>
            <span style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>سقف درگیری سرمایه در کل بازار:</span>
            <div style={{ fontWeight: 800, fontSize: "0.88rem", color: "var(--text-primary)", marginTop: "2px" }}>
              حداکثر {toPersianDigits(riskPolicy?.regimes?.RISK_ON?.max_gross_exposure_pct ?? 70)}٪ پورتفو در رژیم صعودی
            </div>
            <div style={{ fontSize: "0.7rem", color: "var(--tse-blue)", marginTop: "3px" }}>
              درگیری فعلی: {toPersianDigits(portfolioExposurePct.toFixed(0))}٪ ({toPersianDigits((((portfolio?.cash || 0) / totalEquityRials) * 100).toFixed(0))}٪ نقد محفوظ)
            </div>
          </div>

          <div style={{ backgroundColor: "rgba(30, 41, 59, 0.6)", padding: "0.65rem 0.85rem", borderRadius: "8px", border: "1px solid rgba(255,255,255,0.05)" }}>
            <span style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>سقف سرمایه‌گذاری در هر تک‌سهم:</span>
            <div style={{ fontWeight: 800, fontSize: "0.88rem", color: "var(--text-primary)", marginTop: "2px" }}>
              حداکثر {formatPercentFa(riskPolicy?.portfolio_limits?.exceptional_max_position_weight_pct ?? 10, 0, false)} کل سرمایه ({formatNumberFa((initialCapitalRials / 10) * ((riskPolicy?.portfolio_limits?.exceptional_max_position_weight_pct ?? 10) / 100) / 1_000_000)} میلیون تومان)
            </div>
            <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginTop: "3px" }}>
              تنوع‌بخشی بین ۸ الی ۱۲ نماد برتر بدون ریسک تمرکز
            </div>
          </div>

          <div style={{ backgroundColor: "rgba(30, 41, 59, 0.6)", padding: "0.65rem 0.85rem", borderRadius: "8px", border: "1px solid rgba(255,255,255,0.05)" }}>
            <span style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>سیستم افزایش پله‌ای (Scaling In):</span>
            <div style={{ fontWeight: 800, fontSize: "0.88rem", color: "var(--tse-green)", marginTop: "2px" }}>
              افزایش حجم در صورت ارتقای تحلیل
            </div>
            <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginTop: "3px" }}>
              ورود پول سنگین‌تر یا بریک‌اوت با حجم بالا (تا سقف ۱۰٪)
            </div>
          </div>

          <div style={{ backgroundColor: "rgba(30, 41, 59, 0.6)", padding: "0.65rem 0.85rem", borderRadius: "8px", border: "1px solid rgba(255,255,255,0.05)" }}>
            <span style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>سیستم کاهش پله‌ای (Trimming):</span>
            <div style={{ fontWeight: 800, fontSize: "0.88rem", color: "var(--tse-amber)", marginTop: "2px" }}>
              سیو سود ۵۰٪ در تارگت یا تضعیف تحلیل
            </div>
            <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginTop: "3px" }}>
              آزاد کردن نقدینگی و ریسک‌فری کردن مابقی حجم
            </div>
          </div>
        </div>
      </div>

      {/* ── 2. Summary KPI Cards ────────────────────────────────────────── */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "1rem" }}>
        <div className="card-panel" style={{ borderLeft: "4px solid var(--tse-blue)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: "0.76rem", color: "var(--text-muted)" }}>معاملات اجراشده در این کمپین</span>
            <span style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>دفترکل اجرا</span>
          </div>
          <div style={{ fontSize: "1.55rem", fontWeight: 900, color: fillCount === 0 ? "var(--text-primary)" : "var(--tse-blue)", marginTop: "0.25rem" }} className="tabular-num">
            {toPersianDigits(fillCount)} <span style={{ fontSize: "0.8rem", color: "var(--text-muted)", fontWeight: 500 }}>اجرا</span>
          </div>
          <div style={{ fontSize: "0.72rem", color: "var(--text-muted)", marginTop: "0.2rem" }}>
            {formatNumberFa(openPositionsCount)} موقعیت باز • {formatNumberFa(closedTrades.length)} معامله بسته • سرمایه درگیر: {formatDecimalFa(totalInvestedInPositionsTomans / 1_000_000, 1)} میلیون تومان
          </div>
        </div>

        {/* Total Equity */}
        <div className="card-panel" style={{ borderLeft: `4px solid ${totalReturnPct >= 0 ? "var(--tse-green)" : "var(--tse-red)"}` }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: "0.76rem", color: "var(--text-muted)" }}>ارزش خالص حساب (نقد + موقعیت باز)</span>
            <span style={{ fontSize: "0.78rem", fontWeight: 700, color: totalReturnPct >= 0 ? "var(--tse-green)" : "var(--tse-red)" }}>
              {formatPercentFa(totalReturnPct, 2, true)}
            </span>
          </div>
          <div style={{ fontSize: "1.4rem", fontWeight: 900, color: "var(--text-primary)", marginTop: "0.25rem" }} className="tabular-num">
            {formatDecimalFa(totalEquityTomans / 1_000_000, 1)}{" "}
            <span style={{ fontSize: "0.8rem", color: "var(--text-muted)", fontWeight: 500 }}>میلیون تومان</span>
          </div>
          <div style={{ fontSize: "0.72rem", color: "var(--text-muted)", marginTop: "0.2rem" }} className="tabular-num">
            مانده حساب است؛ ارزش یک معامله نیست
          </div>
        </div>

        {/* Free Cash */}
        <div className="card-panel">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: "0.76rem", color: "var(--text-muted)" }}>نقدینگی آزاد در دسترس</span>
            <span style={{ fontSize: "0.72rem", color: "var(--tse-blue)", fontWeight: 600 }}>
              {formatPercentFa(totalEquityRials > 0 ? ((portfolio?.cash || 0) / totalEquityRials) * 100 : 0, 0, false)} نقد
            </span>
          </div>
          <div style={{ fontSize: "1.4rem", fontWeight: 900, color: "var(--tse-blue)", marginTop: "0.25rem" }} className="tabular-num">
            {formatDecimalFa(((portfolio?.cash || 0) / 10) / 1_000_000, 1)}{" "}
            <span style={{ fontSize: "0.8rem", color: "var(--text-muted)", fontWeight: 500 }}>میلیون تومان</span>
          </div>
          <div style={{ fontSize: "0.72rem", color: "var(--text-muted)", marginTop: "0.2rem" }} className="tabular-num">
            سرمایه درگیر در سهام: {formatDecimalFa(totalInvestedInPositionsTomans / 1_000_000, 1)} م.ت ({formatPercentFa(portfolioExposurePct, 0, false)})
          </div>
        </div>

        {/* Unrealized PnL */}
        <div className="card-panel">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: "0.76rem", color: "var(--text-muted)" }}>سود/زیان باز لحظه‌ای</span>
            <span style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>{openPositionsCount} موقعیت فعال</span>
          </div>
          <div
            style={{
              fontSize: "1.4rem",
              fontWeight: 900,
              color: (portfolio?.unrealized_pnl || 0) >= 0 ? "var(--tse-green)" : "var(--tse-red)",
              marginTop: "0.25rem",
            }}
            className="tabular-num"
          >
            {(portfolio?.unrealized_pnl || 0) >= 0 ? "+" : ""}
            {formatDecimalFa(((portfolio?.unrealized_pnl || 0) / 10) / 1_000_000, 2)}{" "}
            <span style={{ fontSize: "0.8rem", color: "var(--text-muted)", fontWeight: 500 }}>میلیون تومان</span>
          </div>
          <div style={{ fontSize: "0.72rem", color: (portfolio?.unrealized_pnl || 0) >= 0 ? "var(--tse-green)" : "var(--tse-red)", marginTop: "0.2rem", fontWeight: 700 }} className="tabular-num">
            {formatPercentFa(totalReturnPct, 2, true)} سود تجمعی کل پورتفو
          </div>
        </div>

        {/* Win Rate & Performance */}
        <div className="card-panel">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: "0.76rem", color: "var(--text-muted)" }}>نسبت ریسک به ریوارد (R/R)</span>
            <span style={{ fontSize: "0.72rem", color: "var(--tse-amber)", fontWeight: 600 }}>میانگین معاملات</span>
          </div>
          <div style={{ fontSize: "1.4rem", fontWeight: 900, color: "var(--tse-amber)", marginTop: "0.25rem" }} className="tabular-num">
            {avgRRRatio != null ? formatRatioFa(`1:${avgRRRatio.toFixed(1)}`) : "—"}
          </div>
          <div style={{ fontSize: "0.72rem", color: "var(--text-muted)", marginTop: "0.2rem" }}>
            نرخ برد معاملات بسته‌شده: {winRatePct != null ? formatPercentFa(winRatePct, 0, false) : "نمونه‌ای ثبت نشده"}
          </div>
        </div>

        {/* Engine Cycles */}
        <div className="card-panel">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: "0.76rem", color: "var(--text-muted)" }}>چرخه‌های اسکن خودکار</span>
            <span style={{ fontSize: "0.72rem", color: "var(--tse-green)", fontWeight: 600 }}>هر ۱ دقیقه حین بازار</span>
          </div>
          <div style={{ fontSize: "1.4rem", fontWeight: 900, color: "var(--text-primary)", marginTop: "0.25rem" }} className="tabular-num">
            {status?.total_cycles || 0}{" "}
            <span style={{ fontSize: "0.8rem", color: "var(--text-muted)", fontWeight: 500 }}>چرخه</span>
          </div>
          <div style={{ fontSize: "0.72rem", color: "var(--text-muted)", marginTop: "0.2rem" }}>
            {status?.last_run_at ? `آخرین: ${new Date(status.last_run_at).toLocaleTimeString("fa-IR")}` : "در صف اجرا"}
          </div>
        </div>
      </div>

      {/* ── 3. Interactive Sub-Tabs Bar ─────────────────────────────────── */}
      <div style={{ display: "flex", gap: "0.5rem", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "0.5rem", flexWrap: "wrap" }}>
        <button
          onClick={() => setActiveSubTab("positions")}
          style={{
            padding: "0.6rem 1.1rem",
            borderRadius: "var(--radius-sm)",
            border: "none",
            backgroundColor: activeSubTab === "positions" ? "var(--tse-blue)" : "transparent",
            color: activeSubTab === "positions" ? "#fff" : "var(--text-secondary)",
            fontWeight: 700,
            fontSize: "0.85rem",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "0.4rem",
            fontFamily: "inherit",
          }}
        >
          <Layers size={16} />
          <span>پوزیشن‌های باز ({openPositionsCount})</span>
        </button>

        <button
          onClick={() => setActiveSubTab("strategies")}
          style={{
            padding: "0.6rem 1.1rem",
            borderRadius: "var(--radius-sm)",
            border: "none",
            backgroundColor: activeSubTab === "strategies" ? "var(--tse-blue)" : "transparent",
            color: activeSubTab === "strategies" ? "#fff" : "var(--text-secondary)",
            fontWeight: 700,
            fontSize: "0.85rem",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "0.4rem",
            fontFamily: "inherit",
          }}
        >
          <Sparkles size={16} />
          <span>ماتریس آرا و استراتژی‌های تست‌شده ({opportunities.length})</span>
        </button>

        <button
          onClick={() => setActiveSubTab("equity")}
          style={{
            padding: "0.6rem 1.1rem",
            borderRadius: "var(--radius-sm)",
            border: "none",
            backgroundColor: activeSubTab === "equity" ? "var(--tse-blue)" : "transparent",
            color: activeSubTab === "equity" ? "#fff" : "var(--text-secondary)",
            fontWeight: 700,
            fontSize: "0.85rem",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "0.4rem",
            fontFamily: "inherit",
          }}
        >
          <TrendingUp size={16} />
          <span>نمودار رشد سرمایه (Equity Curve)</span>
        </button>

        <button
          onClick={() => setActiveSubTab("trades")}
          style={{
            padding: "0.6rem 1.1rem",
            borderRadius: "var(--radius-sm)",
            border: "none",
            backgroundColor: activeSubTab === "trades" ? "var(--tse-blue)" : "transparent",
            color: activeSubTab === "trades" ? "#fff" : "var(--text-secondary)",
            fontWeight: 700,
            fontSize: "0.85rem",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "0.4rem",
            fontFamily: "inherit",
          }}
        >
          <Activity size={16} />
          <span>تاریخچه معاملات و دیتای ML ({trades.length})</span>
        </button>

        <button
          onClick={() => setActiveSubTab("indicators")}
          style={{
            padding: "0.6rem 1.1rem",
            borderRadius: "var(--radius-sm)",
            border: "none",
            backgroundColor: activeSubTab === "indicators" ? "var(--tse-blue)" : "transparent",
            color: activeSubTab === "indicators" ? "#fff" : "var(--text-secondary)",
            fontWeight: 700,
            fontSize: "0.85rem",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "0.4rem",
            fontFamily: "inherit",
          }}
        >
          <Award size={16} />
          <span>ارزیابی دقت اندیکاتورها ({attribution.length})</span>
        </button>
      </div>

      {/* ── 4. Tab 1: Detailed Open Positions ────────────────────────────── */}
      {activeSubTab === "positions" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          {positions.length === 0 ? (
            <div className="card-panel" style={{ textAlign: "center", padding: "4rem 2rem", color: "var(--text-muted)" }}>
              <Briefcase size={48} style={{ opacity: 0.3, margin: "0 auto 1rem" }} />
              <h3 style={{ fontSize: "1.1rem", fontWeight: 700, color: "var(--text-primary)" }}>در حال حاضر پوزیشن بازی وجود ندارد</h3>
              <p style={{ fontSize: "0.85rem", maxWidth: 500, margin: "0.5rem auto 1.5rem" }}>
                فعلاً JSON API رسمی TSETMC داده قابل معامله تأیید نکرده است؛ تا رفع گیت داده و کلید قطع اضطراری، هیچ سهمی به پورتفو اضافه نمی‌شود.
              </p>
              <button
                onClick={triggerCycleNow}
                disabled={triggering || cycleBlocked}
                style={{
                  backgroundColor: "var(--tse-blue)",
                  color: "#fff",
                  border: "none",
                  padding: "0.6rem 1.25rem",
                  borderRadius: "var(--radius-sm)",
                  fontWeight: 700,
                  fontSize: "0.85rem",
                  cursor: triggering || cycleBlocked ? "not-allowed" : "pointer",
                  fontFamily: "inherit",
                  opacity: triggering || cycleBlocked ? 0.55 : 1,
                }}
              >
                {cycleBlocked ? "اسکن تحلیلی — بدون معامله (از داشبورد بروزرسانی کنید)" : "اجرای چرخه بررسی و ارزیابی"}
              </button>
            </div>
          ) : (
            <div className="card-panel" style={{ padding: 0, overflow: "hidden" }}>
              <div
                style={{
                  padding: "0.85rem 1.25rem",
                  backgroundColor: "var(--bg-surface)",
                  borderBottom: "1px solid var(--border-subtle)",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  flexWrap: "wrap",
                  gap: "0.5rem",
                }}
              >
                <div>
                  <h3 style={{ fontSize: "0.95rem", fontWeight: 800, color: "var(--text-primary)", margin: 0 }}>
                    پوزیشن‌های زنده و فعال پورتفو آزمایشی
                  </h3>
                  <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                    برای مشاهده نمودار اختصاصی، فاصله تا تارگت سود، کالبدشکافی هوش مصنوعی و دکمه خروج روی هر سطر کلیک کنید.
                  </span>
                </div>
                <span style={{ fontSize: "0.78rem", fontWeight: 700, color: "var(--tse-blue)", backgroundColor: "rgba(59, 130, 246, 0.12)", padding: "3px 10px", borderRadius: "12px" }}>
                  {positions.length} سهم تحت مدیریت
                </span>
              </div>

              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.82rem" }}>
                  <thead>
                    <tr style={{ color: "var(--text-muted)", textAlign: "right", borderBottom: "1px solid var(--border-subtle)", backgroundColor: "var(--bg-surface)" }}>
                      <th style={{ padding: "0.75rem 1rem" }}>نماد / رژیم بازار</th>
                      <th style={{ padding: "0.75rem 1rem" }}>سرمایه وارد شده</th>
                      <th style={{ padding: "0.75rem 1rem" }}>قیمت ورود / فعلی</th>
                      <th style={{ padding: "0.75rem 1rem" }}>سود / زیان لحظه‌ای</th>
                      <th style={{ padding: "0.75rem 1rem" }}>حد ضرر / فاصله</th>
                      <th style={{ padding: "0.75rem 1rem" }}>هدف سود / فاصله</th>
                      <th style={{ padding: "0.75rem 1rem" }}>مدت باز بودن</th>
                      <th style={{ padding: "0.75rem 1rem" }}>تخمین تا سود</th>
                      <th style={{ padding: "0.75rem 1rem" }}>ریسک / R:R</th>
                      <th style={{ padding: "0.75rem 1rem" }}>روش و دلیل خرید</th>
                      <th style={{ padding: "0.75rem 1rem", textAlign: "center" }}>عملیات</th>
                    </tr>
                  </thead>
                  <tbody>
                    {positions.map((pos) => {
                      const isProfit = pos.unrealized_pnl >= 0;
                      const investedT = (pos.total_invested_tomans || (pos.quantity * pos.average_entry_price / 10)) / 1_000_000;
                      return (
                        <tr
                          key={pos.id}
                          style={{
                            borderBottom: "1px solid var(--border-subtle)",
                            transition: "background-color 0.15s ease",
                            cursor: "pointer",
                          }}
                          onClick={() => setSelectedPosition(pos)}
                          onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = "var(--bg-surface)")}
                          onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "transparent")}
                        >
                          {/* Symbol & Market Stage */}
                          <td style={{ padding: "0.85rem 1rem" }}>
                            <div style={{ fontWeight: 800, fontSize: "0.95rem", color: "var(--text-primary)" }}>{pos.symbol}</div>
                            <span
                              style={{
                                fontSize: "0.68rem",
                                padding: "1px 6px",
                                borderRadius: "4px",
                                backgroundColor: "rgba(59, 130, 246, 0.1)",
                                color: "var(--tse-blue)",
                                display: "inline-block",
                                marginTop: "2px",
                              }}
                            >
                              {pos.market_regime_fa || "رژیم نامشخص"}
                            </span>
                          </td>

                          {/* Invested Capital */}
                          <td style={{ padding: "0.85rem 1rem" }}>
                            <div className="tabular-num" style={{ fontWeight: 800, color: "var(--text-primary)" }}>
                              {toPersianDigits(investedT.toFixed(1))} <span style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>میلیون تومان</span>
                            </div>
                            <div style={{ fontSize: "0.7rem", color: "var(--text-muted)" }} className="tabular-num">
                              {pos.quantity?.toLocaleString("fa-IR")} سهم
                            </div>
                          </td>

                          {/* Entry / Current Price */}
                          <td style={{ padding: "0.85rem 1rem" }}>
                            <div style={{ color: "var(--text-muted)", fontSize: "0.75rem" }} className="tabular-num">
                              ورود: {pos.average_entry_price?.toLocaleString("fa-IR")} ﷼
                            </div>
                            <div style={{ fontWeight: 800, color: "var(--text-primary)", fontSize: "0.88rem" }} className="tabular-num">
                              فعلی: {pos.current_price?.toLocaleString("fa-IR")} ﷼
                            </div>
                          </td>

                          {/* Unrealized PnL */}
                          <td style={{ padding: "0.85rem 1rem" }}>
                            <div
                              style={{
                                fontWeight: 900,
                                fontSize: "0.95rem",
                                color: isProfit ? "var(--tse-green)" : "var(--tse-red)",
                              }}
                              className="tabular-num"
                            >
                              {isProfit ? "+" : ""}{pos.unrealized_pnl_pct}%
                            </div>
                            <div
                              style={{
                                fontSize: "0.72rem",
                                color: isProfit ? "var(--tse-green)" : "var(--tse-red)",
                                fontWeight: 700,
                              }}
                              className="tabular-num"
                            >
                              {isProfit ? "+" : ""}{(pos.unrealized_pnl / 10).toLocaleString("fa-IR")} تومان
                            </div>
                          </td>

                          {/* Stop Loss */}
                          <td style={{ padding: "0.85rem 1rem" }}>
                            <div style={{ color: "var(--tse-red)", fontWeight: 700 }} className="tabular-num">
                              {pos.stop_loss ? `${pos.stop_loss.toLocaleString("fa-IR")} ﷼` : "—"}
                            </div>
                            <div style={{ fontSize: "0.7rem", color: "var(--tse-red)", fontWeight: 600 }} className="tabular-num">
                              {pos.distance_to_stop_pct ? `${pos.distance_to_stop_pct}%` : ""}
                            </div>
                          </td>

                          {/* Target Price */}
                          <td style={{ padding: "0.85rem 1rem" }}>
                            <div style={{ color: "var(--tse-green)", fontWeight: 700 }} className="tabular-num">
                              {pos.target_price ? `${pos.target_price.toLocaleString("fa-IR")} ﷼` : "—"}
                            </div>
                            <div style={{ fontSize: "0.7rem", color: "var(--tse-green)", fontWeight: 700 }} className="tabular-num">
                              {pos.distance_to_target_pct ? `+${pos.distance_to_target_pct}%` : ""}
                            </div>
                          </td>

                          {/* Days Open */}
                          <td style={{ padding: "0.85rem 1rem" }}>
                            <div style={{ display: "flex", alignItems: "center", gap: "4px", fontWeight: 600, color: "var(--text-primary)" }}>
                              <Clock size={13} color="var(--text-muted)" />
                              <span>{pos.days_open ? `${pos.days_open} روز` : "امروز"}</span>
                            </div>
                            <div style={{ fontSize: "0.68rem", color: "var(--text-muted)" }}>
                              {pos.opened_at ? new Date(pos.opened_at).toLocaleDateString("fa-IR") : ""}
                            </div>
                          </td>

                          {/* Expected Days to Target */}
                          <td style={{ padding: "0.85rem 1rem" }}>
                            <div style={{ display: "flex", alignItems: "center", gap: "4px", color: "var(--tse-amber)", fontWeight: 700 }}>
                              <Target size={13} />
                              <span>{pos.expected_days_to_target != null ? `${pos.expected_days_to_target} روز کاری` : "—"}</span>
                            </div>
                            <div style={{ fontSize: "0.68rem", color: "var(--text-muted)" }}>افق استراتژی</div>
                          </td>

                          {/* Risk & R/R */}
                          <td style={{ padding: "0.85rem 1rem" }}>
                            <div style={{ fontWeight: 600, color: "var(--text-primary)" }} className="tabular-num">
                              ریسک: {pos.risk_pct != null ? `${pos.risk_pct}%` : "—"}
                            </div>
                            <div style={{ fontSize: "0.72rem", color: "var(--tse-blue)", fontWeight: 700 }} className="tabular-num">
                              R/R: {pos.risk_reward_ratio == null ? "—" : (typeof pos.risk_reward_ratio === "number" ? `1:${pos.risk_reward_ratio}` : pos.risk_reward_ratio)}
                            </div>
                          </td>

                          {/* Decision Method & Reason */}
                          <td style={{ padding: "0.85rem 1rem", maxWidth: "220px" }}>
                            <div style={{ fontSize: "0.76rem", fontWeight: 700, color: "var(--text-primary)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                              {pos.decision_method || "—"}
                            </div>
                            <div style={{ fontSize: "0.7rem", color: "var(--text-secondary)", marginTop: "2px", lineHeight: "1.3", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                              {pos.entry_reason_fa || "دلیل ثبت نشده"}
                            </div>
                          </td>

                          {/* Details & Actions Button */}
                          <td style={{ padding: "0.85rem 1rem", textAlign: "center" }}>
                            <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "4px" }}>
                              {/* Scale In */}
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleScaleInPosition(pos.id);
                                }}
                                disabled={actionLoadingId === pos.id}
                                style={{
                                  padding: "3px 6px",
                                  backgroundColor: "rgba(34, 197, 94, 0.15)",
                                  color: "var(--tse-green)",
                                  border: "1px solid rgba(34, 197, 94, 0.3)",
                                  borderRadius: "4px",
                                  fontSize: "0.72rem",
                                  fontWeight: 800,
                                  cursor: "pointer",
                                  fontFamily: "inherit",
                                }}
                                title="افزایش پله‌ای حجم سهم برنده (+ ۳٪ تا سقف ۱۰٪)"
                              >
                                ➕ افزایش
                              </button>

                              {/* Trim 50% */}
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleTrimPosition(pos.id);
                                }}
                                disabled={actionLoadingId === pos.id}
                                style={{
                                  padding: "3px 6px",
                                  backgroundColor: "rgba(245, 158, 11, 0.15)",
                                  color: "var(--tse-amber)",
                                  border: "1px solid rgba(245, 158, 11, 0.3)",
                                  borderRadius: "4px",
                                  fontSize: "0.72rem",
                                  fontWeight: 800,
                                  cursor: "pointer",
                                  fontFamily: "inherit",
                                }}
                                title="کاهش ۵۰٪ حجم جهت سیو سود یا کاهش ریسک"
                              >
                                ✂️ کاهش ۵۰٪
                              </button>

                              {/* Details */}
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setSelectedPosition(pos);
                                }}
                                style={{
                                  display: "inline-flex",
                                  alignItems: "center",
                                  gap: "3px",
                                  padding: "3px 6px",
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
                                <Eye size={11} />
                                <span>چارت</span>
                              </button>
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
      )}

      {/* ── 4.5 Tab: Strategy Confluence Matrix ────────────────────────────── */}
      {activeSubTab === "strategies" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          <div className="card-panel">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.5rem" }}>
              <div>
                <h3 style={{ fontSize: "1.05rem", fontWeight: 800, color: "var(--text-primary)", margin: 0, display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  <Sparkles size={18} color="var(--tse-blue)" />
                  ماتریس آرا و استراتژی‌های تست‌شده بازار
                </h3>
                <p style={{ fontSize: "0.78rem", color: "var(--text-secondary)", margin: "0.3rem 0 0" }}>
                  مشاهده دقیق نتایج بررسی ۱۲ استراتژی کمّی برای هر یک از نمادهای رادار، آرای مثبت، درصد اطمینان و دلایل ورود به زبان فارسی
                </p>
              </div>
              <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
                {opportunities.length} فرصت ارزیابی‌شده در دیده‌بان
              </span>
            </div>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            {opportunities.length === 0 ? (
              <div className="card-panel" style={{ textAlign: "center", padding: "3rem", color: "var(--text-muted)" }}>
                در حال حاضر فرصتی بارگذاری نشده است. لطفاً دکمه بروزرسانی یا اجرای اسکن را بزنید.
              </div>
            ) : (
              opportunities.map((opp) => {
                const votes = opp.strategy_votes || [];
                const pProfitPct = opp.p_profit != null ? Math.round(opp.p_profit * 100) : null;
                const scoreColor = opp.opportunity_score >= 80 ? "var(--tse-green)" : opp.opportunity_score >= 70 ? "var(--tse-blue)" : "var(--tse-amber)";
                const target1 = opp.exit_plan?.targets?.[0] ?? null;
                const target2 = opp.exit_plan?.targets?.[1] ?? null;
                const stopLoss = opp.invalidation?.price ?? null;

                return (
                  <div key={opp.id} className="card-panel" style={{ display: "flex", flexDirection: "column", gap: "0.85rem", borderLeft: `4px solid ${scoreColor}` }}>
                    {/* Symbol Header Bar */}
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.75rem", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "0.75rem" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                        <span style={{ fontSize: "1.2rem", fontWeight: 900, color: "var(--text-primary)" }}>{opp.symbol}</span>
                        <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>{opp.name_fa}</span>
                        <span style={{ fontSize: "0.72rem", backgroundColor: "rgba(59, 130, 246, 0.12)", color: "var(--tse-blue)", padding: "2px 8px", borderRadius: "4px", fontWeight: 700 }}>
                          {opp.sector || "گروه نامشخص"}
                        </span>
                      </div>

                      <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
                          <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>امتیاز رادار:</span>
                          <span style={{ fontSize: "1rem", fontWeight: 900, color: scoreColor }} className="tabular-num">
                            {opp.opportunity_score}
                          </span>
                        </div>
                        <div style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
                          <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>احتمال سود (p_profit):</span>
                          <span style={{ fontSize: "1rem", fontWeight: 800, color: "var(--tse-blue)" }} className="tabular-num">
                            {pProfitPct != null ? `${pProfitPct}٪` : "—"}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Price Targets Row */}
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: "0.6rem", fontSize: "0.78rem" }}>
                      <div style={{ backgroundColor: "var(--bg-surface)", padding: "0.5rem 0.75rem", borderRadius: "6px" }}>
                        <span style={{ color: "var(--text-muted)", fontSize: "0.7rem" }}>محدوده ورود:</span>
                        <div style={{ fontWeight: 700, color: "var(--text-primary)" }} className="tabular-num">
                          {opp.entry_zone?.low?.toLocaleString("fa-IR")} - {opp.entry_zone?.high?.toLocaleString("fa-IR")} ﷼
                        </div>
                      </div>
                      <div style={{ backgroundColor: "var(--bg-surface)", padding: "0.5rem 0.75rem", borderRadius: "6px" }}>
                        <span style={{ color: "var(--text-muted)", fontSize: "0.7rem" }}>حد ضرر:</span>
                        <div style={{ fontWeight: 700, color: "var(--tse-red)" }} className="tabular-num">
                          {stopLoss != null ? `${stopLoss.toLocaleString("fa-IR")} ﷼` : "—"}
                        </div>
                      </div>
                      <div style={{ backgroundColor: "var(--bg-surface)", padding: "0.5rem 0.75rem", borderRadius: "6px" }}>
                        <span style={{ color: "var(--text-muted)", fontSize: "0.7rem" }}>تارگت ۱:</span>
                        <div style={{ fontWeight: 700, color: "var(--tse-green)" }} className="tabular-num">
                          {target1 != null ? `${target1.toLocaleString("fa-IR")} ﷼` : "—"}
                        </div>
                      </div>
                      <div style={{ backgroundColor: "var(--bg-surface)", padding: "0.5rem 0.75rem", borderRadius: "6px" }}>
                        <span style={{ color: "var(--text-muted)", fontSize: "0.7rem" }}>تارگت ۲:</span>
                        <div style={{ fontWeight: 700, color: "var(--tse-green)" }} className="tabular-num">
                          {target2 != null ? `${target2.toLocaleString("fa-IR")} ﷼` : "—"}
                        </div>
                      </div>
                    </div>

                    {/* Votes Grid */}
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "0.5rem" }}>
                      {votes.map((v: any, vIdx: number) => {
                        const sKey = typeof v === "string" ? v : v.strategy || v.strategy_key || "";
                        const votePower = typeof v === "object" && v.vote != null ? Math.round(v.vote * 100) : null;
                        const reasonFa = typeof v === "object" ? v.reason_fa : "";

                        return (
                          <div
                            key={vIdx}
                            style={{
                              backgroundColor: "var(--bg-surface)",
                              padding: "0.6rem 0.85rem",
                              borderRadius: "6px",
                              border: "1px solid var(--border-subtle)",
                              display: "flex",
                              flexDirection: "column",
                              gap: "0.25rem",
                            }}
                          >
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                              <span style={{ fontWeight: 700, fontSize: "0.82rem", color: "var(--text-primary)" }}>
                                {getStrategyFa(sKey)}
                              </span>
                              <span style={{ fontSize: "0.72rem", color: "var(--tse-blue)", fontWeight: 700 }} className="tabular-num">
                                قدرت: {votePower != null ? `${votePower}٪` : "—"}
                              </span>
                            </div>
                            <span style={{ fontSize: "0.74rem", color: "var(--text-secondary)", lineHeight: 1.4 }}>
                              {reasonFa || "دلیل ماشینی ثبت نشده"}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}

      {/* ── 5. Tab 2: Equity Curve ───────────────────────────────────────── */}
      {activeSubTab === "equity" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          <div className="card-panel">
            <h3 style={{ fontSize: "1.05rem", fontWeight: 800, color: "var(--text-primary)", margin: 0, display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <TrendingUp size={18} color="var(--tse-green)" />
              نمودار رشد ارزش کل سرمایه و پورتفو (Equity Curve)
            </h3>
            <p style={{ fontSize: "0.78rem", color: "var(--text-secondary)", margin: "0.3rem 0 0" }}>
              رصد تغییرات ارزش پورتفو، سودهای تحقق‌یافته و مقایسه با سرمایه اولیه ثبت‌شده کمپین
            </p>
          </div>

          <div className="card-panel" style={{ padding: "1.5rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
              <div>
                <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>سرمایه اولیه:</span>
                <span style={{ fontWeight: 700, color: "var(--text-primary)", marginRight: "0.3rem" }}>{formatToman(initialCapitalRials / 10)}</span>
              </div>
              <div>
                <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>ارزش فعلی:</span>
                <span style={{ color: "var(--text-muted)", marginRight: "1rem", fontSize: "0.85rem" }} className="tabular-num">
                  {(totalEquityTomans).toLocaleString("fa-IR")} تومان ({totalReturnPct >= 0 ? "+" : ""}{toPersianDigits(totalReturnPct.toFixed(2))}٪)
                </span>
              </div>
            </div>

            {/* Visual SVG Equity Curve */}
            <div style={{ height: "260px", width: "100%", display: "flex", alignItems: "flex-end", gap: "4px", padding: "1rem 0", borderBottom: "1px solid var(--border-subtle)" }}>
              {history.length === 1 ? (
                <div
                  data-testid="equity-opening-point"
                  aria-label={`نقطه افتتاحیه کمپین با ارزش ${Math.round(history[0].total_equity / 10)} تومان`}
                  style={{
                    width: "100%",
                    height: "100%",
                    position: "relative",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <div style={{ position: "absolute", insetInline: 0, top: "50%", height: "1px", backgroundColor: "rgba(59,130,246,0.35)" }} />
                  <div style={{ position: "relative", display: "flex", flexDirection: "column", alignItems: "center", gap: "0.45rem" }}>
                    <span style={{ width: 16, height: 16, borderRadius: "50%", backgroundColor: "var(--tse-blue)", border: "3px solid rgba(147,197,253,0.45)", boxShadow: "0 0 0 5px rgba(59,130,246,0.12)" }} />
                    <strong style={{ color: "var(--text-primary)", fontSize: "0.82rem" }}>{formatToman(history[0].total_equity / 10)}</strong>
                    <span style={{ color: "var(--text-muted)", fontSize: "0.72rem" }}>
                      نقطه افتتاحیه • {new Date(history[0].snapshot_at).toLocaleString("fa-IR")}
                    </span>
                  </div>
                </div>
              ) : history.length > 1 ? (
                history.map((h, idx) => {
                  const heightPct = Math.max(15, Math.min(95, ((h.total_equity - equityChartMin) / (equityChartMax - equityChartMin)) * 100));
                  const isUp = h.total_equity >= initialCapitalRials;

                  return (
                    <div
                      key={idx}
                      title={`تاریخ: ${new Date(h.snapshot_at).toLocaleDateString("fa-IR")} | ارزش: ${(h.total_equity / 10).toLocaleString("fa-IR")} تومان`}
                      style={{
                        flex: 1,
                        height: `${heightPct}%`,
                        backgroundColor: isUp ? "var(--tse-green)" : "var(--tse-red)",
                        borderRadius: "2px 2px 0 0",
                        opacity: 0.85,
                        transition: "all 0.2s ease",
                      }}
                    />
                  );
                })
              ) : (
                <div style={{ width: "100%", textAlign: "center", color: "var(--text-muted)", fontSize: "0.85rem", alignSelf: "center" }}>
                  داده‌های نمودار با اجرای دوره‌ای اسکن‌ها ذخیره و نمایش داده خواهند شد.
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ── 6. Tab 3: Trade History & ML Dataset ─────────────────────────── */}
      {activeSubTab === "trades" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          <div className="card-panel">
            <h3 style={{ fontSize: "1.05rem", fontWeight: 800, color: "var(--text-primary)", margin: 0, display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <Activity size={18} color="var(--tse-blue)" />
              تاریخچه معاملات آزمایشی و پایگاه داده یادگیری ماشین (ML Dataset)
            </h3>
            <p style={{ fontSize: "0.78rem", color: "var(--text-secondary)", margin: "0.3rem 0 0" }}>
              ثبت تمام ویژگی‌های بازار در لحظه ورود و خروج به همراه دلایل سود و درس‌آموخته‌های معاملات زیان‌ده
            </p>
          </div>

          <div className="card-panel" style={{ padding: 0, overflow: "hidden" }}>
            {trades.length === 0 ? (
              <div style={{ padding: "3rem", textAlign: "center", color: "var(--text-muted)", fontSize: "0.85rem" }}>
                هنوز معامله‌ای بسته نشده است. با فعال شدن حد سود یا حد ضرر، لاگ کامل معامله در اینجا ثبت خواهد شد.
              </div>
            ) : (
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.82rem" }}>
                  <thead>
                    <tr style={{ color: "var(--text-muted)", textAlign: "right", borderBottom: "1px solid var(--border-subtle)", backgroundColor: "var(--bg-surface)" }}>
                      <th style={{ padding: "0.75rem 1rem" }}>نماد</th>
                      <th style={{ padding: "0.75rem 1rem" }}>قیمت ورود</th>
                      <th style={{ padding: "0.75rem 1rem" }}>قیمت خروج</th>
                      <th style={{ padding: "0.75rem 1rem" }}>سود/زیان خالص</th>
                      <th style={{ padding: "0.75rem 1rem" }}>درصد بازده</th>
                      <th style={{ padding: "0.75rem 1rem" }}>مدت نگهداری</th>
                      <th style={{ padding: "0.75rem 1rem" }}>علت خروج</th>
                      <th style={{ padding: "0.75rem 1rem" }}>درس‌آموخته معاملاتی (AI Lesson)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {trades.map((t) => {
                      const isWin = t.net_pnl > 0;
                      return (
                        <tr key={t.id} style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                          <td style={{ padding: "0.85rem 1rem", fontWeight: 800, color: "var(--text-primary)" }}>{t.symbol}</td>
                          <td style={{ padding: "0.85rem 1rem" }} className="tabular-num">{t.entry_price?.toLocaleString("fa-IR")} ﷼</td>
                          <td style={{ padding: "0.85rem 1rem" }} className="tabular-num">{t.exit_price ? `${t.exit_price.toLocaleString("fa-IR")} ﷼` : "—"}</td>
                          <td style={{ padding: "0.85rem 1rem", fontWeight: 700, color: isWin ? "var(--tse-green)" : "var(--tse-red)" }} className="tabular-num">
                            {(t.net_pnl / 10).toLocaleString("fa-IR")} تومان
                          </td>
                          <td style={{ padding: "0.85rem 1rem", fontWeight: 800, color: isWin ? "var(--tse-green)" : "var(--tse-red)" }} className="tabular-num">
                            {isWin ? "+" : ""}{t.return_pct}%
                          </td>
                          <td style={{ padding: "0.85rem 1rem" }}>{toPersianDigits(t.holding_days)} روز ({toPersianDigits(t.holding_hours?.toFixed(0) || "0")} ساعت)</td>
                          <td style={{ padding: "0.85rem 1rem" }}>
                            <span style={{ fontSize: "0.75rem", backgroundColor: isWin ? "rgba(34, 197, 94, 0.15)" : "rgba(239, 68, 68, 0.15)", color: isWin ? "var(--tse-green)" : "var(--tse-red)", padding: "2px 8px", borderRadius: "4px", fontWeight: 700 }}>
                              {getExitReasonFa(t.exit_reason)}
                            </span>
                          </td>
                          <td style={{ padding: "0.85rem 1rem", fontSize: "0.75rem", color: "var(--text-secondary)" }}>{t.lesson_fa || t.reason_fa}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── 7. Tab 4: Indicator Performance Attribution ─────────────────── */}
      {activeSubTab === "indicators" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          <div className="card-panel">
            <h3 style={{ fontSize: "1.05rem", fontWeight: 800, color: "var(--text-primary)", margin: 0, display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <Award size={18} color="var(--tse-amber)" />
              ارزیابی و اسناد عملکرد اندیکاتورها (Indicator Performance Attribution)
            </h3>
            <p style={{ fontSize: "0.78rem", color: "var(--text-secondary)", margin: "0.3rem 0 0" }}>
              محاسبه نرخ برد، دقت و سودآوری تجمعی هر یک از ۱۲ اندیکاتور برای وزن‌دهی بهینه‌تر در تصمیم‌گیری‌های بعدی
            </p>
          </div>

          <div className="card-panel" style={{ padding: 0, overflow: "hidden" }}>
            {attribution.length === 0 ? (
              <div style={{ padding: "3rem", textAlign: "center", color: "var(--text-muted)", fontSize: "0.85rem" }}>
                هنوز دیتای عملکردی اندیکاتورها محاسبه نشده است. با بسته شدن اولین معاملات، عملکرد هر اندیکاتور در این جدول ارزیابی می‌شود.
              </div>
            ) : (
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.82rem" }}>
                  <thead>
                    <tr style={{ color: "var(--text-muted)", textAlign: "right", borderBottom: "1px solid var(--border-subtle)", backgroundColor: "var(--bg-surface)" }}>
                      <th style={{ padding: "0.75rem 1rem" }}>نام اندیکاتور</th>
                      <th style={{ padding: "0.75rem 1rem" }}>تعداد کل سیگنال‌ها</th>
                      <th style={{ padding: "0.75rem 1rem" }}>سیگنال‌های سودده</th>
                      <th style={{ padding: "0.75rem 1rem" }}>سیگنال‌های زیان‌ده</th>
                      <th style={{ padding: "0.75rem 1rem" }}>دقت پیش‌بینی (Precision)</th>
                      <th style={{ padding: "0.75rem 1rem" }}>میانگین بازدهی (صعودی)</th>
                      <th style={{ padding: "0.75rem 1rem" }}>سودآوری تجمعی</th>
                    </tr>
                  </thead>
                  <tbody>
                    {attribution.map((ind) => {
                      const precColor = ind.precision >= 0.6 ? "var(--tse-green)" : ind.precision >= 0.4 ? "var(--tse-amber)" : "var(--tse-red)";
                      return (
                        <tr key={ind.indicator_name} style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                          <td style={{ padding: "0.85rem 1rem", fontWeight: 800, color: "var(--text-primary)" }}>{ind.display_name_fa}</td>
                          <td style={{ padding: "0.85rem 1rem" }} className="tabular-num">{ind.total_signals}</td>
                          <td style={{ padding: "0.85rem 1rem", color: "var(--tse-green)", fontWeight: 700 }} className="tabular-num">
                            {ind.profitable_signals}
                          </td>
                          <td style={{ padding: "0.85rem 1rem", color: "var(--tse-red)", fontWeight: 700 }} className="tabular-num">
                            {ind.loss_signals}
                          </td>
                          <td style={{ padding: "0.85rem 1rem" }}>
                            <span style={{ fontWeight: 800, color: precColor }} className="tabular-num">
                              {toPersianDigits((ind.precision * 100).toFixed(1))}٪
                            </span>
                          </td>
                          <td style={{ padding: "0.85rem 1rem", color: "var(--tse-green)", fontWeight: 700 }} className="tabular-num">
                            {ind.avg_return_when_bullish > 0 ? "+" : ""}{toPersianDigits(ind.avg_return_when_bullish.toFixed(2))}٪
                          </td>
                          <td
                            style={{
                              padding: "0.85rem 1rem",
                              fontWeight: 800,
                              color: ind.cumulative_pnl >= 0 ? "var(--tse-green)" : "var(--tse-red)",
                            }}
                            className="tabular-num"
                          >
                            {(ind.cumulative_pnl / 10).toLocaleString("fa-IR")} تومان
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── 8. Dedicated Trade Detail & Chart Modal ────────────────────── */}
      {selectedPosition && (
        <div
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
            alignItems: "center",
            justifyContent: "center",
            padding: "1.5rem",
          }}
          onClick={() => setSelectedPosition(null)}
        >
          <div
            style={{
              backgroundColor: "var(--bg-secondary)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "12px",
              width: "100%",
              maxWidth: "920px",
              maxHeight: "90vh",
              overflowY: "auto",
              display: "flex",
              flexDirection: "column",
              boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.5)",
            }}
            onClick={(e) => e.stopPropagation()}
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
                position: "sticky",
                top: 0,
                zIndex: 10,
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                <div
                  style={{
                    width: "40px",
                    height: "40px",
                    borderRadius: "8px",
                    backgroundColor: "rgba(59, 130, 246, 0.15)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "var(--tse-blue)",
                  }}
                >
                  <BarChart3 size={22} />
                </div>
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
                    <h3 style={{ fontSize: "1.25rem", fontWeight: 900, color: "var(--text-primary)", margin: 0 }}>
                      کالبدشکافی زنده موقعیت معاملاتی: {selectedPosition.symbol}
                    </h3>
                    <span
                      style={{
                        fontSize: "0.75rem",
                        padding: "2px 8px",
                        borderRadius: "4px",
                        backgroundColor: selectedPosition.unrealized_pnl >= 0 ? "var(--tse-green-subtle)" : "var(--tse-red-subtle)",
                        color: selectedPosition.unrealized_pnl >= 0 ? "var(--tse-green)" : "var(--tse-red)",
                        fontWeight: 800,
                      }}
                      className="tabular-num"
                    >
                      {selectedPosition.unrealized_pnl >= 0 ? "+" : ""}{selectedPosition.unrealized_pnl_pct}% سود باز لحظه‌ای
                    </span>
                  </div>
                  <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                    {positionDetail?.name_fa || selectedPosition.symbol} • صنعت: {positionDetail?.sector_name || "نامشخص"} • {selectedPosition.market_regime_fa || "رژیم نامشخص"}
                  </span>
                </div>
              </div>

              <button
                onClick={() => setSelectedPosition(null)}
                style={{
                  background: "transparent",
                  border: "none",
                  color: "var(--text-muted)",
                  cursor: "pointer",
                  padding: "4px",
                  borderRadius: "6px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <X size={20} />
              </button>
            </div>

            {/* Modal Body */}
            <div style={{ padding: "1.5rem", display: "flex", flexDirection: "column", gap: "1.25rem" }}>
              {/* Feedback Alert for Close Action */}
              {closeSuccessMsg && (
                <div
                  style={{
                    backgroundColor: "var(--tse-green-subtle)",
                    color: "var(--tse-green)",
                    border: "1px solid rgba(46, 160, 67, 0.4)",
                    padding: "0.75rem 1rem",
                    borderRadius: "6px",
                    fontWeight: 700,
                    fontSize: "0.85rem",
                    display: "flex",
                    alignItems: "center",
                    gap: "0.5rem",
                  }}
                >
                  <Check size={16} />
                  <span>{closeSuccessMsg}</span>
                </div>
              )}

              {/* ── Section 1: الان کجا هستیم؟ (Trade Trajectory Progress Gauge) ── */}
              <div className="card-panel" style={{ backgroundColor: "var(--bg-surface)", padding: "1.25rem", border: "1px solid var(--border-subtle)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.45rem" }}>
                    <Target size={18} color="var(--tse-blue)" />
                    <span style={{ fontWeight: 800, fontSize: "0.95rem", color: "var(--text-primary)" }}>
                      الان کجای مسیر معامله هستیم؟ (مسیر سوددهی تا اهداف قیمتی)
                    </span>
                  </div>
                  <span style={{ fontSize: "0.78rem", color: "var(--tse-green)", fontWeight: 800 }}>
                    {positionDetail?.progress_to_target_pct != null
                      ? `${positionDetail.progress_to_target_pct}٪ از مسیر رسیدن به تارگت اول طی شده است`
                      : "پیشرفت قابل محاسبه نیست"}
                  </span>
                </div>

                {/* Segmented Trajectory Track */}
                <div style={{ margin: "1.5rem 0 1rem", position: "relative" }}>
                  {/* Base Track Line */}
                  <div style={{ height: "8px", backgroundColor: "rgba(255,255,255,0.08)", borderRadius: "4px", width: "100%", position: "relative" }}>
                    {/* Progress Fill to Current Price */}
                    <div
                      style={{
                        height: "100%",
                        width: `${Math.min(100, Math.max(0, positionDetail?.progress_to_target_pct ?? 0))}%`,
                        backgroundColor: "var(--tse-green)",
                        borderRadius: "4px",
                        boxShadow: "0 0 10px rgba(34, 197, 94, 0.5)",
                      }}
                    />
                  </div>

                  {/* 4 Checkpoint Badges */}
                  <div style={{ display: "flex", justifyContent: "space-between", marginTop: "0.75rem", fontSize: "0.76rem" }}>
                    {/* 1. Stop Loss */}
                    <div style={{ textAlign: "right" }}>
                      <div style={{ color: "var(--tse-red)", fontWeight: 800 }}>حد ضرر (Stop Loss)</div>
                      <div style={{ color: "var(--tse-red)", fontWeight: 700, fontSize: "0.85rem" }} className="tabular-num">
                        {selectedPosition.stop_loss?.toLocaleString("fa-IR")} ﷼
                      </div>
                      <div style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>
                        {selectedPosition.distance_to_stop_pct}% فاصله
                      </div>
                    </div>

                    {/* 2. Entry Price */}
                    <div style={{ textAlign: "center" }}>
                      <div style={{ color: "var(--tse-blue)", fontWeight: 800 }}>قیمت ورود به معامله</div>
                      <div style={{ color: "var(--text-primary)", fontWeight: 800, fontSize: "0.85rem" }} className="tabular-num">
                        {selectedPosition.average_entry_price?.toLocaleString("fa-IR")} ﷼
                      </div>
                      <div style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>مبنای خرید</div>
                    </div>

                    {/* 3. Live Current Price Marker */}
                    <div style={{ textAlign: "center", backgroundColor: "rgba(34, 197, 94, 0.12)", padding: "4px 8px", borderRadius: "6px", border: "1px solid rgba(34, 197, 94, 0.3)" }}>
                      <div style={{ color: "var(--tse-green)", fontWeight: 900, display: "flex", alignItems: "center", gap: "3px" }}>
                        <span style={{ width: 6, height: 6, borderRadius: "50%", backgroundColor: "var(--tse-green)" }} />
                        الان اینجاییم (فعلی)
                      </div>
                      <div style={{ color: "var(--tse-green)", fontWeight: 900, fontSize: "0.95rem" }} className="tabular-num">
                        {selectedPosition.current_price?.toLocaleString("fa-IR")} ﷼
                      </div>
                      <div style={{ fontSize: "0.72rem", color: "var(--tse-green)", fontWeight: 700 }}>
                        {selectedPosition.unrealized_pnl >= 0 ? "+" : ""}{selectedPosition.unrealized_pnl_pct}% سود لحظه‌ای
                      </div>
                    </div>

                    {/* 4. Target 1 */}
                    <div style={{ textAlign: "left" }}>
                      <div style={{ color: "var(--tse-green)", fontWeight: 800 }}>تارگت سود اول (هدف اصلی)</div>
                      <div style={{ color: "var(--tse-green)", fontWeight: 800, fontSize: "0.85rem" }} className="tabular-num">
                        {selectedPosition.target_price?.toLocaleString("fa-IR")} ﷼
                      </div>
                      <div style={{ fontSize: "0.7rem", color: "var(--tse-green)", fontWeight: 700 }}>
                        {positionDetail?.distance_to_target_pct ? `+${positionDetail.distance_to_target_pct}٪ تا هدف` : "+۶.۴٪ مانده"}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Key Numbers Grid */}
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: "0.6rem", marginTop: "1rem" }}>
                  <div style={{ padding: "0.6rem 0.8rem", backgroundColor: "var(--bg-secondary)", borderRadius: "6px" }}>
                    <div style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>فاصله تا تارگت سود</div>
                    <div style={{ fontWeight: 800, color: "var(--tse-green)", fontSize: "0.95rem", marginTop: "2px" }} className="tabular-num">
                      +{positionDetail?.distance_to_target_pct || selectedPosition.distance_to_target_pct}% ({positionDetail?.distance_to_target_rials ? `+${positionDetail.distance_to_target_rials.toLocaleString("fa-IR")} ﷼` : ""})
                    </div>
                  </div>

                  <div style={{ padding: "0.6rem 0.8rem", backgroundColor: "var(--bg-secondary)", borderRadius: "6px" }}>
                    <div style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>فاصله امن تا حد ضرر</div>
                    <div style={{ fontWeight: 800, color: "var(--tse-red)", fontSize: "0.95rem", marginTop: "2px" }} className="tabular-num">
                      {selectedPosition.distance_to_stop_pct}% ({positionDetail?.distance_to_stop_rials ? `${positionDetail.distance_to_stop_rials.toLocaleString("fa-IR")} ﷼` : ""})
                    </div>
                  </div>

                  <div style={{ padding: "0.6rem 0.8rem", backgroundColor: "var(--bg-secondary)", borderRadius: "6px" }}>
                    <div style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>سود باز لحظه‌ای</div>
                    <div style={{ fontWeight: 900, color: selectedPosition.unrealized_pnl >= 0 ? "var(--tse-green)" : "var(--tse-red)", fontSize: "0.95rem", marginTop: "2px" }} className="tabular-num">
                      {(selectedPosition.unrealized_pnl / 10).toLocaleString("fa-IR")} تومان
                    </div>
                  </div>

                  <div style={{ padding: "0.6rem 0.8rem", backgroundColor: "var(--bg-secondary)", borderRadius: "6px" }}>
                    <div style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>سرمایه وارد شده</div>
                    <div style={{ fontWeight: 800, color: "var(--text-primary)", fontSize: "0.95rem", marginTop: "2px" }} className="tabular-num">
                      {(selectedPosition.total_invested_tomans / 1_000_000).toFixed(1)} میلیون تومان
                    </div>
                  </div>
                </div>
              </div>

              {/* ── Section 2: نمودار کندل‌استیک و سطوح قیمتی ── */}
              <div className="card-panel" style={{ backgroundColor: "var(--bg-surface)", padding: "1.25rem", border: "1px solid var(--border-subtle)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.45rem" }}>
                    <BarChart3 size={18} color="var(--tse-green)" />
                    <span style={{ fontWeight: 800, fontSize: "0.95rem", color: "var(--text-primary)" }}>
                      نمودار روند قیمت سهم و سطوح معاملاتی (Price Action & Targets)
                    </span>
                  </div>
                  <div style={{ display: "flex", gap: "0.75rem", fontSize: "0.72rem" }}>
                    <span style={{ color: "var(--tse-green)", display: "flex", alignItems: "center", gap: "4px" }}>
                      <span style={{ width: 8, height: 2, backgroundColor: "var(--tse-green)" }} /> تارگت ۱
                    </span>
                    <span style={{ color: "var(--tse-blue)", display: "flex", alignItems: "center", gap: "4px" }}>
                      <span style={{ width: 8, height: 2, backgroundColor: "var(--tse-blue)" }} /> قیمت ورود
                    </span>
                    <span style={{ color: "var(--tse-red)", display: "flex", alignItems: "center", gap: "4px" }}>
                      <span style={{ width: 8, height: 2, backgroundColor: "var(--tse-red)" }} /> حد ضرر
                    </span>
                  </div>
                </div>

                {/* SVG Visual Candle Bar Chart */}
                <div style={{ height: "180px", width: "100%", display: "flex", alignItems: "flex-end", gap: "8px", padding: "1rem 0", position: "relative" }}>
                  {(positionDetail?.candles || []).map((c: any, idx: number) => {
                    const candlePrices = (positionDetail?.candles || [])
                      .flatMap((bar: any) => [bar.low, bar.high, bar.open, bar.close])
                      .filter((price: unknown): price is number => typeof price === "number" && Number.isFinite(price));
                    const minPrice = candlePrices.length > 0 ? Math.min(...candlePrices) : c.close;
                    const maxPrice = candlePrices.length > 0 ? Math.max(...candlePrices) : c.close;
                    const priceRange = Math.max(1, maxPrice - minPrice);
                    const heightPct = Math.max(1, Math.min(100, ((c.close - minPrice) / priceRange) * 100));
                    const isUp = c.close >= c.open;

                    return (
                      <div
                        key={idx}
                        style={{
                          flex: 1,
                          display: "flex",
                          flexDirection: "column",
                          alignItems: "center",
                          height: "100%",
                          justifyContent: "flex-end",
                        }}
                        title={`تاریخ: ${c.date} | قیمت بسته شدن: ${c.close.toLocaleString("fa-IR")} ﷼`}
                      >
                        <div
                          style={{
                            width: "100%",
                            maxWidth: "16px",
                            height: `${heightPct}%`,
                            backgroundColor: isUp ? "var(--tse-green)" : "var(--tse-red)",
                            borderRadius: "2px",
                            opacity: 0.9,
                          }}
                        />
                        <span style={{ fontSize: "0.6rem", color: "var(--text-muted)", marginTop: "4px", whiteSpace: "nowrap" }}>
                          {c.date?.split("/")[2] || idx}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* ── Section 3: دلایل ورود و آرای استراتژی‌ها ── */}
              <div className="card-panel" style={{ backgroundColor: "var(--bg-surface)", padding: "1.25rem", border: "1px solid var(--border-subtle)" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "0.45rem", marginBottom: "0.75rem" }}>
                  <Brain size={18} color="var(--tse-blue)" />
                  <span style={{ fontWeight: 800, fontSize: "0.95rem", color: "var(--text-primary)" }}>
                    دلایل ورود هوش مصنوعی و آرای استراتژی‌های کمّی بازار
                  </span>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "0.6rem" }}>
                  {(positionDetail?.strategy_votes || []).map((sv: any, idx: number) => (
                    <div
                      key={idx}
                      style={{
                        backgroundColor: "var(--bg-secondary)",
                        padding: "0.75rem 0.85rem",
                        borderRadius: "6px",
                        border: "1px solid var(--border-subtle)",
                        display: "flex",
                        flexDirection: "column",
                        gap: "0.25rem",
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <span style={{ fontWeight: 700, fontSize: "0.84rem", color: "var(--text-primary)" }}>
                          {sv.strategy_fa || sv.strategy}
                        </span>
                        <span style={{ fontSize: "0.72rem", color: "var(--tse-blue)", fontWeight: 800 }} className="tabular-num">
                          قدرت رأی: {sv.vote != null ? `${Math.round(sv.vote * 100)}٪` : "—"}
                        </span>
                      </div>
                      <span style={{ fontSize: "0.75rem", color: "var(--text-secondary)", lineHeight: 1.4 }}>
                        {sv.reason_fa}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* ── Section 4: AI Recommendation & Action Buttons ── */}
              <div
                style={{
                  backgroundColor: "rgba(59, 130, 246, 0.08)",
                  border: "1px solid rgba(59, 130, 246, 0.25)",
                  borderRadius: "8px",
                  padding: "1rem 1.25rem",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  flexWrap: "wrap",
                  gap: "1rem",
                }}
              >
                <div style={{ flex: 1, minWidth: "260px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.4rem", color: "var(--tse-blue)", fontWeight: 800, fontSize: "0.9rem" }}>
                    <Sparkles size={16} />
                    <span>توصیه معاملاتی سیستم:</span>
                  </div>
                  <p style={{ fontSize: "0.82rem", color: "var(--text-primary)", margin: "0.3rem 0 0", lineHeight: 1.5 }}>
                    {positionDetail?.ai_summary_fa || "جمع‌بندی تحلیلی معتبری برای این موقعیت ثبت نشده است."}
                  </p>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap" }}>
                  {/* Scale-In Button */}
                  <button
                    onClick={() => handleScaleInPosition(selectedPosition.id)}
                    disabled={actionLoadingId === selectedPosition.id}
                    style={{
                      backgroundColor: "rgba(34, 197, 94, 0.2)",
                      color: "var(--tse-green)",
                      border: "1px solid var(--tse-green)",
                      padding: "0.6rem 1rem",
                      borderRadius: "6px",
                      fontWeight: 800,
                      fontSize: "0.82rem",
                      cursor: actionLoadingId === selectedPosition.id ? "not-allowed" : "pointer",
                      display: "flex",
                      alignItems: "center",
                      gap: "0.4rem",
                      fontFamily: "inherit",
                    }}
                    title="افزایش پله‌ای سهم برنده (با رعایت سقف ۱۰٪ مدیریت سرمایه)"
                  >
                    <span>➕ افزایش پله‌ای سهم (+ ۳٪)</span>
                  </button>

                  {/* Trim 50% Button */}
                  <button
                    onClick={() => handleTrimPosition(selectedPosition.id)}
                    disabled={actionLoadingId === selectedPosition.id}
                    style={{
                      backgroundColor: "rgba(245, 158, 11, 0.2)",
                      color: "var(--tse-amber)",
                      border: "1px solid var(--tse-amber)",
                      padding: "0.6rem 1rem",
                      borderRadius: "6px",
                      fontWeight: 800,
                      fontSize: "0.82rem",
                      cursor: actionLoadingId === selectedPosition.id ? "not-allowed" : "pointer",
                      display: "flex",
                      alignItems: "center",
                      gap: "0.4rem",
                      fontFamily: "inherit",
                    }}
                    title="فروش نیمی از حجم جهت سیو سود و کاهش ریسک"
                  >
                    <span>✂️ کاهش پله‌ای (- ۵۰٪ سیو سود)</span>
                  </button>

                  {/* Manual Close Position Button */}
                  <button
                    onClick={() => handleManualClosePosition(selectedPosition.id)}
                    disabled={closingPositionId === selectedPosition.id}
                    style={{
                      backgroundColor: "var(--tse-red)",
                      color: "#fff",
                      border: "none",
                      padding: "0.6rem 1rem",
                      borderRadius: "6px",
                      fontWeight: 800,
                      fontSize: "0.82rem",
                      cursor: closingPositionId === selectedPosition.id ? "not-allowed" : "pointer",
                      display: "flex",
                      alignItems: "center",
                      gap: "0.4rem",
                      fontFamily: "inherit",
                      boxShadow: "0 4px 12px rgba(239, 68, 68, 0.3)",
                    }}
                  >
                    <LogOut size={15} />
                    <span>{closingPositionId === selectedPosition.id ? "در حال بستن..." : "فروش کامل سهم"}</span>
                  </button>

                  <button
                    onClick={() => setSelectedPosition(null)}
                    style={{
                      backgroundColor: "transparent",
                      color: "var(--text-secondary)",
                      border: "1px solid var(--border-subtle)",
                      padding: "0.6rem 0.85rem",
                      borderRadius: "6px",
                      fontWeight: 600,
                      fontSize: "0.82rem",
                      cursor: "pointer",
                      fontFamily: "inherit",
                    }}
                  >
                    بستن
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
