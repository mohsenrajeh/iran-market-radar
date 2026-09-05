"use client";
import React, { useState, useEffect, useCallback } from "react";
import { Header } from "../components/Header";
import { Sidebar, NavTab } from "../components/Sidebar";
import { OverviewView } from "../components/OverviewView";
import { OpportunitiesView } from "../components/OpportunitiesView";
import { OpenPositionsView } from "../components/OpenPositionsView";
import { FundamentalView } from "../components/FundamentalView";
import { TradingLabView } from "../components/TradingLabView";
import { HealthSettingsView } from "../components/HealthSettingsView";
import { UnifiedSymbolModal } from "../components/UnifiedSymbolModal";
import { LoginModal } from "../components/LoginModal";
import { AlertCircle, RefreshCw, X } from "lucide-react";

async function responseErrorMessage(response: Response, fallback: string): Promise<string> {
  try {
    const payload = await response.json();
    if (typeof payload?.detail === "string") return payload.detail;
    if (typeof payload?.detail?.message === "string") return payload.detail.message;
  } catch {
    // A non-JSON upstream error is reduced to a safe user-facing message.
  }
  return fallback;
}

export default function DashboardPage() {
  const [activeTab, setActiveTab] = useState<NavTab>("overview");
  // Lazy-mount: tracks which tabs have been rendered at least once so they persist (display:none)
  const [visitedTabs, setVisitedTabs] = useState<Set<NavTab>>(() => new Set<NavTab>(["overview"]));
  const [selectedSymbolForModal, setSelectedSymbolForModal] = useState<string | null>(null);

  // Tab Persistence across F5 and page reloads
  useEffect(() => {
    const hash = typeof window !== "undefined" ? window.location.hash.replace("#", "") : "";
    const savedTab = typeof window !== "undefined" ? localStorage.getItem("radar_active_tab") : null;
    const validTabs: NavTab[] = ["overview", "opportunities", "open_positions", "fundamental", "trading_lab", "health_settings"];
    let targetTab: NavTab = "overview";
    if (hash && validTabs.includes(hash as NavTab)) {
      targetTab = hash as NavTab;
    } else if (savedTab && validTabs.includes(savedTab as NavTab)) {
      targetTab = savedTab as NavTab;
    }
    setActiveTab(targetTab);
    setVisitedTabs((prev) => new Set([...Array.from(prev), targetTab]));
  }, []);

  useEffect(() => {
    const requireOwnerLogin = () => {
      setIsAuthenticated(false);
      setCurrentUser("");
      setRefreshError("نشست شما منقضی شده است. برای ادامه، دوباره به‌عنوان مالک سامانه وارد شوید.");
    };
    window.addEventListener("radar:auth-required", requireOwnerLogin);
    return () => window.removeEventListener("radar:auth-required", requireOwnerLogin);
  }, []);

  // Ensure activeTab is always marked as visited so it renders immediately
  useEffect(() => {
    setVisitedTabs((prev) => {
      if (prev.has(activeTab)) return prev;
      const next = new Set(prev);
      next.add(activeTab);
      return next;
    });
  }, [activeTab]);

  const handleSelectTab = (tab: NavTab) => {
    setVisitedTabs((prev) => { const s = new Set(prev); s.add(tab); return s; });
    setActiveTab(tab);
    if (typeof window !== "undefined") {
      localStorage.setItem("radar_active_tab", tab);
      window.history.replaceState(null, "", `#${tab}`);
    }
  };

  // Authentication state is derived only from the server-side HttpOnly session.
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [authChecked, setAuthChecked] = useState<boolean>(false);
  const [currentUser, setCurrentUser] = useState<string>("");

  useEffect(() => {
    fetch("/api/v1/auth/me", { credentials: "same-origin", cache: "no-store" })
      .then((res) => res.json())
      .then((profile) => {
        setIsAuthenticated(Boolean(profile.authenticated));
        setCurrentUser(profile.username || "");
      })
      .catch(() => {
        setIsAuthenticated(false);
        setCurrentUser("");
      })
      .finally(() => setAuthChecked(true));
  }, []);

  // Global State Data
  const [overview, setOverview] = useState<any | null>(null);
  const [opportunities, setOpportunities] = useState<any[]>([]);
  const [referenceSymbols, setReferenceSymbols] = useState<any>({ rows: [], meta: {}, trade_eligible: false });
  const [sectors, setSectors] = useState<any[]>([]);
  const [portfolio, setPortfolio] = useState<any | null>(null);
  const [openPositionsCount, setOpenPositionsCount] = useState<number>(0);
  const [loading, setLoading] = useState(true);

  // Unified Global Refresh State & Error Handling
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastUpdatedTime, setLastUpdatedTime] = useState<string>("");
  const [refreshToast, setRefreshToast] = useState<string | null>(null);
  const [refreshError, setRefreshError] = useState<string | null>(null);
  const [lastRefreshResult, setLastRefreshResult] = useState<{
    message: string;
    timestamp: string;
    tradeEligible: boolean;
  } | null>(null);

  // Auto-Refresh & Market Session State
  const [isAutoRefreshEnabled, setIsAutoRefreshEnabled] = useState<boolean>(true);
  const [cadenceSeconds, setCadenceSeconds] = useState<number>(60);
  const [marketSession, setMarketSession] = useState<any | null>(null);

  useEffect(() => {
    const savedAuto = typeof window !== "undefined" ? localStorage.getItem("radar_auto_refresh") : null;
    if (savedAuto === "false") {
      setIsAutoRefreshEnabled(false);
    }
  }, []);

  const toggleAutoRefresh = () => {
    setIsAutoRefreshEnabled((prev) => {
      const nextVal = !prev;
      if (typeof window !== "undefined") {
        localStorage.setItem("radar_auto_refresh", String(nextVal));
      }
      return nextVal;
    });
  };

  const fetchGlobalData = useCallback(async (manual = false) => {
    if (manual) {
      setIsRefreshing(true);
      setRefreshError(null);
    }
    try {
      if (manual) {
        // Advance market session, compute features, re-score, and execute auto-trader
        const syncRes = await fetch("/api/v1/market/sync-all", { method: "POST", credentials: "same-origin" });
        if (syncRes.status === 401) {
          window.dispatchEvent(new Event("radar:auth-required"));
          throw new Error("نشست شما منقضی شده است؛ لطفاً دوباره وارد شوید.");
        }
        if (!syncRes.ok) {
          throw new Error(await responseErrorMessage(syncRes, `همگام‌سازی رسمی با خطای ${syncRes.status} متوقف شد.`));
        }
        const syncPayload = await syncRes.json();
        const resultMessage = syncPayload?.message || "همگام‌سازی انجام شد؛ هیچ معامله‌ای در این مرحله اجرا نشد.";
        setRefreshToast(resultMessage);
        setLastRefreshResult({
          message: resultMessage,
          timestamp: syncPayload?.timestamp_jalali || "زمان ثبت نشده",
          tradeEligible: Boolean(syncPayload?.sync_stats?.trade_eligible),
        });
        setTimeout(() => setRefreshToast(null), 4500);
      }

      const [resOverview, resOpps, resSectors, resReferenceSymbols] = await Promise.all([
        fetch("/api/v1/market/overview", { credentials: "same-origin", cache: "no-store" }),
        fetch("/api/v1/opportunities?actionable_only=false&min_score=0", { credentials: "same-origin", cache: "no-store" }),
        fetch("/api/v1/market/sectors", { credentials: "same-origin", cache: "no-store" }),
        fetch("/api/v1/market/reference-symbols?per_page=2000", { credentials: "same-origin", cache: "no-store" }),
      ]);

      const publicResponses = [resOverview, resOpps, resSectors, resReferenceSymbols];
      const failed = publicResponses.find((response) => !response.ok);
      if (failed) {
        throw new Error(await responseErrorMessage(failed, `به‌روزرسانی ناقص ماند (HTTP ${failed.status}).`));
      }

      setOverview(await resOverview.json());
      setOpportunities(await resOpps.json());
      setSectors(await resSectors.json());
      setReferenceSymbols(await resReferenceSymbols.json());
      // Private portfolio expiry must never suppress fresh public market data.
      const resPort = await fetch("/api/v1/paper/portfolio", { credentials: "same-origin", cache: "no-store" });
      if (resPort.ok) {
        const portData = await resPort.json();
        setPortfolio(portData);
        const openCount = (portData.positions || []).filter((p: any) => p.is_open).length;
        setOpenPositionsCount(openCount);
      } else if (resPort.status === 401) {
        window.dispatchEvent(new Event("radar:auth-required"));
        setPortfolio(null);
        setOpenPositionsCount(0);
      } else {
        throw new Error(await responseErrorMessage(resPort, `دریافت پرتفوی ناقص ماند (HTTP ${resPort.status}).`));
      }
      setRefreshError(null);

      const now = new Date();
      const timeStr = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}:${String(now.getSeconds()).padStart(2, "0")}`;
      setLastUpdatedTime(timeStr);
    } catch (e: any) {
      console.error("Global refresh error:", e);
      setRefreshError(e.message || "به‌روزرسانی کامل نشد؛ اتصال منبع داده و نشست مالک را بررسی کنید.");
    } finally {
      if (manual) setIsRefreshing(false);
      setLoading(false);
    }
  }, []);

  // Session-aware recursive timer. Outside market it performs one local read,
  // then sleeps exactly until the next open; it does not poll every minute.
  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    const run = async (initial: boolean) => {
      let session: any = null;
      try {
        const response = await fetch("/api/v1/market/session-state", { cache: "no-store" });
        if (response.ok) session = await response.json();
      } catch {
        // Public/local dashboard loading still works if the clock route fails.
      }
      if (cancelled) return;
      if (session) {
        setMarketSession(session);
        setCadenceSeconds(Number(session.cadence_seconds || 60));
      }
      if (initial || session?.upstream_requests_allowed) {
        await fetchGlobalData(false);
      }
      if (!cancelled && isAutoRefreshEnabled) {
        const delaySeconds = Math.max(5, Number(session?.cadence_seconds || 60));
        timer = setTimeout(() => run(false), delaySeconds * 1000);
      }
    };

    run(true);
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [isAutoRefreshEnabled, fetchGlobalData]);

  const getTabTitle = (tab: NavTab) => {
    switch (tab) {
      case "overview": return "داشبورد اجرایی و نمای تحلیلی بازار بورس و فرابورس";
      case "opportunities": return "دیده‌بان جامع، فیلتر دسته‌بندی‌شده و رادار سهام";
      case "open_positions": return "میزکار تخصصی معاملات باز، رصد سود/زیان و مدیریت سرمایه";
      case "fundamental": return "مرکز تحلیل بنیادی، نسبت‌های مالی، ارزش‌گذاری و اطلاعیه‌های کدال";
      case "trading_lab": return "مرکز بهبود معاملات: ثبت نتیجه، تحلیل ضرر و تنظیم کنترل‌شده";
      case "health_settings": return "سلامت خط دریافت داده، پایش وب‌سرویس و تنظیمات سامانه";
      default: return "رادار بازار سرمایه ایران";
    }
  };

  const handleOpenSymbolModal = (symOrOpp: any) => {
    if (typeof symOrOpp === "string") {
      setSelectedSymbolForModal(symOrOpp);
    } else if (symOrOpp && symOrOpp.symbol) {
      setSelectedSymbolForModal(symOrOpp.symbol);
    }
  };

  if (!authChecked) {
    return <div style={{ minHeight: "100vh", background: "var(--bg-primary)" }} />;
  }

  return (
    <div className="app-shell" style={{ display: "flex", minHeight: "100vh", backgroundColor: "var(--bg-primary)" }}>
      {/* 1. Right Navigation Sidebar */}
      <Sidebar
        activeTab={activeTab}
        onSelectTab={handleSelectTab}
        opportunityCount={opportunities.length}
        openPositionsCount={openPositionsCount}
        ownerName={currentUser}
      />

      {/* 2. Main Content Area */}
      <div className="app-main" style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        {/* Top Status Header with Single Global Refresh and Live Search */}
        <Header
          currentViewTitle={getTabTitle(activeTab)}
          regime={overview?.market_regime || "unknown"}
          regimeFa={overview?.market_regime_fa || "نامشخص — داده معتبر دریافت نشده"}
          jalaliTime={overview?.current_time_jalali || ""}
          tradingMode={overview?.trading_mode || "paper"}
          isRefreshing={isRefreshing}
          onRefreshAll={() => fetchGlobalData(true)}
          lastUpdatedTime={lastUpdatedTime}
          onSelectSymbol={handleOpenSymbolModal}
          isAutoRefreshEnabled={isAutoRefreshEnabled}
          onToggleAutoRefresh={toggleAutoRefresh}
          cadenceSeconds={cadenceSeconds}
          marketSession={marketSession}
          lastMarketUpdateAt={referenceSymbols?.meta?.last_success_at}
        />

        {lastRefreshResult && (
          <div
            role="status"
            style={{
              margin: "0.75rem 1.75rem 0",
              padding: "0.65rem 0.9rem",
              borderRadius: "8px",
              border: `1px solid ${lastRefreshResult.tradeEligible ? "rgba(34,197,94,0.45)" : "rgba(245,158,11,0.45)"}`,
              backgroundColor: lastRefreshResult.tradeEligible ? "rgba(34,197,94,0.10)" : "rgba(245,158,11,0.10)",
              color: lastRefreshResult.tradeEligible ? "var(--tse-green)" : "var(--tse-amber)",
              fontSize: "0.8rem",
              fontWeight: 700,
            }}
          >
            آخرین نتیجه به‌روزرسانی ({lastRefreshResult.timestamp}): {lastRefreshResult.message}
          </div>
        )}

        {/* Live Refresh Toast Notification */}
        {refreshToast && (
          <div
            style={{
              position: "fixed",
              top: "70px",
              left: "50%",
              transform: "translateX(-50%)",
              backgroundColor: "#166534",
              color: "#f0fdf4",
              padding: "0.6rem 1.25rem",
              borderRadius: "8px",
              boxShadow: "0 10px 25px rgba(0,0,0,0.5)",
              zIndex: 99999,
              fontWeight: 800,
              fontSize: "0.85rem",
              border: "1px solid #22c55e",
              animation: "fadeIn 0.2s ease-in-out",
            }}
          >
            {refreshToast}
          </div>
        )}

        {/* Live Error Banner if Market Refresh Fails */}
        {refreshError && (
          <div
            style={{
              position: "fixed",
              top: "70px",
              left: "50%",
              transform: "translateX(-50%)",
              backgroundColor: "#991b1b",
              color: "#fef2f2",
              padding: "0.75rem 1.5rem",
              borderRadius: "8px",
              boxShadow: "0 10px 30px rgba(0,0,0,0.7)",
              zIndex: 99999,
              fontWeight: 700,
              fontSize: "0.88rem",
              border: "1px solid #ef4444",
              display: "flex",
              alignItems: "center",
              gap: "0.75rem",
            }}
          >
            <AlertCircle size={20} color="#fca5a5" />
            <div style={{ flex: 1 }}>{refreshError}</div>
            <button
              onClick={() => fetchGlobalData(true)}
              style={{
                backgroundColor: "#ef4444",
                color: "#fff",
                border: "none",
                padding: "0.35rem 0.75rem",
                borderRadius: "4px",
                fontSize: "0.75rem",
                fontWeight: 800,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: "0.3rem",
                fontFamily: "inherit",
              }}
            >
              <RefreshCw size={12} />
              <span>تلاش مجدد</span>
            </button>
            <button
              onClick={() => setRefreshError(null)}
              style={{
                background: "transparent",
                border: "none",
                color: "#fca5a5",
                cursor: "pointer",
                padding: "2px",
              }}
            >
              <X size={16} />
            </button>
          </div>
        )}

        {/* View Router — Stable DOM tree: display:none preserves scroll pos & component state */}
        <main style={{ padding: "0", flex: 1, overflowY: "auto" }}>
          {/* Overview — always mounted (default tab) */}
          <div className="app-view" style={{ padding: "1.5rem 1.75rem", display: activeTab === "overview" ? "block" : "none" }}>
            <OverviewView
              overviewData={overview}
              portfolioData={portfolio}
              topOpportunities={opportunities.filter((item: any) => item.actionable === true)}
              sectors={sectors}
              onSelectOpportunity={handleOpenSymbolModal}
              onSelectSymbol={handleOpenSymbolModal}
              onNavigateTab={handleSelectTab}
            />
          </div>

          {/* Opportunities — lazy-mounted on first visit */}
          {(visitedTabs.has("opportunities") || activeTab === "opportunities") && (
            <div className="app-view" style={{ padding: "1.5rem 1.75rem", display: activeTab === "opportunities" ? "block" : "none" }}>
              <OpportunitiesView
                opportunities={opportunities}
                referenceSymbols={referenceSymbols}
                onSelectOpportunity={handleOpenSymbolModal}
                onSelectSymbol={handleOpenSymbolModal}
              />
            </div>
          )}

          {/* Open Positions — lazy-mounted on first visit */}
          {(visitedTabs.has("open_positions") || activeTab === "open_positions") && (
            <div className="app-view" style={{ display: activeTab === "open_positions" ? "block" : "none" }}>
              <OpenPositionsView
                initialPortfolio={portfolio}
                onSelectSymbol={handleOpenSymbolModal}
              />
            </div>
          )}

          {/* Fundamental — lazy-mounted on first visit */}
          {(visitedTabs.has("fundamental") || activeTab === "fundamental") && (
            <div className="app-view" style={{ padding: "1.5rem 1.75rem", display: activeTab === "fundamental" ? "block" : "none" }}>
              <FundamentalView
                onSelectSymbol={handleOpenSymbolModal}
              />
            </div>
          )}

          {/* Trading Lab — lazy-mounted on first visit */}
          {(visitedTabs.has("trading_lab") || activeTab === "trading_lab") && (
            <div className="app-view" style={{ padding: "1.5rem 1.75rem", display: activeTab === "trading_lab" ? "block" : "none" }}>
              <TradingLabView />
            </div>
          )}

          {/* Health & Settings — lazy-mounted on first visit */}
          {(visitedTabs.has("health_settings") || activeTab === "health_settings") && (
            <div className="app-view" style={{ padding: "1.5rem 1.75rem", display: activeTab === "health_settings" ? "block" : "none" }}>
              <HealthSettingsView />
            </div>
          )}
        </main>
      </div>

      {/* ── 3. Global 360° Unified Stock Analysis Modal ─────────────────── */}
      <UnifiedSymbolModal
        symbol={selectedSymbolForModal}
        onClose={() => setSelectedSymbolForModal(null)}
        onOrderPlaced={() => fetchGlobalData(false)}
      />

      {/* ── 4. Persistent 30-Day Auth Modal ─────────────────────────────── */}
      {!isAuthenticated && (
        <LoginModal
          onLoginSuccess={(user) => {
            setIsAuthenticated(true);
            setCurrentUser(user);
            setRefreshError(null);
            fetchGlobalData(false);
          }}
        />
      )}
    </div>
  );
}
