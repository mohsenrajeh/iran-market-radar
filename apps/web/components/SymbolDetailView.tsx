"use client";
import React, { useState, useEffect } from "react";
import {
  LineChart,
  RefreshCw,
  TrendingUp,
  BarChart3,
  Activity,
  Layers,
  ShieldCheck,
  Zap,
  CheckCircle2,
  AlertTriangle,
  ArrowUpRight,
  ArrowDownRight,
} from "lucide-react";

interface SymbolDetailProps {
  initialSymbol?: string;
}

export const SymbolDetailView: React.FC<SymbolDetailProps> = ({ initialSymbol = "" }) => {
  const [selectedSymbol, setSelectedSymbol] = useState(initialSymbol);
  const [availableSymbols, setAvailableSymbols] = useState<string[]>(initialSymbol ? [initialSymbol] : []);
  const [chartData, setChartData] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [syncMsg, setSyncMsg] = useState<string | null>(null);

  // Overlay Toggles
  const [showEMA, setShowEMA] = useState(true);
  const [showBollinger, setShowBollinger] = useState(true);

  // Active Sub-Indicator Panel Tab
  const [activeIndicator, setActiveIndicator] = useState<"volume" | "rsi" | "macd" | "client_flow" | "orderbook" | "pivots">("client_flow");

  useEffect(() => {
    fetch("/api/v1/symbols")
      .then((res) => (res.ok ? res.json() : []))
      .then((rows) => {
        const symbols = Array.isArray(rows) ? rows.map((row: any) => row.ticker).filter(Boolean) : [];
        setAvailableSymbols(symbols);
        if (!selectedSymbol && symbols.length > 0) setSelectedSymbol(symbols[0]);
      })
      .catch(() => setAvailableSymbols(initialSymbol ? [initialSymbol] : []));
  }, [initialSymbol, selectedSymbol]);

  useEffect(() => {
    if (selectedSymbol) fetchChartData(selectedSymbol);
  }, [selectedSymbol]);

  const fetchChartData = async (sym: string) => {
    setLoading(true);
    setSyncMsg(null);
    try {
      const res = await fetch(`/api/v1/symbols/${encodeURIComponent(sym)}/chart?limit=60`);
      if (res.ok) {
        const data = await res.json();
        setChartData(data);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleSyncLive = async () => {
    setSyncing(true);
    setSyncMsg(null);
    try {
      const res = await fetch(`/api/v1/symbols/${encodeURIComponent(selectedSymbol)}/sync-live`, {
        method: "POST",
      });
      const data = await res.json();
      if (res.ok) {
        setSyncMsg(data.message || "داده‌های زنده با موفقیت از TSETMC بروزرسانی شد.");
        await fetchChartData(selectedSymbol);
      } else {
        setSyncMsg("خطا در برقراری ارتباط زنده با وب‌سرویس TSETMC.");
      }
    } catch (e) {
      setSyncMsg("خطا در ارسال درخواست همگام‌سازی زنده.");
    } finally {
      setSyncing(false);
    }
  };

  const bars = chartData?.bars || [];
  const latestBar = bars[bars.length - 1];
  const techAnalysis = chartData?.technical_analysis;
  const orderbook = chartData?.orderbook_depth || [];
  const pivots = techAnalysis?.pivot_points || {};

  // SVG Chart Dimensions & Scaling
  const width = 850;
  const height = 300;
  const paddingX = 35;
  const paddingY = 25;

  const minPrice = bars.length > 0 ? Math.min(...bars.map((b: any) => b.low)) * 0.98 : 0;
  const maxPrice = bars.length > 0 ? Math.max(...bars.map((b: any) => b.high)) * 1.02 : 1;

  const getX = (index: number) => paddingX + (index * (width - 2 * paddingX)) / Math.max(1, bars.length - 1);
  const getY = (price: number) => height - paddingY - ((price - minPrice) / Math.max(1, maxPrice - minPrice)) * (height - 2 * paddingY);

  // Sub-panel dimension
  const subHeight = 120;
  const getSubY = (val: number, minVal: number, maxVal: number) =>
    subHeight - 15 - ((val - minVal) / Math.max(1e-6, maxVal - minVal)) * (subHeight - 30);

  // Price change calculations
  const priceChange = latestBar ? latestBar.last - latestBar.open : 0;
  const priceChangePct = latestBar && latestBar.open > 0 ? (priceChange / latestBar.open) * 100 : 0;
  const isUpToday = priceChangePct >= 0;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
      {/* 1. Symbol Selector & Live TSETMC Toolbar */}
      <div className="card-panel" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <div style={{ width: "36px", height: "36px", borderRadius: "8px", backgroundColor: "rgba(46, 160, 67, 0.2)", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--tse-green)" }}>
            <LineChart size={22} />
          </div>
          <div>
            <h2 style={{ fontSize: "1.1rem", fontWeight: 800, color: "var(--text-primary)" }}>
              دیده‌بان تحلیلی نماد {chartData?.name_fa || selectedSymbol} ({selectedSymbol})
            </h2>
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "0.15rem" }}>
              بازار: {chartData?.market || "بورس تهران"} • صنعت: {chartData?.sector || "فلزات اساسی"}
            </div>
          </div>
        </div>

        {/* Live Status Indicator */}
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <span style={{
            backgroundColor: "var(--tse-green-subtle)",
            color: "var(--tse-green)",
            border: "1px solid rgba(46, 160, 67, 0.3)",
            borderRadius: "var(--radius-sm)",
            padding: "0.35rem 0.75rem",
            fontSize: "0.78rem",
            fontWeight: 700,
            display: "flex",
            alignItems: "center",
            gap: "0.35rem",
          }}>
            <span style={{ width: "8px", height: "8px", borderRadius: "50%", backgroundColor: "var(--tse-green)", display: "inline-block" }}></span>
            <span>{chartData ? "داده رسمی نمودار بارگذاری شده" : "داده رسمی در دسترس نیست"}</span>
          </span>
        </div>
      </div>

      {/* Symbol Fast Selector Buttons */}
      <div style={{ display: "flex", gap: "0.35rem", flexWrap: "wrap" }}>
        {availableSymbols.map((sym) => (
          <button
            key={sym}
            onClick={() => setSelectedSymbol(sym)}
            style={{
              backgroundColor: selectedSymbol === sym ? "var(--tse-green)" : "var(--bg-surface)",
              color: selectedSymbol === sym ? "#fff" : "var(--text-secondary)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-sm)",
              padding: "0.35rem 0.8rem",
              fontWeight: selectedSymbol === sym ? 800 : 500,
              fontSize: "0.82rem",
              cursor: "pointer",
              fontFamily: "inherit",
              transition: "all 0.15s ease",
            }}
          >
            {sym}
          </button>
        ))}
      </div>

      {/* 2. Key Live Metrics Cards Row */}
      {latestBar && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "0.85rem" }}>
          <div className="card-panel">
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>آخرین قیمت معامله</div>
            <div style={{ fontSize: "1.45rem", fontWeight: 800, color: "var(--text-primary)", marginTop: "0.2rem" }} className="tabular-num">
              {latestBar.last?.toLocaleString("fa-IR")} <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>ریال</span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "0.2rem", fontSize: "0.78rem", color: isUpToday ? "var(--tse-green)" : "var(--tse-red)", fontWeight: 700, marginTop: "0.25rem" }}>
              {isUpToday ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
              <span className="tabular-num">{isUpToday ? "+" : ""}{priceChangePct.toFixed(2)}٪ ({priceChange.toLocaleString("fa-IR")})</span>
            </div>
          </div>

          <div className="card-panel">
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>قیمت پایانی (حجم مبنا)</div>
            <div style={{ fontSize: "1.45rem", fontWeight: 800, color: "var(--tse-blue)", marginTop: "0.2rem" }} className="tabular-num">
              {latestBar.close?.toLocaleString("fa-IR")} <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>ریال</span>
            </div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "0.25rem" }}>
              دامنه روز: <span className="tabular-num">{latestBar.allowed_min?.toLocaleString("fa-IR")}</span> تا <span className="tabular-num">{latestBar.allowed_max?.toLocaleString("fa-IR")}</span>
            </div>
          </div>

          <div className="card-panel">
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>قدرت خریدار حقیقی (تابلوخوانی)</div>
            <div style={{ fontSize: "1.45rem", fontWeight: 800, color: latestBar.real_buy_power_ratio != null && latestBar.real_buy_power_ratio >= 1.2 ? "var(--tse-green)" : "var(--text-primary)", marginTop: "0.2rem" }} className="tabular-num">
              {latestBar.real_buy_power_ratio ?? "—"} <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>برابر فروشنده</span>
            </div>
            <div style={{ fontSize: "0.75rem", color: latestBar.net_real_inflow != null && latestBar.net_real_inflow >= 0 ? "var(--tse-green)" : "var(--tse-red)", marginTop: "0.25rem" }} className="tabular-num">
              خالص ورود پول: {latestBar.net_real_inflow != null ? `${(latestBar.net_real_inflow / 1_000_000_000).toLocaleString("fa-IR", { maximumFractionDigits: 1 })} میلیارد ریال` : "—"}
            </div>
          </div>

          <div className="card-panel">
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>ارزش معاملات امروز</div>
            <div style={{ fontSize: "1.45rem", fontWeight: 800, color: "var(--text-primary)", marginTop: "0.2rem" }} className="tabular-num">
              {latestBar.value != null ? (latestBar.value / 1_000_000_000).toLocaleString("fa-IR", { maximumFractionDigits: 0 }) : "—"} <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>میلیارد ریال</span>
            </div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "0.25rem" }}>
              حجم: <span className="tabular-num">{latestBar.volume != null ? (latestBar.volume / 1_000_000).toLocaleString("fa-IR", { maximumFractionDigits: 1 }) : "—"}</span> میلیون برگه سهم
            </div>
          </div>
        </div>
      )}

      {/* 3. Main Candlestick Chart Panel with Overlay Controls */}
      <div className="card-panel">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem", flexWrap: "wrap", gap: "0.5rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <span style={{ fontWeight: 800, fontSize: "0.95rem" }}>
              نمودار قیمتی و میانگین‌های متحرک ۶۰ روز گذشته (واحد: ریال)
            </span>
          </div>

          {/* Indicator Overlay Checkboxes */}
          <div style={{ display: "flex", alignItems: "center", gap: "1rem", fontSize: "0.8rem" }}>
            <label style={{ display: "flex", alignItems: "center", gap: "0.35rem", cursor: "pointer", color: "var(--text-secondary)" }}>
              <input type="checkbox" checked={showEMA} onChange={(e) => setShowEMA(e.target.checked)} />
              <span style={{ color: "#f0883e", fontWeight: 600 }}>EMA 20</span> / <span style={{ color: "#58a6ff", fontWeight: 600 }}>50</span> / <span style={{ color: "#bc8cff", fontWeight: 600 }}>100</span>
            </label>

            <label style={{ display: "flex", alignItems: "center", gap: "0.35rem", cursor: "pointer", color: "var(--text-secondary)" }}>
              <input type="checkbox" checked={showBollinger} onChange={(e) => setShowBollinger(e.target.checked)} />
              <span style={{ color: "#79c0ff", fontWeight: 600 }}>باند بولینگر (20, 2)</span>
            </label>
          </div>
        </div>

        {/* SVG Rendered Multi-Indicator Price Chart */}
        <div style={{ width: "100%", overflowX: "auto" }}>
          <svg viewBox={`0 0 ${width} ${height}`} style={{ width: "100%", height: "300px", backgroundColor: "var(--bg-surface)", borderRadius: "var(--radius-sm)" }}>
            {/* Grid lines */}
            {[0.2, 0.4, 0.6, 0.8].map((fraction, i) => {
              const y = paddingY + fraction * (height - 2 * paddingY);
              const p = maxPrice - fraction * (maxPrice - minPrice);
              return (
                <g key={i}>
                  <line x1={paddingX} y1={y} x2={width - paddingX} y2={y} stroke="var(--border-subtle)" strokeDasharray="3 3" />
                  <text x={width - paddingX + 5} y={y + 4} fill="var(--text-muted)" fontSize="9" fontFamily="Vazirmatn">
                    {Math.round(p).toLocaleString("fa-IR")}
                  </text>
                </g>
              );
            })}

            {/* Bollinger Bands Shaded Area & Lines */}
            {showBollinger && bars.length > 1 && (
              <>
                <path
                  d={
                    bars.map((b: any, i: number) => `${i === 0 ? "M" : "L"} ${getX(i)} ${getY(b.bb_upper || b.close)}`).join(" ") +
                    " " +
                    bars.slice().reverse().map((b: any, i: number) => `L ${getX(bars.length - 1 - i)} ${getY(b.bb_lower || b.close)}`).join(" ") +
                    " Z"
                  }
                  fill="rgba(56, 139, 253, 0.08)"
                />
                <path
                  d={bars.map((b: any, i: number) => `${i === 0 ? "M" : "L"} ${getX(i)} ${getY(b.bb_upper || b.close)}`).join(" ")}
                  fill="none"
                  stroke="rgba(88, 166, 255, 0.4)"
                  strokeWidth="1"
                  strokeDasharray="2 2"
                />
                <path
                  d={bars.map((b: any, i: number) => `${i === 0 ? "M" : "L"} ${getX(i)} ${getY(b.bb_lower || b.close)}`).join(" ")}
                  fill="none"
                  stroke="rgba(88, 166, 255, 0.4)"
                  strokeWidth="1"
                  strokeDasharray="2 2"
                />
              </>
            )}

            {/* EMA Overlay Lines */}
            {showEMA && bars.length > 1 && (
              <>
                {/* EMA 20 */}
                <path
                  d={bars.map((b: any, i: number) => `${i === 0 ? "M" : "L"} ${getX(i)} ${getY(b.ema_20 || b.close)}`).join(" ")}
                  fill="none"
                  stroke="#f0883e"
                  strokeWidth="1.6"
                />
                {/* EMA 50 */}
                <path
                  d={bars.map((b: any, i: number) => `${i === 0 ? "M" : "L"} ${getX(i)} ${getY(b.ema_50 || b.close)}`).join(" ")}
                  fill="none"
                  stroke="#58a6ff"
                  strokeWidth="1.6"
                />
                {/* EMA 100 */}
                <path
                  d={bars.map((b: any, i: number) => `${i === 0 ? "M" : "L"} ${getX(i)} ${getY(b.ema_100 || b.close)}`).join(" ")}
                  fill="none"
                  stroke="#bc8cff"
                  strokeWidth="1.4"
                  strokeDasharray="4 2"
                />
              </>
            )}

            {/* Candlesticks */}
            {bars.map((b: any, idx: number) => {
              const x = getX(idx);
              const isUp = b.close >= b.open;
              const candleColor = isUp ? "#2ea043" : "#f85149";
              const openY = getY(b.open);
              const closeY = getY(b.close);
              const highY = getY(b.high);
              const lowY = getY(b.low);

              const candleTop = Math.min(openY, closeY);
              const candleHeight = Math.max(2, Math.abs(openY - closeY));

              return (
                <g key={idx}>
                  {/* High-Low Wick */}
                  <line x1={x} y1={highY} x2={x} y2={lowY} stroke={candleColor} strokeWidth="1.2" />
                  {/* Real Body */}
                  <rect
                    x={x - 3.5}
                    y={candleTop}
                    width="7"
                    height={candleHeight}
                    fill={candleColor}
                    rx="1"
                  />
                </g>
              );
            })}
          </svg>
        </div>
      </div>

      {/* 4. Secondary Technical Indicator Tabs & Multi-Panel Workspace */}
      <div className="card-panel" style={{ padding: "1.25rem" }}>
        {/* Indicator Sub-tabs */}
        <div style={{ display: "flex", gap: "0.4rem", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "0.75rem", marginBottom: "1rem", flexWrap: "wrap" }}>
          {[
            { id: "client_flow", label: "تابلوخوانی و جریان پول حقیقی", icon: Zap },
            { id: "rsi", label: "اسیلاتور RSI (14)", icon: Activity },
            { id: "macd", label: "اندیکاتور MACD (12, 26, 9)", icon: TrendingUp },
            { id: "volume", label: "حجم و میانگین حجم ۲۰ روزه", icon: BarChart3 },
            { id: "orderbook", label: "عمق مظنه ۵ سطحی", icon: Layers },
            { id: "pivots", label: "سطوح پیوت پوینت (Pivot S/R)", icon: ShieldCheck },
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = activeIndicator === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveIndicator(tab.id as any)}
                style={{
                  backgroundColor: isActive ? "var(--bg-surface)" : "transparent",
                  color: isActive ? "var(--text-primary)" : "var(--text-muted)",
                  border: `1px solid ${isActive ? "var(--border-active)" : "transparent"}`,
                  borderRadius: "var(--radius-sm)",
                  padding: "0.4rem 0.8rem",
                  fontSize: "0.82rem",
                  fontWeight: isActive ? 700 : 500,
                  display: "flex",
                  alignItems: "center",
                  gap: "0.4rem",
                  cursor: "pointer",
                  fontFamily: "inherit",
                }}
              >
                <Icon size={15} color={isActive ? "var(--tse-green)" : "var(--text-muted)"} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* Panel Content based on Active Tab */}

        {/* Sub-Panel: Client Flow (حقیقی و حقوقی) */}
        {activeIndicator === "client_flow" && (
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.5rem", fontSize: "0.82rem" }}>
              <span style={{ fontWeight: 700 }}>نمودار سرانه خریدار حقیقی به فروشنده و ورود پول هوشمند</span>
              <span style={{ color: "var(--tse-green)", fontWeight: 700 }}>
                قدرت جاری: {latestBar?.real_buy_power_ratio != null ? `${latestBar.real_buy_power_ratio} برابر` : "—"}
              </span>
            </div>

            <div style={{ width: "100%", overflowX: "auto" }}>
              <svg viewBox={`0 0 ${width} ${subHeight}`} style={{ width: "100%", height: "120px", backgroundColor: "var(--bg-surface)", borderRadius: "4px" }}>
                {/* 1.0 Baseline */}
                <line x1={paddingX} y1={subHeight / 2} x2={width - paddingX} y2={subHeight / 2} stroke="rgba(255,255,255,0.2)" strokeDasharray="2 2" />
                <text x={width - paddingX + 5} y={subHeight / 2 + 4} fill="var(--text-muted)" fontSize="9" fontFamily="Vazirmatn">1.0X</text>

                {bars.map((b: any, idx: number) => {
                  if (b.real_buy_power_ratio == null) return null;
                  const x = getX(idx);
                  const bp = b.real_buy_power_ratio;
                  const barColor = bp >= 1.2 ? "#2ea043" : bp >= 0.9 ? "#58a6ff" : "#f85149";
                  const barH = Math.min(50, Math.abs(bp - 1.0) * 35);
                  const isAbove = bp >= 1.0;
                  const y = isAbove ? subHeight / 2 - barH : subHeight / 2;

                  return (
                    <rect
                      key={idx}
                      x={x - 3}
                      y={y}
                      width="6"
                      height={Math.max(2, barH)}
                      fill={barColor}
                      rx="1"
                    />
                  );
                })}
              </svg>
            </div>
          </div>
        )}

        {/* Sub-Panel: RSI (14) */}
        {activeIndicator === "rsi" && (
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.5rem", fontSize: "0.82rem" }}>
              <span style={{ fontWeight: 700 }}>اسیلاتور شاخص قدرت نسبی (RSI 14)</span>
              <span style={{ color: latestBar?.rsi_14 != null && latestBar.rsi_14 >= 70 ? "var(--tse-red)" : latestBar?.rsi_14 != null && latestBar.rsi_14 <= 30 ? "var(--tse-green)" : "var(--text-primary)", fontWeight: 700 }}>
                RSI: {latestBar?.rsi_14 ?? "—"}
              </span>
            </div>

            <div style={{ width: "100%", overflowX: "auto" }}>
              <svg viewBox={`0 0 ${width} ${subHeight}`} style={{ width: "100%", height: "120px", backgroundColor: "var(--bg-surface)", borderRadius: "4px" }}>
                {/* 70 Level */}
                <line x1={paddingX} y1={getSubY(70, 0, 100)} x2={width - paddingX} y2={getSubY(70, 0, 100)} stroke="rgba(248, 81, 73, 0.4)" strokeDasharray="3 3" />
                <text x={width - paddingX + 5} y={getSubY(70, 0, 100) + 4} fill="var(--tse-red)" fontSize="9" fontFamily="Vazirmatn">70</text>

                {/* 30 Level */}
                <line x1={paddingX} y1={getSubY(30, 0, 100)} x2={width - paddingX} y2={getSubY(30, 0, 100)} stroke="rgba(46, 160, 67, 0.4)" strokeDasharray="3 3" />
                <text x={width - paddingX + 5} y={getSubY(30, 0, 100) + 4} fill="var(--tse-green)" fontSize="9" fontFamily="Vazirmatn">30</text>

                {/* RSI Line */}
                <path
                  d={bars.reduce((path: string, b: any, i: number) => b.rsi_14 == null ? path : `${path ? `${path} L` : "M"} ${getX(i)} ${getSubY(b.rsi_14, 0, 100)}`, "")}
                  fill="none"
                  stroke="#a371f7"
                  strokeWidth="1.8"
                />
              </svg>
            </div>
          </div>
        )}

        {/* Sub-Panel: MACD */}
        {activeIndicator === "macd" && (
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.5rem", fontSize: "0.82rem" }}>
              <span style={{ fontWeight: 700 }}>اندیکاتور MACD (12, 26, 9) و هیستوگرام</span>
              <span style={{ color: "var(--text-secondary)" }}>
                MACD: <strong style={{ color: "#58a6ff" }}>{latestBar?.macd ?? "—"}</strong> | Signal: <strong style={{ color: "#f0883e" }}>{latestBar?.macd_signal ?? "—"}</strong>
              </span>
            </div>

            <div style={{ width: "100%", overflowX: "auto" }}>
              <svg viewBox={`0 0 ${width} ${subHeight}`} style={{ width: "100%", height: "120px", backgroundColor: "var(--bg-surface)", borderRadius: "4px" }}>
                {/* Zero line */}
                <line x1={paddingX} y1={subHeight / 2} x2={width - paddingX} y2={subHeight / 2} stroke="rgba(255,255,255,0.2)" strokeDasharray="2 2" />

                {/* Histogram Bars */}
                {bars.map((b: any, idx: number) => {
                  const x = getX(idx);
                  const h = b.macd_hist || 0;
                  const barColor = h >= 0 ? "#2ea043" : "#f85149";
                  const barHeight = Math.min(45, Math.abs(h) * 1.5);
                  const y = h >= 0 ? subHeight / 2 - barHeight : subHeight / 2;

                  return (
                    <rect
                      key={idx}
                      x={x - 2.5}
                      y={y}
                      width="5"
                      height={Math.max(1, barHeight)}
                      fill={barColor}
                    />
                  );
                })}

                {/* MACD Line */}
                <path
                  d={bars.map((b: any, i: number) => `${i === 0 ? "M" : "L"} ${getX(i)} ${subHeight / 2 - Math.max(-45, Math.min(45, (b.macd || 0) * 1.5))}`).join(" ")}
                  fill="none"
                  stroke="#58a6ff"
                  strokeWidth="1.5"
                />

                {/* Signal Line */}
                <path
                  d={bars.map((b: any, i: number) => `${i === 0 ? "M" : "L"} ${getX(i)} ${subHeight / 2 - Math.max(-45, Math.min(45, (b.macd_signal || 0) * 1.5))}`).join(" ")}
                  fill="none"
                  stroke="#f0883e"
                  strokeWidth="1.5"
                />
              </svg>
            </div>
          </div>
        )}

        {/* Sub-Panel: Volume */}
        {activeIndicator === "volume" && (
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.5rem", fontSize: "0.82rem" }}>
              <span style={{ fontWeight: 700 }}>حجم معاملات روزانه و میانگین متحرک حجم ۲۰ روزه</span>
              <span style={{ color: "var(--text-secondary)" }}>
                حجم امروز: {((latestBar?.volume || 0) / 1_000_000).toFixed(1)}M
              </span>
            </div>

            <div style={{ width: "100%", overflowX: "auto" }}>
              <svg viewBox={`0 0 ${width} ${subHeight}`} style={{ width: "100%", height: "120px", backgroundColor: "var(--bg-surface)", borderRadius: "4px" }}>
                {(() => {
                  const maxVol = Math.max(...bars.map((b: any) => b.volume || 1), 1);
                  return bars.map((b: any, idx: number) => {
                    const x = getX(idx);
                    const isUp = b.close >= b.open;
                    const barH = ((b.volume || 0) / maxVol) * (subHeight - 20);
                    return (
                      <rect
                        key={idx}
                        x={x - 3}
                        y={subHeight - barH - 5}
                        width="6"
                        height={Math.max(2, barH)}
                        fill={isUp ? "rgba(46, 160, 67, 0.7)" : "rgba(248, 81, 73, 0.7)"}
                        rx="1"
                      />
                    );
                  });
                })()}
              </svg>
            </div>
          </div>
        )}

        {/* Sub-Panel: 5-Level Orderbook Depth */}
        {activeIndicator === "orderbook" && (
          <div>
            <div style={{ fontWeight: 700, fontSize: "0.85rem", marginBottom: "0.6rem" }}>
              عمق ۵ مظنه برتر عرضه و تقاضا (Order Book Depth)
            </div>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.82rem" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border-subtle)", color: "var(--text-muted)", textAlign: "right" }}>
                  <th style={{ padding: "0.4rem" }}>تعداد خریدار</th>
                  <th style={{ padding: "0.4rem" }}>حجم تقاضا (Buy)</th>
                  <th style={{ padding: "0.4rem" }}>قیمت خرید</th>
                  <th style={{ padding: "0.4rem" }}>قیمت فروش</th>
                  <th style={{ padding: "0.4rem" }}>حجم عرضه (Sell)</th>
                  <th style={{ padding: "0.4rem" }}>تعداد فروشنده</th>
                </tr>
              </thead>
              <tbody>
                {orderbook.map((row: any, idx: number) => (
                  <tr key={idx} style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                    <td style={{ padding: "0.5rem", color: "var(--text-muted)" }}>{row.bid_count}</td>
                    <td style={{ padding: "0.5rem", color: "var(--tse-green)", fontWeight: 700 }} className="tabular-num">
                      {row.bid_volume?.toLocaleString("fa-IR")}
                    </td>
                    <td style={{ padding: "0.5rem", color: "var(--tse-green)", fontWeight: 800 }} className="tabular-num">
                      {row.bid_price?.toLocaleString("fa-IR")}
                    </td>
                    <td style={{ padding: "0.5rem", color: "var(--tse-red)", fontWeight: 800 }} className="tabular-num">
                      {row.ask_price?.toLocaleString("fa-IR")}
                    </td>
                    <td style={{ padding: "0.5rem", color: "var(--tse-red)", fontWeight: 700 }} className="tabular-num">
                      {row.ask_volume?.toLocaleString("fa-IR")}
                    </td>
                    <td style={{ padding: "0.5rem", color: "var(--text-muted)" }}>{row.ask_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Sub-Panel: Pivots & Key Support/Resistance */}
        {activeIndicator === "pivots" && (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
            <div style={{ backgroundColor: "var(--bg-surface)", padding: "0.75rem", borderRadius: "4px" }}>
              <div style={{ fontWeight: 700, fontSize: "0.85rem", color: "var(--tse-green)", marginBottom: "0.5rem" }}>
                سطوح حمایتی Floor Pivots (ریال):
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.35rem", fontSize: "0.8rem" }}>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span>نقطه پیوت مبنا (Pivot):</span>
                  <span className="tabular-num" style={{ fontWeight: 700 }}>{pivots.pivot?.toLocaleString("fa-IR")}</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span>حمایت اول (S1):</span>
                  <span className="tabular-num" style={{ color: "var(--tse-green)", fontWeight: 700 }}>{pivots.s1?.toLocaleString("fa-IR")}</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span>حمایت دوم (S2):</span>
                  <span className="tabular-num" style={{ color: "var(--tse-green)", fontWeight: 700 }}>{pivots.s2?.toLocaleString("fa-IR")}</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span>حمایت سوم (S3):</span>
                  <span className="tabular-num" style={{ color: "var(--tse-green)", fontWeight: 700 }}>{pivots.s3?.toLocaleString("fa-IR")}</span>
                </div>
              </div>
            </div>

            <div style={{ backgroundColor: "var(--bg-surface)", padding: "0.75rem", borderRadius: "4px" }}>
              <div style={{ fontWeight: 700, fontSize: "0.85rem", color: "var(--tse-red)", marginBottom: "0.5rem" }}>
                سطوح مقاومتی Floor Pivots (ریال):
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.35rem", fontSize: "0.8rem" }}>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span>مقاومت اول (R1):</span>
                  <span className="tabular-num" style={{ color: "var(--tse-red)", fontWeight: 700 }}>{pivots.r1?.toLocaleString("fa-IR")}</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span>مقاومت دوم (R2):</span>
                  <span className="tabular-num" style={{ color: "var(--tse-red)", fontWeight: 700 }}>{pivots.r2?.toLocaleString("fa-IR")}</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span>مقاومت سوم (R3):</span>
                  <span className="tabular-num" style={{ color: "var(--tse-red)", fontWeight: 700 }}>{pivots.r3?.toLocaleString("fa-IR")}</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 5. Comprehensive AI & Technical Analysis Dashboard */}
      {techAnalysis && (
        <div className="card-panel" style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-subtle)" }}>
          <div style={{ fontWeight: 800, fontSize: "0.95rem", marginBottom: "0.75rem", display: "flex", alignItems: "center", gap: "0.4rem" }}>
            <Zap size={18} color="var(--tse-amber)" />
            <span>خلاصه جامع تحلیل تکنیکال، تابلوخوانی و سیگنال‌های هوش مصنوعی نماد {selectedSymbol}</span>
          </div>

          {/* Badges */}
          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginBottom: "0.85rem" }}>
            <span style={{ backgroundColor: "rgba(46, 160, 67, 0.15)", color: "var(--tse-green)", padding: "0.25rem 0.6rem", borderRadius: "4px", fontSize: "0.78rem", fontWeight: 700 }}>
              {techAnalysis.trend_badge}
            </span>
            <span style={{ backgroundColor: "rgba(88, 166, 255, 0.15)", color: "var(--tse-blue)", padding: "0.25rem 0.6rem", borderRadius: "4px", fontSize: "0.78rem", fontWeight: 700 }}>
              {techAnalysis.rsi_badge}
            </span>
            <span style={{ backgroundColor: "rgba(163, 113, 247, 0.15)", color: "#a371f7", padding: "0.25rem 0.6rem", borderRadius: "4px", fontSize: "0.78rem", fontWeight: 700 }}>
              {techAnalysis.macd_badge}
            </span>
            <span style={{ backgroundColor: "rgba(210, 153, 34, 0.15)", color: "var(--tse-amber)", padding: "0.25rem 0.6rem", borderRadius: "4px", fontSize: "0.78rem", fontWeight: 700 }}>
              {techAnalysis.flow_badge}
            </span>
          </div>

          {/* Persian Explanations List */}
          <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem" }}>
            {techAnalysis.key_reasons_fa?.map((r: string, idx: number) => (
              <div key={idx} style={{ fontSize: "0.82rem", color: "var(--text-secondary)", display: "flex", alignItems: "center", gap: "0.4rem" }}>
                <CheckCircle2 size={14} color="var(--tse-green)" style={{ flexShrink: 0 }} />
                <span>{r}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
