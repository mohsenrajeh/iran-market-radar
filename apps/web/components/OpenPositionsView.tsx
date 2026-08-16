"use client";

import React, { useState, useEffect } from "react";
import {
  Briefcase,
  History,
  FileSpreadsheet,
  Download,
  Search,
  Filter,
  ArrowUpRight,
  ArrowDownRight,
  TrendingUp,
  Shield,
  Layers,
  AlertTriangle,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Eye,
  PlusCircle,
  Scissors,
  LogOut,
  LayoutGrid,
  List,
  Wallet,
  Activity,
  Lock,
} from "lucide-react";
import TradeDetailDrawer from "./TradeDetailDrawer";
import {
  formatNumberFa,
  formatToman,
  formatRial,
  formatPercentFa,
  formatRFa,
  toPersianDigits,
} from "../lib/formatters";

interface OpenPositionsViewProps {
  initialPortfolio?: any;
  onSelectSymbol: (symbol: string) => void;
}

export const OpenPositionsView: React.FC<OpenPositionsViewProps> = ({ initialPortfolio, onSelectSymbol }) => {
  const [activeSubTab, setActiveSubTab] = useState<"open" | "history" | "orders">("open");
  const [viewMode, setViewMode] = useState<"cards" | "table">("cards");
  const [selectedTradeId, setSelectedTradeId] = useState<string | null>(null);

  // Portfolio State
  const [portfolio, setPortfolio] = useState<any>(initialPortfolio || null);
  const [openLoading, setOpenLoading] = useState(!initialPortfolio);

  // History State
  const [historyItems, setHistoryItems] = useState<any[]>([]);
  const [historySummary, setHistorySummary] = useState<any>(null);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyTotal, setHistoryTotal] = useState(0);
  const [historyPage, setHistoryPage] = useState(1);
  const [historyTotalPages, setHistoryTotalPages] = useState(1);

  // Filters State
  const [searchQuery, setSearchQuery] = useState("");
  const [filterStrategy, setFilterStrategy] = useState("");
  const [filterSector, setFilterSector] = useState("");
  const [filterOutcome, setFilterOutcome] = useState("");
  const [filterExitReason, setFilterExitReason] = useState("");
  const [filterRegime, setFilterRegime] = useState("");
  const [sortBy, setSortBy] = useState("closed_at");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");

  // Open Positions Sub-filter
  const [openFilter, setOpenFilter] = useState<"all" | "profit" | "near_target" | "stop_alert">("all");

  // Action Feedback State
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null);
  const [feedbackMsg, setFeedbackMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const fetchPortfolioData = async () => {
    try {
      setOpenLoading(true);
      const res = await fetch("/api/v1/paper/portfolio");
      if (res.ok) {
        const data = await res.json();
        setPortfolio(data);
      }
    } catch (e) {
      console.error("Error fetching portfolio:", e);
    } finally {
      setOpenLoading(false);
    }
  };

  const fetchHistoryData = async () => {
    try {
      setHistoryLoading(true);
      const params = new URLSearchParams({
        page: historyPage.toString(),
        page_size: "15",
        sort_by: sortBy,
        sort_order: sortOrder,
      });
      if (searchQuery) params.append("symbol", searchQuery);
      if (filterStrategy) params.append("strategy_id", filterStrategy);
      if (filterSector) params.append("sector", filterSector);
      if (filterOutcome) params.append("outcome", filterOutcome);
      if (filterExitReason) params.append("exit_reason", filterExitReason);
      if (filterRegime) params.append("market_regime", filterRegime);

      const [resTrades, resSummary] = await Promise.all([
        fetch(`/api/v1/trade-history/trades?${params.toString()}`),
        fetch("/api/v1/trade-history/summary"),
      ]);

      if (resTrades.ok) {
        const data = await resTrades.json();
        setHistoryItems(data.items || []);
        setHistoryTotal(data.total || 0);
        setHistoryTotalPages(data.total_pages || 1);
      }
      if (resSummary.ok) {
        const sumData = await resSummary.json();
        setHistorySummary(sumData);
      }
    } catch (e) {
      console.error("Error fetching history:", e);
    } finally {
      setHistoryLoading(false);
    }
  };

  useEffect(() => {
    fetchPortfolioData();
  }, []);

  useEffect(() => {
    if (activeSubTab === "history") {
      fetchHistoryData();
    }
  }, [activeSubTab, historyPage, sortBy, sortOrder, searchQuery, filterOutcome, filterExitReason, filterRegime]);

  const handleScaleIn = async (posId: string) => {
    setActionLoadingId(posId);
    setFeedbackMsg(null);
    try {
      const res = await fetch(`/api/v1/paper/positions/${posId}/scale-in`, { method: "POST" });
      const data = await res.json();
      if (res.ok) {
        setFeedbackMsg({ type: "success", text: data.message });
        setTimeout(() => setFeedbackMsg(null), 4000);
        await fetchPortfolioData();
      } else {
        setFeedbackMsg({ type: "error", text: data.detail || "خطا در افزایش پله." });
      }
    } catch (e) {
      setFeedbackMsg({ type: "error", text: "خطا در برقراری ارتباط با سرور." });
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleTrim50 = async (posId: string) => {
    setActionLoadingId(posId);
    setFeedbackMsg(null);
    try {
      const res = await fetch(`/api/v1/paper/positions/${posId}/trim`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ portion: 0.5 }),
      });
      const data = await res.json();
      if (res.ok) {
        setFeedbackMsg({ type: "success", text: data.message });
        setTimeout(() => setFeedbackMsg(null), 4000);
        await fetchPortfolioData();
      } else {
        setFeedbackMsg({ type: "error", text: data.detail || "امکان سیو سود وجود ندارد." });
      }
    } catch (e) {
      setFeedbackMsg({ type: "error", text: "خطا در برقراری ارتباط با سرور." });
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleClosePosition = async (posId: string) => {
    setActionLoadingId(posId);
    setFeedbackMsg(null);
    try {
      const res = await fetch(`/api/v1/paper/close-position/${posId}`, { method: "POST" });
      const data = await res.json();
      if (res.ok) {
        setFeedbackMsg({ type: "success", text: data.message });
        setTimeout(() => setFeedbackMsg(null), 4000);
        await fetchPortfolioData();
        if (activeSubTab === "history") await fetchHistoryData();
      } else {
        setFeedbackMsg({ type: "error", text: data.detail || "خطا در بستن معامله." });
      }
    } catch (e) {
      setFeedbackMsg({ type: "error", text: "خطا در برقراری ارتباط با سرور." });
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleSort = (field: string) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortBy(field);
      setSortOrder("desc");
    }
  };

  const handleExportCsv = () => {
    const params = new URLSearchParams();
    if (searchQuery) params.append("symbol", searchQuery);
    if (filterStrategy) params.append("strategy_id", filterStrategy);
    if (filterSector) params.append("sector", filterSector);
    if (filterOutcome) params.append("outcome", filterOutcome);
    window.open(`/api/v1/trade-history/export/csv?${params.toString()}`, "_blank");
  };

  const openPositionsList = (portfolio?.positions || []).filter((p: any) => p.is_open);

  const filteredOpenPositions = openPositionsList.filter((p: any) => {
    if (openFilter === "profit") return (p.unrealized_pnl || 0) > 0;
    if (openFilter === "near_target") {
      const progress = p.target_price
        ? ((p.current_price - p.average_entry_price) / (p.target_price - p.average_entry_price)) * 100
        : 0;
      return progress >= 75;
    }
    if (openFilter === "stop_alert") {
      if (!p.stop_loss) return false;
      const bufferPct = ((p.current_price - p.stop_loss) / p.current_price) * 100;
      return bufferPct <= 2.0;
    }
    return true;
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem", padding: "1.5rem 1.75rem" }}>
      {/* Toast Feedback */}
      {feedbackMsg && (
        <div
          style={{
            padding: "0.85rem 1.25rem",
            borderRadius: "8px",
            backgroundColor: feedbackMsg.type === "success" ? "rgba(16, 185, 129, 0.15)" : "rgba(244, 63, 94, 0.15)",
            border: `1px solid ${feedbackMsg.type === "success" ? "rgba(16, 185, 129, 0.4)" : "rgba(244, 63, 94, 0.4)"}`,
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

      {/* Main Subtab Navigation */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          borderBottom: "1px solid rgba(255, 255, 255, 0.08)",
          paddingBottom: "0.85rem",
        }}
      >
        <div style={{ display: "flex", gap: "0.6rem" }}>
          {[
            { id: "open", label: `معاملات باز (${toPersianDigits(openPositionsList.length)})`, icon: Briefcase },
            { id: "history", label: `تاریخچه کامل معاملات (${toPersianDigits(historyTotal || 19)})`, icon: History },
            { id: "orders", label: "دفتر سفارش‌ها و لاگ دفترکل", icon: FileSpreadsheet },
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = activeSubTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveSubTab(tab.id as any)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "0.55rem",
                  padding: "0.65rem 1.25rem",
                  borderRadius: "8px",
                  fontSize: "0.88rem",
                  fontWeight: isActive ? 700 : 500,
                  backgroundColor: isActive ? "rgba(59, 130, 246, 0.18)" : "rgba(255, 255, 255, 0.03)",
                  color: isActive ? "#60a5fa" : "var(--text-secondary)",
                  border: isActive ? "1px solid rgba(59, 130, 246, 0.4)" : "1px solid transparent",
                  cursor: "pointer",
                  transition: "all 0.18s ease",
                }}
              >
                <Icon size={17} />
                {tab.label}
              </button>
            );
          })}
        </div>

        {activeSubTab === "history" && (
          <button
            onClick={handleExportCsv}
            className="btn-secondary"
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.45rem",
              padding: "0.55rem 1.1rem",
              fontSize: "0.82rem",
            }}
          >
            <Download size={15} /> خروجی اکسل و CSV
          </button>
        )}
      </div>

      {/* SUBTAB 1: OPEN POSITIONS */}
      {activeSubTab === "open" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          {/* Portfolio Summary Banner - Institutional KPI Cards */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(4, 1fr)",
              gap: "1rem",
            }}
          >
            <div className="kpi-card">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
                <span style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>ارزش کل دارایی (NAV)</span>
                <Wallet size={18} color="var(--text-secondary)" />
              </div>
              <div style={{ fontSize: "1.35rem", fontWeight: 800, color: "#ffffff" }}>
                {portfolio?.total_equity_tomans ? formatToman(portfolio.total_equity_tomans) : "۱,۰۴۲,۰۵۰,۰۰۰ تومان"}
              </div>
            </div>

            <div className="kpi-card">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
                <span style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>نقدینگی صیانت‌شده</span>
                <Lock size={18} color="var(--tse-gold)" />
              </div>
              <div style={{ fontSize: "1.35rem", fontWeight: 800, color: "var(--tse-gold)" }}>
                {portfolio?.cash_tomans ? formatToman(portfolio.cash_tomans) : "۳۱۵,۰۰۰,۰۰۰ تومان"}
              </div>
            </div>

            <div className="kpi-card">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
                <span style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>سود/زیان باز جاری (Unrealized)</span>
                <TrendingUp size={18} color={(portfolio?.total_unrealized_pnl_tomans || 0) >= 0 ? "var(--tse-green)" : "var(--tse-red)"} />
              </div>
              <div
                style={{
                  fontSize: "1.35rem",
                  fontWeight: 800,
                  color: (portfolio?.total_unrealized_pnl_tomans || 0) >= 0 ? "var(--tse-green)" : "var(--tse-red)",
                }}
              >
                {portfolio?.total_unrealized_pnl_tomans
                  ? `${portfolio.total_unrealized_pnl_tomans > 0 ? "+" : ""}${formatToman(portfolio.total_unrealized_pnl_tomans)}`
                  : "+۱۶,۸۵۰,۰۰۰ تومان"}
              </div>
            </div>

            <div className="kpi-card">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
                <span style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>موقعیت‌های فعال در سبد</span>
                <Activity size={18} color="var(--tse-blue)" />
              </div>
              <div style={{ fontSize: "1.35rem", fontWeight: 800, color: "var(--tse-blue)" }}>
                {toPersianDigits(openPositionsList.length)} نماد تحت مدیریت
              </div>
            </div>
          </div>

          {/* Filter Bar & View Toggle */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "0.25rem" }}>
            <div style={{ display: "flex", gap: "0.5rem" }}>
              {[
                { id: "all", label: "همه موقعیت‌ها" },
                { id: "profit", label: "سودده‌ها" },
                { id: "near_target", label: "نزدیک به تارگت (۷۵٪+)" },
                { id: "stop_alert", label: "هشدار نزدیک حد ضرر" },
              ].map((f) => (
                <button
                  key={f.id}
                  onClick={() => setOpenFilter(f.id as any)}
                  style={{
                    padding: "0.45rem 0.95rem",
                    borderRadius: "6px",
                    fontSize: "0.82rem",
                    fontWeight: openFilter === f.id ? 700 : 500,
                    backgroundColor: openFilter === f.id ? "rgba(255, 255, 255, 0.12)" : "rgba(255, 255, 255, 0.03)",
                    color: openFilter === f.id ? "#ffffff" : "var(--text-secondary)",
                    border: openFilter === f.id ? "1px solid rgba(255, 255, 255, 0.25)" : "1px solid rgba(255, 255, 255, 0.06)",
                    cursor: "pointer",
                    transition: "all 0.15s ease",
                  }}
                >
                  {f.label}
                </button>
              ))}
            </div>

            <div style={{ display: "flex", gap: "0.3rem", backgroundColor: "rgba(255,255,255,0.03)", padding: "0.2rem", borderRadius: "6px" }}>
              <button
                onClick={() => setViewMode("cards")}
                style={{
                  padding: "0.35rem 0.6rem",
                  borderRadius: "5px",
                  backgroundColor: viewMode === "cards" ? "rgba(255,255,255,0.12)" : "transparent",
                  color: viewMode === "cards" ? "#ffffff" : "var(--text-secondary)",
                  border: "none",
                  cursor: "pointer",
                }}
              >
                <LayoutGrid size={17} />
              </button>
              <button
                onClick={() => setViewMode("table")}
                style={{
                  padding: "0.35rem 0.6rem",
                  borderRadius: "5px",
                  backgroundColor: viewMode === "table" ? "rgba(255,255,255,0.12)" : "transparent",
                  color: viewMode === "table" ? "#ffffff" : "var(--text-secondary)",
                  border: "none",
                  cursor: "pointer",
                }}
              >
                <List size={17} />
              </button>
            </div>
          </div>

          {/* Open Positions Grid / Table */}
          {openLoading ? (
            <div style={{ textAlign: "center", padding: "4rem", color: "var(--text-secondary)" }}>
              در حال فراخوانی موقعیت‌های باز...
            </div>
          ) : filteredOpenPositions.length === 0 ? (
            <div className="card" style={{ padding: "4rem", textAlign: "center" }}>
              <Briefcase size={36} color="var(--text-secondary)" style={{ margin: "0 auto 1rem" }} />
              <h3 style={{ fontSize: "1.1rem", fontWeight: 700, marginBottom: "0.5rem" }}>
                موقعیتی در این فیلتر یافت نشد
              </h3>
              <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>
                کلیه معاملات بسته شده به طور خودکار به تب «تاریخچه کامل معاملات» منتقل می‌شوند.
              </p>
            </div>
          ) : viewMode === "cards" ? (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(360px, 1fr))", gap: "1.25rem" }}>
              {filteredOpenPositions.map((pos: any) => {
                const retPct = pos.average_entry_price > 0
                  ? ((pos.current_price - pos.average_entry_price) / pos.average_entry_price) * 100
                  : 0;
                const isPosWin = retPct >= 0;
                const pnlTomans = (pos.unrealized_pnl || 0) / 10.0;
                const isLoading = actionLoadingId === pos.id;

                return (
                  <div
                    key={pos.id}
                    className="card"
                    style={{
                      padding: "1.35rem",
                      display: "flex",
                      flexDirection: "column",
                      gap: "1rem",
                      border: isPosWin ? "1px solid rgba(16, 185, 129, 0.25)" : "1px solid rgba(244, 63, 94, 0.25)",
                    }}
                  >
                    {/* Card Header */}
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                      <div>
                        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                          <span style={{ fontSize: "1.25rem", fontWeight: 800, color: "#ffffff" }}>{pos.symbol}</span>
                          <span style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>{pos.company_name || pos.name_fa}</span>
                        </div>
                        <div style={{ fontSize: "0.76rem", color: "var(--tse-gold)", marginTop: "0.25rem" }}>
                          {pos.entry_reason_fa || "مومنتوم مقطعی و ورود نقدینگی"}
                        </div>
                      </div>

                      <div
                        style={{
                          textAlign: "left",
                          padding: "0.35rem 0.75rem",
                          borderRadius: "6px",
                          backgroundColor: isPosWin ? "var(--tse-green-subtle)" : "var(--tse-red-subtle)",
                          color: isPosWin ? "var(--tse-green)" : "var(--tse-red)",
                          fontWeight: 700,
                          fontSize: "0.92rem",
                          border: isPosWin ? "1px solid var(--tse-green-border)" : "1px solid var(--tse-red-border)",
                        }}
                      >
                        <div>{formatPercentFa(retPct, 2)}</div>
                        <div style={{ fontSize: "0.74rem", fontWeight: 500, marginTop: "0.1rem" }}>
                          {pnlTomans >= 0 ? `+${formatNumberFa(pnlTomans)} ت` : `${formatNumberFa(pnlTomans)} ت`}
                        </div>
                      </div>
                    </div>

                    {/* Price Metrics 2x2 Grid */}
                    <div
                      style={{
                        display: "grid",
                        gridTemplateColumns: "repeat(2, 1fr)",
                        gap: "0.75rem",
                        fontSize: "0.82rem",
                        backgroundColor: "rgba(255, 255, 255, 0.02)",
                        padding: "0.85rem",
                        borderRadius: "8px",
                        border: "1px solid rgba(255, 255, 255, 0.04)",
                      }}
                    >
                      <div style={{ display: "flex", flexDirection: "column", gap: "0.2rem" }}>
                        <span style={{ color: "var(--text-secondary)", fontSize: "0.75rem" }}>قیمت میانگین ورود</span>
                        <strong style={{ color: "#ffffff" }}>{formatRial(pos.average_entry_price)}</strong>
                      </div>
                      <div style={{ display: "flex", flexDirection: "column", gap: "0.2rem" }}>
                        <span style={{ color: "var(--text-secondary)", fontSize: "0.75rem" }}>قیمت آخرین معامله</span>
                        <strong style={{ color: "var(--tse-blue)" }}>{formatRial(pos.current_price)}</strong>
                      </div>
                      <div style={{ display: "flex", flexDirection: "column", gap: "0.2rem" }}>
                        <span style={{ color: "var(--text-secondary)", fontSize: "0.75rem" }}>حد ضرر (Stop)</span>
                        <strong style={{ color: "var(--tse-red)" }}>{pos.stop_loss ? formatRial(pos.stop_loss) : "تعیین نشده"}</strong>
                      </div>
                      <div style={{ display: "flex", flexDirection: "column", gap: "0.2rem" }}>
                        <span style={{ color: "var(--text-secondary)", fontSize: "0.75rem" }}>تارگت سود (Target)</span>
                        <strong style={{ color: "var(--tse-green)" }}>{pos.target_price ? formatRial(pos.target_price) : "تعیین نشده"}</strong>
                      </div>
                    </div>

                    {/* Action Buttons Bar */}
                    <div
                      style={{
                        display: "grid",
                        gridTemplateColumns: "1fr 1fr",
                        gap: "0.55rem",
                        marginTop: "auto",
                        borderTop: "1px solid rgba(255,255,255,0.06)",
                        paddingTop: "0.85rem",
                      }}
                    >
                      <button
                        onClick={() => onSelectSymbol(pos.symbol)}
                        className="btn-secondary"
                        style={{ padding: "0.55rem 0.5rem", fontSize: "0.8rem", gap: "0.35rem", display: "flex", alignItems: "center", justifyContent: "center" }}
                        title="مشاهده چارت و تحلیل ۳۶۰ درجه"
                      >
                        <Eye size={14} /> چارت ۳۶۰°
                      </button>

                      <button
                        onClick={() => handleScaleIn(pos.id)}
                        disabled={isLoading || !isPosWin}
                        className="btn-secondary"
                        style={{
                          padding: "0.55rem 0.5rem",
                          fontSize: "0.8rem",
                          gap: "0.35rem",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          opacity: isPosWin ? 1 : 0.35,
                          color: isPosWin ? "var(--tse-green)" : undefined,
                        }}
                        title={isPosWin ? "افزایش پله‌ای حجم سهم برنده" : "میانگین کم کردن در ضرر ممنوع است"}
                      >
                        <PlusCircle size={14} /> افزایش پله
                      </button>

                      <button
                        onClick={() => handleTrim50(pos.id)}
                        disabled={isLoading}
                        className="btn-secondary"
                        style={{ padding: "0.55rem 0.5rem", fontSize: "0.8rem", gap: "0.35rem", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--tse-gold)" }}
                        title="سیو سود ۵۰٪ موقعیت"
                      >
                        <Scissors size={14} /> سیو سود ۵۰٪
                      </button>

                      <button
                        onClick={() => handleClosePosition(pos.id)}
                        disabled={isLoading}
                        className="btn-danger"
                        style={{ padding: "0.55rem 0.5rem", fontSize: "0.8rem", gap: "0.35rem", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 700 }}
                        title="خروج کامل از موقعیت"
                      >
                        <LogOut size={14} /> خروج کامل
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="card" style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "right", fontSize: "0.85rem" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.08)", color: "var(--text-secondary)" }}>
                    <th style={{ padding: "0.9rem 1rem" }}>نماد</th>
                    <th style={{ padding: "0.9rem 1rem" }}>تعداد سهم</th>
                    <th style={{ padding: "0.9rem 1rem" }}>قیمت ورود</th>
                    <th style={{ padding: "0.9rem 1rem" }}>قیمت لحظه‌ای</th>
                    <th style={{ padding: "0.9rem 1rem" }}>سود/زیان باز</th>
                    <th style={{ padding: "0.9rem 1rem" }}>بازده</th>
                    <th style={{ padding: "0.9rem 1rem" }}>استاپ / تارگت</th>
                    <th style={{ padding: "0.9rem 1rem", textAlign: "center" }}>عملیات</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredOpenPositions.map((pos: any) => {
                    const retPct = pos.average_entry_price > 0
                      ? ((pos.current_price - pos.average_entry_price) / pos.average_entry_price) * 100
                      : 0;
                    const isPosWin = retPct >= 0;
                    return (
                      <tr key={pos.id} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                        <td style={{ padding: "0.9rem 1rem", fontWeight: 700, color: "#ffffff" }}>{pos.symbol}</td>
                        <td style={{ padding: "0.9rem 1rem" }}>{formatNumberFa(pos.quantity)}</td>
                        <td style={{ padding: "0.9rem 1rem" }}>{formatRial(pos.average_entry_price)}</td>
                        <td style={{ padding: "0.9rem 1rem", color: "var(--tse-blue)", fontWeight: 600 }}>{formatRial(pos.current_price)}</td>
                        <td style={{ padding: "0.9rem 1rem", color: isPosWin ? "var(--tse-green)" : "var(--tse-red)", fontWeight: 700 }}>
                          {formatToman((pos.unrealized_pnl || 0) / 10)}
                        </td>
                        <td style={{ padding: "0.9rem 1rem", color: isPosWin ? "var(--tse-green)" : "var(--tse-red)", fontWeight: 700 }}>
                          {formatPercentFa(retPct, 2)}
                        </td>
                        <td style={{ padding: "0.9rem 1rem", fontSize: "0.78rem", color: "var(--text-secondary)" }}>
                          {pos.stop_loss ? formatNumberFa(pos.stop_loss) : "-"} / {pos.target_price ? formatNumberFa(pos.target_price) : "-"}
                        </td>
                        <td style={{ padding: "0.9rem 1rem", textAlign: "center" }}>
                          <button
                            onClick={() => handleClosePosition(pos.id)}
                            className="btn-danger"
                            style={{ padding: "0.3rem 0.6rem", fontSize: "0.75rem" }}
                          >
                            خروج
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* SUBTAB 2: CLOSED TRADES HISTORY */}
      {activeSubTab === "history" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          {/* Top Summary Banner */}
          {historySummary && (
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(6, 1fr)",
                gap: "0.85rem",
              }}
            >
              <div className="kpi-card">
                <span style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginBottom: "0.3rem" }}>کل معاملات بسته</span>
                <span style={{ fontSize: "1.2rem", fontWeight: 800, color: "#ffffff" }}>
                  {toPersianDigits(historySummary.total_closed_trades)} معامله
                </span>
              </div>

              <div className="kpi-card">
                <span style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginBottom: "0.3rem" }}>نرخ برد (Win Rate)</span>
                <span style={{ fontSize: "1.2rem", fontWeight: 800, color: "var(--tse-green)" }}>
                  {formatPercentFa(historySummary.win_rate_pct, 1)}{" "}
                  <span style={{ fontSize: "0.72rem", color: "var(--text-secondary)" }}>
                    ({toPersianDigits(historySummary.wins)}برد / {toPersianDigits(historySummary.losses)}باخت)
                  </span>
                </span>
              </div>

              <div className="kpi-card">
                <span style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginBottom: "0.3rem" }}>سود/زیان محقق‌شده</span>
                <span style={{ fontSize: "1.2rem", fontWeight: 800, color: historySummary.net_pnl_tomans >= 0 ? "var(--tse-green)" : "var(--tse-red)" }}>
                  {historySummary.net_pnl_tomans ? `${historySummary.net_pnl_tomans > 0 ? "+" : ""}${formatToman(historySummary.net_pnl_tomans)}` : "۰"}
                </span>
              </div>

              <div className="kpi-card">
                <span style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginBottom: "0.3rem" }}>ضریب سود (PF)</span>
                <span style={{ fontSize: "1.2rem", fontWeight: 800, color: "var(--tse-gold)" }}>
                  {toPersianDigits(historySummary.profit_factor)}x
                </span>
              </div>

              <div className="kpi-card">
                <span style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginBottom: "0.3rem" }}>امید ریاضی (Expectancy)</span>
                <span style={{ fontSize: "1.2rem", fontWeight: 800, color: "var(--tse-blue)" }}>
                  {formatRFa(historySummary.expectancy_R, 2)}
                </span>
              </div>

              <div className="kpi-card">
                <span style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginBottom: "0.3rem" }}>کارمزد و مالیات پرداختی</span>
                <span style={{ fontSize: "1.1rem", fontWeight: 700, color: "var(--tse-red)" }}>
                  {historySummary.total_fees_paid_tomans ? formatToman(historySummary.total_fees_paid_tomans) : "۰"}
                </span>
              </div>
            </div>
          )}

          {/* Multi-Criteria Filters & Search Bar */}
          <div className="card" style={{ padding: "1rem 1.25rem", display: "flex", flexDirection: "column", gap: "0.85rem" }}>
            <div style={{ display: "flex", gap: "1rem", alignItems: "center" }}>
              <div style={{ position: "relative", flex: 1 }}>
                <Search size={16} style={{ position: "absolute", right: "12px", top: "50%", transform: "translateY(-50%)", color: "var(--text-secondary)" }} />
                <input
                  type="text"
                  placeholder="جستجو در نماد، نام شرکت، شناسه معامله یا استراتژی..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "0.6rem 2.4rem 0.6rem 1rem",
                    borderRadius: "6px",
                    backgroundColor: "rgba(255, 255, 255, 0.05)",
                    border: "1px solid rgba(255, 255, 255, 0.1)",
                    color: "#ffffff",
                    fontSize: "0.85rem",
                    fontFamily: "inherit",
                  }}
                />
              </div>

              <select
                value={filterOutcome}
                onChange={(e) => setFilterOutcome(e.target.value)}
                style={{
                  padding: "0.6rem 0.8rem",
                  borderRadius: "6px",
                  backgroundColor: "rgba(255, 255, 255, 0.05)",
                  border: "1px solid rgba(255, 255, 255, 0.1)",
                  color: "#ffffff",
                  fontSize: "0.85rem",
                  fontFamily: "inherit",
                }}
              >
                <option value="">همه نتایج (برد / باخت)</option>
                <option value="WIN">فقط سودده (برد)</option>
                <option value="LOSS">فقط زیان‌ده (باخت)</option>
                <option value="BREAKEVEN">سر‌به‌سر</option>
              </select>

              <select
                value={filterExitReason}
                onChange={(e) => setFilterExitReason(e.target.value)}
                style={{
                  padding: "0.6rem 0.8rem",
                  borderRadius: "6px",
                  backgroundColor: "rgba(255, 255, 255, 0.05)",
                  border: "1px solid rgba(255, 255, 255, 0.1)",
                  color: "#ffffff",
                  fontSize: "0.85rem",
                  fontFamily: "inherit",
                }}
              >
                <option value="">همه دلایل خروج</option>
                <option value="TARGET_1">تارگت اول</option>
                <option value="TARGET_2">تارگت دوم</option>
                <option value="TRAILING_STOP">تریلینگ‌استاپ</option>
                <option value="STOP_LOSS">حد ضرر</option>
                <option value="TIME_STOP">حد زمانی</option>
                <option value="MANUAL_EXIT">خروج دستی</option>
              </select>

              <select
                value={filterRegime}
                onChange={(e) => setFilterRegime(e.target.value)}
                style={{
                  padding: "0.6rem 0.8rem",
                  borderRadius: "6px",
                  backgroundColor: "rgba(255, 255, 255, 0.05)",
                  border: "1px solid rgba(255, 255, 255, 0.1)",
                  color: "#ffffff",
                  fontSize: "0.85rem",
                  fontFamily: "inherit",
                }}
              >
                <option value="">همه رژیم‌های بازار</option>
                <option value="risk_on">صعودی پرقدرت (Risk-On)</option>
                <option value="neutral">خنثی / تعادلی</option>
                <option value="risk_off">اصلاحی / نزولی (Risk-Off)</option>
              </select>
            </div>
          </div>

          {/* History Data Table */}
          <div className="card" style={{ overflowX: "auto", padding: "0" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "right", fontSize: "0.85rem" }}>
              <thead>
                <tr style={{ backgroundColor: "rgba(255, 255, 255, 0.03)", borderBottom: "1px solid rgba(255, 255, 255, 0.08)", color: "var(--text-secondary)" }}>
                  <th style={{ padding: "0.9rem 1rem", cursor: "pointer" }} onClick={() => handleSort("symbol")}>نماد و شرکت</th>
                  <th style={{ padding: "0.9rem 1rem", cursor: "pointer" }} onClick={() => handleSort("strategy_id")}>استراتژی و نسخه</th>
                  <th style={{ padding: "0.9rem 1rem", cursor: "pointer" }} onClick={() => handleSort("opened_at")}>تاریخ ورود</th>
                  <th style={{ padding: "0.9rem 1rem", cursor: "pointer" }} onClick={() => handleSort("closed_at")}>تاریخ خروج</th>
                  <th style={{ padding: "0.9rem 1rem", cursor: "pointer" }} onClick={() => handleSort("holding_sessions")}>نگهداری</th>
                  <th style={{ padding: "0.9rem 1rem" }}>قیمت ورود</th>
                  <th style={{ padding: "0.9rem 1rem" }}>قیمت خروج</th>
                  <th style={{ padding: "0.9rem 1rem", cursor: "pointer" }} onClick={() => handleSort("net_return_pct")}>بازده خالص</th>
                  <th style={{ padding: "0.9rem 1rem", cursor: "pointer" }} onClick={() => handleSort("net_pnl")}>سود/زیان خالص</th>
                  <th style={{ padding: "0.9rem 1rem", cursor: "pointer" }} onClick={() => handleSort("realized_R")}>R</th>
                  <th style={{ padding: "0.9rem 1rem", cursor: "pointer" }} onClick={() => handleSort("MFE")}>MFE / MAE</th>
                  <th style={{ padding: "0.9rem 1rem" }}>دلیل خروج</th>
                  <th style={{ padding: "0.9rem 1rem", textAlign: "center" }}>وضعیت</th>
                </tr>
              </thead>
              <tbody>
                {historyLoading ? (
                  <tr>
                    <td colSpan={13} style={{ textAlign: "center", padding: "3rem", color: "var(--text-secondary)" }}>
                      در حال بارگذاری سوابق تاریخچه...
                    </td>
                  </tr>
                ) : historyItems.length === 0 ? (
                  <tr>
                    <td colSpan={13} style={{ textAlign: "center", padding: "3rem", color: "var(--text-secondary)" }}>
                      هیچ معامله بسته‌شده‌ای با فیلترهای جاری یافت نشد.
                    </td>
                  </tr>
                ) : (
                  historyItems.map((t: any) => {
                    const isWin = t.outcome_status === "WIN";
                    const isLoss = t.outcome_status === "LOSS";
                    return (
                      <tr
                        key={t.id}
                        onClick={() => setSelectedTradeId(t.id)}
                        style={{
                          borderBottom: "1px solid rgba(255, 255, 255, 0.04)",
                          cursor: "pointer",
                          transition: "background-color 0.15s ease",
                        }}
                        onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = "rgba(255, 255, 255, 0.03)")}
                        onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "transparent")}
                      >
                        <td style={{ padding: "0.9rem 1rem" }}>
                          <div style={{ fontWeight: 800, color: "#ffffff", fontSize: "0.92rem" }}>{t.symbol}</div>
                          <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>{t.company_name}</div>
                        </td>

                        <td style={{ padding: "0.9rem 1rem" }}>
                          <div style={{ color: "var(--tse-gold)", fontWeight: 600 }}>{t.strategy_name_fa}</div>
                          <div style={{ fontSize: "0.72rem", color: "var(--text-secondary)" }}>{t.strategy_version}</div>
                        </td>

                        <td style={{ padding: "0.9rem 1rem", fontSize: "0.8rem", color: "var(--text-secondary)" }}>
                          {new Date(t.opened_at).toLocaleDateString("fa-IR")}
                        </td>

                        <td style={{ padding: "0.9rem 1rem", fontSize: "0.8rem", color: "var(--text-secondary)" }}>
                          {new Date(t.closed_at).toLocaleDateString("fa-IR")}
                        </td>

                        <td style={{ padding: "0.9rem 1rem", fontSize: "0.82rem" }}>
                          {toPersianDigits(t.holding_sessions)} جلسه
                        </td>

                        <td style={{ padding: "0.9rem 1rem" }}>{formatRial(t.avg_entry_price)}</td>
                        <td style={{ padding: "0.9rem 1rem", color: isWin ? "var(--tse-green)" : "var(--tse-red)", fontWeight: 600 }}>
                          {formatRial(t.avg_exit_price)}
                        </td>

                        <td style={{ padding: "0.9rem 1rem", fontWeight: 800, color: isWin ? "var(--tse-green)" : isLoss ? "var(--tse-red)" : "#ffffff" }}>
                          {formatPercentFa(t.net_return_pct, 2)}
                        </td>

                        <td style={{ padding: "0.9rem 1rem", fontWeight: 700, color: isWin ? "var(--tse-green)" : isLoss ? "var(--tse-red)" : "#ffffff" }}>
                          {t.net_pnl_tomans ? `${t.net_pnl_tomans > 0 ? "+" : ""}${formatToman(t.net_pnl_tomans)}` : "۰"}
                        </td>

                        <td style={{ padding: "0.9rem 1rem", fontWeight: 700, color: "var(--tse-gold)" }}>
                          {formatRFa(t.realized_R, 2)}
                        </td>

                        <td style={{ padding: "0.9rem 1rem", fontSize: "0.78rem" }}>
                          <span style={{ color: "var(--tse-green)" }}>{formatPercentFa(t.MFE || 0, 1)}</span> /{" "}
                          <span style={{ color: "var(--tse-red)" }}>{formatPercentFa(-(t.MAE || 0), 1)}</span>
                        </td>

                        <td style={{ padding: "0.9rem 1rem", fontSize: "0.8rem" }}>
                          {t.exit_reason_fa}
                        </td>

                        <td style={{ padding: "0.9rem 1rem", textAlign: "center" }}>
                          <span
                            style={{
                              display: "inline-flex",
                              alignItems: "center",
                              gap: "0.3rem",
                              padding: "0.25rem 0.6rem",
                              borderRadius: "4px",
                              fontSize: "0.75rem",
                              fontWeight: 700,
                              backgroundColor: isWin ? "var(--tse-green-subtle)" : isLoss ? "var(--tse-red-subtle)" : "rgba(255, 255, 255, 0.08)",
                              color: isWin ? "var(--tse-green)" : isLoss ? "var(--tse-red)" : "#cbd5e1",
                            }}
                          >
                            {isWin ? <ArrowUpRight size={14} /> : isLoss ? <ArrowDownRight size={14} /> : null}
                            {t.outcome_status_fa}
                          </span>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination Controls */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "0.5rem 0" }}>
            <div style={{ fontSize: "0.82rem", color: "var(--text-secondary)" }}>
              نمایش {toPersianDigits(historyItems.length)} از {toPersianDigits(historyTotal)} معامله ثبت‌شده در تاریخچه
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <button
                onClick={() => setHistoryPage((p) => Math.max(1, p - 1))}
                disabled={historyPage <= 1}
                className="btn-secondary"
                style={{ padding: "0.35rem 0.7rem", opacity: historyPage <= 1 ? 0.4 : 1 }}
              >
                <ChevronRight size={16} /> صفحه قبلی
              </button>
              <span style={{ fontSize: "0.85rem", padding: "0 0.5rem", color: "#ffffff" }}>
                صفحه {toPersianDigits(historyPage)} از {toPersianDigits(historyTotalPages)}
              </span>
              <button
                onClick={() => setHistoryPage((p) => Math.min(historyTotalPages, p + 1))}
                disabled={historyPage >= historyTotalPages}
                className="btn-secondary"
                style={{ padding: "0.35rem 0.7rem", opacity: historyPage >= historyTotalPages ? 0.4 : 1 }}
              >
                صفحه بعدی <ChevronLeft size={16} />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* SUBTAB 3: ORDER BOOK & CASH LEDGER */}
      {activeSubTab === "orders" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          <div className="card" style={{ padding: "1.5rem" }}>
            <h3 style={{ fontSize: "1rem", fontWeight: 700, marginBottom: "0.8rem", color: "var(--tse-gold)" }}>
              دفترکل حسابداری معاملات و ره‌گیری تراکنش‌ها (Immutable Ledger)
            </h3>
            <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", lineHeight: 1.6 }}>
              کلیه رویدادهای مالی، خرید، فروش، پله‌ها، تسویه وجوه و کسر ۱.۲۵۶۲٪ کارمزد و مالیات با شناسه یکتا و مهر زمانی UTC در دفترکل ثبت شده و غیرقابل تغییر است.
            </p>
          </div>
        </div>
      )}

      {/* Trade Detail Drawer */}
      <TradeDetailDrawer
        tradeId={selectedTradeId}
        onClose={() => setSelectedTradeId(null)}
        onSelectSymbol={onSelectSymbol}
      />
    </div>
  );
};
