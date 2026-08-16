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

  // Authentication State (Persistent 30 days)
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(true);
  const [currentUser, setCurrentUser] = useState<string>("admin");

  useEffect(() => {
    // Check saved session
    const token = typeof window !== "undefined" ? localStorage.getItem("radar_auth_token") : null;
    if (!token) {
      // Default to authenticated for seamless local paper-trading access
      setIsAuthenticated(true);
      setCurrentUser("admin");
    } else {
      setIsAuthenticated(true);
      const savedUser = localStorage.getItem("radar_auth_user") || "admin";
      setCurrentUser(savedUser);
    }
  }, []);

  // Global State Data
  const [overview, setOverview] = useState<any | null>(null);
  const [opportunities, setOpportunities] = useState<any[]>([]);
  const [sectors, setSectors] = useState<any[]>([]);
  const [portfolio, setPortfolio] = useState<any | null>(null);
  const [openPositionsCount, setOpenPositionsCount] = useState<number>(0);
  const [loading, setLoading] = useState(true);

  // Unified Global Refresh State & Error Handling
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastUpdatedTime, setLastUpdatedTime] = useState<string>("");
  const [refreshToast, setRefreshToast] = useState<string | null>(null);
  const [refreshError, setRefreshError] = useState<string | null>(null);

  // Auto-Refresh & Market Session State
  const [isAutoRefreshEnabled, setIsAutoRefreshEnabled] = useState<boolean>(true);
  const [cadenceSeconds, setCadenceSeconds] = useState<number>(10);

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
        const syncRes = await fetch("/api/v1/market/sync-all", { method: "POST" });
        if (!syncRes.ok) {
          const errText = await syncRes.text();
          throw new Error(`خطای سرور (${syncRes.status}): ${errText || "عدم دریافت پاسخ معتبر از هسته پردازش بورس"}`);
        }
        setRefreshToast("✅ بازار یک گام به جلو حرکت کرد: قیمت‌ها بروزرسانی شدند و سود/زیان محاسبه گردید.");
        setTimeout(() => setRefreshToast(null), 4500);
      }

      const [resOverview, resOpps, resSectors, resPort] = await Promise.all([
        fetch("/api/v1/market/overview"),
        fetch("/api/v1/opportunities?actionable_only=false"),
        fetch("/api/v1/market/sectors"),
        fetch("/api/v1/paper/portfolio"),
      ]);

      if (!resOverview.ok && manual) {
        throw new Error("خطا در دریافت وضعیت شاخص‌های کل بازار.");
      }

      if (resOverview.ok) setOverview(await resOverview.json());
      if (resOpps.ok) setOpportunities(await resOpps.json());
      if (resSectors.ok) setSectors(await resSectors.json());
      if (resPort.ok) {
        const portData = await resPort.json();
        setPortfolio(portData);
        const openCount = (portData.positions || []).filter((p: any) => p.is_open).length;
        setOpenPositionsCount(openCount);
      }

      const now = new Date();
      const timeStr = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}:${String(now.getSeconds()).padStart(2, "0")}`;
      setLastUpdatedTime(timeStr);
    } catch (e: any) {
      console.error("Global refresh error:", e);
      if (manual) {
        setRefreshError(e.message || "خطا در برقراری ارتباط با وب‌سرویس بورس و پایگاه داده. لطفاً اتصال را بررسی نمایید.");
      }
    } finally {
      if (manual) setIsRefreshing(false);
      setLoading(false);
    }
  }, []);

  // Fetch recommended cadence on mount & periodic check
  useEffect(() => {
    fetch("/api/v1/market/session-state")
      .then((r) => r.json())
      .then((data) => {
        if (data && data.cadence_seconds) {
          setCadenceSeconds(data.cadence_seconds);
        }
      })
      .catch(() => {});
  }, []);

  // Initial Load + Auto Adaptive Periodic Refresh (Silent background updates without unmounting DOM)
  useEffect(() => {
    fetchGlobalData(false);

    if (!isAutoRefreshEnabled) return;

    const intervalMs = Math.max(5000, cadenceSeconds * 1000);
    const timer = setInterval(() => {
      fetchGlobalData(false);
    }, intervalMs);

    return () => clearInterval(timer);
  }, [isAutoRefreshEnabled, cadenceSeconds, fetchGlobalData]);

  const getTabTitle = (tab: NavTab) => {
    switch (tab) {
      case "overview": return "داشبورد اجرایی و نمای تحلیلی بازار بورس و فرابورس";
      case "opportunities": return "دیده‌بان جامع، فیلتر دسته‌بندی‌شده و رادار سهام";
      case "open_positions": return "میزکار تخصصی معاملات باز، رصد سود/زیان و مدیریت سرمایه";
      case "fundamental": return "مرکز تحلیل بنیادی، نسبت‌های مالی، ارزش‌گذاری و اطلاعیه‌های کدال";
      case "trading_lab": return "مرکز آزمایشگاه، معاملات آزمایشی، شبیه‌ساز بک‌تست و ارزیابی استراتژی‌ها";
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

  return (
    <div style={{ display: "flex", minHeight: "100vh", backgroundColor: "var(--bg-primary)" }}>
      {/* 1. Right Navigation Sidebar */}
      <Sidebar
        activeTab={activeTab}
        onSelectTab={handleSelectTab}
        opportunityCount={opportunities.length}
        openPositionsCount={openPositionsCount}
      />

      {/* 2. Main Content Area */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        {/* Top Status Header with Single Global Refresh and Live Search */}
        <Header
          currentViewTitle={getTabTitle(activeTab)}
          regime={overview?.market_regime || "risk_on"}
          regimeFa={overview?.market_regime_fa || "رونق و تقاضای پرقدرت"}
          jalaliTime={overview?.current_time_jalali || ""}
          tradingMode={overview?.trading_mode || "paper"}
          isRefreshing={isRefreshing}
          onRefreshAll={() => fetchGlobalData(true)}
          lastUpdatedTime={lastUpdatedTime}
          onSelectSymbol={handleOpenSymbolModal}
          isAutoRefreshEnabled={isAutoRefreshEnabled}
          onToggleAutoRefresh={toggleAutoRefresh}
          cadenceSeconds={cadenceSeconds}
        />

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
          <div style={{ padding: "1.5rem 1.75rem", display: activeTab === "overview" ? "block" : "none" }}>
            <OverviewView
              overviewData={overview}
              portfolioData={portfolio}
              topOpportunities={opportunities}
              sectors={sectors}
              onSelectOpportunity={handleOpenSymbolModal}
              onSelectSymbol={handleOpenSymbolModal}
              onNavigateTab={handleSelectTab}
            />
          </div>

          {/* Opportunities — lazy-mounted on first visit */}
          {(visitedTabs.has("opportunities") || activeTab === "opportunities") && (
            <div style={{ padding: "1.5rem 1.75rem", display: activeTab === "opportunities" ? "block" : "none" }}>
              <OpportunitiesView
                opportunities={opportunities}
                onSelectOpportunity={handleOpenSymbolModal}
                onSelectSymbol={handleOpenSymbolModal}
              />
            </div>
          )}

          {/* Open Positions — lazy-mounted on first visit */}
          {(visitedTabs.has("open_positions") || activeTab === "open_positions") && (
            <div style={{ display: activeTab === "open_positions" ? "block" : "none" }}>
              <OpenPositionsView
                initialPortfolio={portfolio}
                onSelectSymbol={handleOpenSymbolModal}
              />
            </div>
          )}

          {/* Fundamental — lazy-mounted on first visit */}
          {(visitedTabs.has("fundamental") || activeTab === "fundamental") && (
            <div style={{ padding: "1.5rem 1.75rem", display: activeTab === "fundamental" ? "block" : "none" }}>
              <FundamentalView
                onSelectSymbol={handleOpenSymbolModal}
              />
            </div>
          )}

          {/* Trading Lab — lazy-mounted on first visit */}
          {(visitedTabs.has("trading_lab") || activeTab === "trading_lab") && (
            <div style={{ padding: "1.5rem 1.75rem", display: activeTab === "trading_lab" ? "block" : "none" }}>
              <TradingLabView />
            </div>
          )}

          {/* Health & Settings — lazy-mounted on first visit */}
          {(visitedTabs.has("health_settings") || activeTab === "health_settings") && (
            <div style={{ padding: "1.5rem 1.75rem", display: activeTab === "health_settings" ? "block" : "none" }}>
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
            fetchGlobalData(false);
          }}
        />
      )}
    </div>
  );
}
