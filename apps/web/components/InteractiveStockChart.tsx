"use client";
import React, { useState, useMemo } from "react";
import {
  TrendingUp,
  TrendingDown,
  Layers,
  Sliders,
  Clock,
  ShieldCheck,
  AlertTriangle,
  Award,
  Sparkles,
  ArrowUpRight,
  ArrowDownRight,
  Activity,
  Zap,
  Info,
  Target,
  ShieldAlert,
} from "lucide-react";
import { toPersianDigits } from "../lib/formatters";

export interface Bar {
  trading_date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  yesterday_price?: number;
  volume: number;
  value?: number;
  corporate_action?: string | null;
  stage_entry?: { stage: 1 | 2 | 3; pct: number; qty: number; price: number } | null;
  exit_marker?: { type: "target1" | "target2" | "trailing_stop" | "stop_loss" | "manual"; price: number } | null;
}

interface InteractiveStockChartProps {
  symbol: string;
  nameFa?: string;
  bars: Bar[];
  plannedEntry?: number;
  avgFillPrice?: number;
  orderLimit?: number;
  target1?: number;
  target2?: number;
  stopLoss?: number;
  isGoodStock?: boolean;
  sellAdvicePrice?: number;
  rsiValue?: number;
  marketRegime?: string;
  chaseLimitR?: number; // max allowable chase before blocking (default 0.35 R)
  timeframe?: "1D" | "60m" | "15m";
}

export const InteractiveStockChart: React.FC<InteractiveStockChartProps> = ({
  symbol,
  nameFa,
  bars,
  plannedEntry,
  avgFillPrice,
  orderLimit,
  target1,
  target2,
  stopLoss,
  isGoodStock = true,
  sellAdvicePrice,
  rsiValue = 58.4,
  marketRegime = "risk_on",
  chaseLimitR = 0.35,
}) => {
  const [selectedTimeframe, setSelectedTimeframe] = useState<"1D" | "60m" | "15m">("1D");
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);
  const [showEMA, setShowEMA] = useState(true);
  const [showPriceLines, setShowPriceLines] = useState(true);
  const [showRiskRewardZones, setShowRiskRewardZones] = useState(true);
  const [showVolume, setShowVolume] = useState(true);
  const [showRSI, setShowRSI] = useState(true);
  const [showTradeMarkers, setShowTradeMarkers] = useState(true);

  // Take the last 40 bars for optimal institutional visual clarity
  const data: Bar[] = useMemo(() => {
    if (!bars || !Array.isArray(bars) || bars.length === 0) return [];
    return bars.slice(-40);
  }, [bars]);

  // Compute EMA 9 and EMA 21
  const emaData = useMemo(() => {
    if (data.length === 0) return { ema9: [], ema21: [] };
    const calcEMA = (period: number) => {
      const k = 2 / (period + 1);
      const res: (number | null)[] = [];
      let prev: number | null = null;
      for (let i = 0; i < data.length; i++) {
        const c = data[i].close;
        if (i < period - 1) {
          res.push(null);
        } else if (prev === null) {
          const sum = data.slice(0, period).reduce((a, b) => a + b.close, 0);
          prev = sum / period;
          res.push(prev);
        } else {
          prev = c * k + prev * (1 - k);
          res.push(prev);
        }
      }
      return res;
    };
    return {
      ema9: calcEMA(9),
      ema21: calcEMA(21),
    };
  }, [data]);

  // Compute live RSI array for the pane
  const rsiSeries = useMemo(() => {
    if (data.length < 14) return data.map(() => rsiValue);
    const gains: number[] = [];
    const losses: number[] = [];
    for (let i = 1; i < data.length; i++) {
      const diff = data[i].close - data[i - 1].close;
      gains.push(diff > 0 ? diff : 0);
      losses.push(diff < 0 ? Math.abs(diff) : 0);
    }
    const rsiArr: number[] = [rsiValue];
    let avgGain = gains.slice(0, 14).reduce((a, b) => a + b, 0) / 14;
    let avgLoss = losses.slice(0, 14).reduce((a, b) => a + b, 0) / 14;
    
    for (let i = 14; i < data.length; i++) {
      const g = gains[i - 1] || 0;
      const l = losses[i - 1] || 0;
      avgGain = (avgGain * 13 + g) / 14;
      avgLoss = (avgLoss * 13 + l) / 14;
      const rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
      const val = 100 - (100 / (1 + rs));
      rsiArr.push(Math.min(95, Math.max(15, Math.round(val * 10) / 10)));
    }
    while (rsiArr.length < data.length) {
      rsiArr.unshift(rsiValue);
    }
    return rsiArr.slice(-data.length);
  }, [data, rsiValue]);

  // Dimensions & Multi-Pane Layout
  const svgWidth = 1040;
  const candlePaneTop = 25;
  const candlePaneHeight = 280;
  
  const volPaneTop = candlePaneTop + candlePaneHeight + 15;
  const volPaneHeight = showVolume ? 60 : 0;
  
  const rsiPaneTop = volPaneTop + volPaneHeight + (showVolume ? 15 : 10);
  const rsiPaneHeight = showRSI ? 75 : 0;
  
  const totalHeight = rsiPaneTop + rsiPaneHeight + 35;
  const leftPadding = 80;
  const rightPadding = 195; // Gutter for labels on right price scale
  const chartW = svgWidth - leftPadding - rightPadding;

  // Active prices evaluation
  const latestClose = data.length > 0 ? data[data.length - 1].close : 5000;
  const effectiveEntry = avgFillPrice || plannedEntry || latestClose;
  const isFilled = Boolean(avgFillPrice && avgFillPrice > 0);

  // Compute Risk / Reward from active entry (avgFillPrice if filled, plannedEntry if pending)
  const calcStop = stopLoss || Math.round(effectiveEntry * 0.945);
  const calcT1 = target1 || Math.round(effectiveEntry * 1.075);
  const calcT2 = target2 || Math.round(effectiveEntry * 1.145);

  const initialRiskRials = Math.max(1, Math.abs(effectiveEntry - calcStop));
  const reward1Rials = Math.max(1, calcT1 - effectiveEntry);
  const reward2Rials = Math.max(1, calcT2 - effectiveEntry);
  const rMultipleT1 = toPersianDigits((reward1Rials / initialRiskRials).toFixed(1));
  const rMultipleT2 = toPersianDigits((reward2Rials / initialRiskRials).toFixed(1));

  // Chase Check: Is price currently higher than planned entry by more than chaseLimitR * risk?
  const maxChasePrice = plannedEntry ? plannedEntry + (initialRiskRials * chaseLimitR) : effectiveEntry * 1.02;
  const isChaseBlocked = Boolean(!isFilled && plannedEntry && latestClose > maxChasePrice);

  // Price Scale Bounds (Tight & Institutional, accounting for candles and active levels)
  const allPrices = useMemo(() => {
    const pList = data.flatMap((b) => [b.high || b.close, b.low || b.close, b.close]);
    if (showPriceLines) {
      if (effectiveEntry > 0) pList.push(effectiveEntry);
      if (calcT1 > 0) pList.push(calcT1);
      if (calcT2 > 0) pList.push(calcT2);
      if (calcStop > 0) pList.push(calcStop);
      if (sellAdvicePrice && sellAdvicePrice > 0) pList.push(sellAdvicePrice);
    }
    return pList.filter((p) => typeof p === "number" && !isNaN(p) && p > 0);
  }, [data, effectiveEntry, calcT1, calcT2, calcStop, sellAdvicePrice, showPriceLines]);

  const rawMin = allPrices.length > 0 ? Math.min(...allPrices) : 5000;
  const rawMax = allPrices.length > 0 ? Math.max(...allPrices) : 8000;
  const priceMargin = (rawMax - rawMin) * 0.06 || 100;
  const minPrice = rawMin - priceMargin;
  const maxPrice = rawMax + priceMargin;
  const priceRange = maxPrice - minPrice || 1;

  // Coordinate mappers
  const getPriceY = (val: number) => {
    return candlePaneTop + (1 - (val - minPrice) / priceRange) * candlePaneHeight;
  };

  const barCount = data.length || 1;
  const barSlot = chartW / barCount;
  const barWidth = Math.max(8, Math.min(18, barSlot * 0.68));
  const getBarX = (i: number) => leftPadding + i * barSlot + barSlot / 2;

  // Volume scale
  const maxVol = Math.max(...data.map((b) => b.volume || 1), 1);
  const getVolY = (vol: number) => {
    const normalized = (vol / maxVol) * volPaneHeight;
    return volPaneTop + volPaneHeight - normalized;
  };

  // RSI scale (0 to 100)
  const getRsiY = (val: number) => {
    const clamped = Math.min(100, Math.max(0, val));
    return rsiPaneTop + (1 - clamped / 100) * rsiPaneHeight;
  };

  const activeBar = hoveredIdx !== null && data[hoveredIdx] ? data[hoveredIdx] : data[data.length - 1];
  const activeEma9 = hoveredIdx !== null && emaData.ema9[hoveredIdx] ? emaData.ema9[hoveredIdx] : emaData.ema9[emaData.ema9.length - 1];
  const activeEma21 = hoveredIdx !== null && emaData.ema21[hoveredIdx] ? emaData.ema21[hoveredIdx] : emaData.ema21[emaData.ema21.length - 1];
  const activeRsi = hoveredIdx !== null ? rsiSeries[hoveredIdx] : rsiSeries[rsiSeries.length - 1];

  const formatFa = (n?: number | null) => {
    if (n === undefined || n === null || isNaN(n)) return "—";
    return Math.round(n).toLocaleString("fa-IR");
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", width: "100%", direction: "rtl" }}>
      {/* ── 1. Top Control Strip & Live Crosshair Telemetry ──────────────── */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "0.75rem",
          backgroundColor: "#131b2e",
          padding: "0.75rem 1.15rem",
          borderRadius: "10px",
          border: "1px solid #1e293b",
        }}
      >
        {/* Left (RTL Start): Live OHLC + Indicator Readouts */}
        <div style={{ display: "flex", alignItems: "center", gap: "1rem", flexWrap: "wrap", fontSize: "0.8rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
            <span style={{ fontWeight: 900, color: "#f8fafc", fontSize: "1.05rem" }}>
              {symbol}
            </span>
            <span style={{ fontSize: "0.75rem", color: "#64748b" }}>
              ({nameFa || "نماد معاملاتی بورس"})
            </span>
            <span style={{ fontSize: "0.72rem", color: "#38bdf8", backgroundColor: "rgba(56, 189, 248, 0.12)", padding: "2px 6px", borderRadius: "4px", fontWeight: 700 }}>
              {activeBar?.trading_date || "امروز"}
            </span>
          </div>

          <div style={{ display: "flex", gap: "0.6rem", color: "#94a3b8", alignItems: "center", flexWrap: "wrap" }}>
            <span>باز: <strong style={{ color: "#f8fafc" }}>{formatFa(activeBar?.open)}</strong></span>
            <span>سقف: <strong style={{ color: "#22c55e" }}>{formatFa(activeBar?.high)}</strong></span>
            <span>کف: <strong style={{ color: "#ef4444" }}>{formatFa(activeBar?.low)}</strong></span>
            <span>آخر: <strong style={{ color: activeBar && activeBar.close >= (activeBar.yesterday_price || activeBar.open) ? "#22c55e" : "#ef4444" }}>{formatFa(activeBar?.close)}</strong></span>
            <span>حجم: <strong style={{ color: "#38bdf8" }}>{formatFa(activeBar?.volume)}</strong></span>
            {activeEma9 && <span>EMA۹: <strong style={{ color: "#38bdf8" }}>{formatFa(activeEma9)}</strong></span>}
            {activeEma21 && <span>EMA۲۱: <strong style={{ color: "#f59e0b" }}>{formatFa(activeEma21)}</strong></span>}
            <span>RSI: <strong style={{ color: "#c084fc" }}>{formatFa(activeRsi)}</strong></span>
          </div>
        </div>

        {/* Right (RTL End): Chase State Banner & View Controls */}
        <div style={{ display: "flex", alignItems: "center", gap: "0.4rem", flexWrap: "wrap" }}>
          {isChaseBlocked ? (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.35rem",
                backgroundColor: "rgba(239, 68, 68, 0.2)",
                border: "1px solid #ef4444",
                color: "#fca5a5",
                padding: "3px 8px",
                borderRadius: "4px",
                fontSize: "0.72rem",
                fontWeight: 800,
              }}
            >
              <AlertTriangle size={13} color="#ef4444" />
              <span>⛔ تعقیب قیمت مسدود (CHASE_BLOCKED) — منتظر پولبک به ناحیه ورود بمانید</span>
            </div>
          ) : isFilled ? (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.35rem",
                backgroundColor: "rgba(34, 197, 94, 0.15)",
                border: "1px solid #22c55e",
                color: "#86efac",
                padding: "3px 8px",
                borderRadius: "4px",
                fontSize: "0.72rem",
                fontWeight: 800,
              }}
            >
              <ShieldCheck size={13} color="#22c55e" />
              <span>✅ معامله فعال در سبد • محاسبه R بر مبنای میانگین خرید ({formatFa(avgFillPrice)} ﷼)</span>
            </div>
          ) : (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.35rem",
                backgroundColor: "rgba(56, 189, 248, 0.12)",
                border: "1px solid #38bdf8",
                color: "#bae6fd",
                padding: "3px 8px",
                borderRadius: "4px",
                fontSize: "0.72rem",
                fontWeight: 800,
              }}
            >
              <Sparkles size={13} color="#38bdf8" />
              <span>آماده ورود با تیکت مدیریت ریسک (R/R هدف ۱: {rMultipleT1})</span>
            </div>
          )}

          {/* Timeframe selector */}
          <div style={{ display: "flex", backgroundColor: "#0b101b", borderRadius: "5px", padding: "2px", border: "1px solid #1e293b", marginRight: "0.4rem" }}>
            {(["1D", "60m", "15m"] as const).map((tf) => (
              <button
                key={tf}
                onClick={() => setSelectedTimeframe(tf)}
                style={{
                  padding: "3px 7px",
                  borderRadius: "4px",
                  border: "none",
                  backgroundColor: selectedTimeframe === tf ? "#38bdf8" : "transparent",
                  color: selectedTimeframe === tf ? "#0b101b" : "#94a3b8",
                  fontSize: "0.72rem",
                  fontWeight: 800,
                  cursor: "pointer",
                  fontFamily: "inherit",
                }}
              >
                {tf === "1D" ? "روزانه" : tf === "60m" ? "ساعتی" : "۱۵ دقیقه"}
              </button>
            ))}
          </div>

          {/* Feature Toggles */}
          <button
            onClick={() => setShowPriceLines(!showPriceLines)}
            style={{
              padding: "4px 8px",
              borderRadius: "4px",
              border: `1px solid ${showPriceLines ? "#38bdf8" : "#1e293b"}`,
              backgroundColor: showPriceLines ? "rgba(56, 189, 248, 0.15)" : "transparent",
              color: showPriceLines ? "#38bdf8" : "#64748b",
              fontSize: "0.72rem",
              fontWeight: 700,
              cursor: "pointer",
              fontFamily: "inherit",
            }}
          >
            سطوح قیمت
          </button>

          <button
            onClick={() => setShowRiskRewardZones(!showRiskRewardZones)}
            style={{
              padding: "4px 8px",
              borderRadius: "4px",
              border: `1px solid ${showRiskRewardZones ? "#22c55e" : "#1e293b"}`,
              backgroundColor: showRiskRewardZones ? "rgba(34, 197, 94, 0.15)" : "transparent",
              color: showRiskRewardZones ? "#22c55e" : "#64748b",
              fontSize: "0.72rem",
              fontWeight: 700,
              cursor: "pointer",
              fontFamily: "inherit",
            }}
          >
            ناحیه ریسک/ریوارد
          </button>

          <button
            onClick={() => setShowTradeMarkers(!showTradeMarkers)}
            style={{
              padding: "4px 8px",
              borderRadius: "4px",
              border: `1px solid ${showTradeMarkers ? "#c084fc" : "#1e293b"}`,
              backgroundColor: showTradeMarkers ? "rgba(192, 132, 252, 0.15)" : "transparent",
              color: showTradeMarkers ? "#c084fc" : "#64748b",
              fontSize: "0.72rem",
              fontWeight: 700,
              cursor: "pointer",
              fontFamily: "inherit",
            }}
          >
            پله‌های معامله
          </button>
        </div>
      </div>

      {/* ── 2. Master SVG Financial Chart Engine ────────────────────────── */}
      <div
        dir="ltr"
        style={{
          backgroundColor: "#080d1a",
          borderRadius: "10px",
          border: "1px solid #1e293b",
          padding: "0.5rem",
          overflowX: "auto",
          position: "relative",
          direction: "ltr",
        }}
      >
        <svg
          viewBox={`0 0 ${svgWidth} ${totalHeight}`}
          style={{ width: "100%", height: "auto", display: "block", minHeight: "420px" }}
          onMouseMove={(e) => {
            const rect = e.currentTarget.getBoundingClientRect();
            const mouseX = ((e.clientX - rect.left) / rect.width) * svgWidth;
            if (mouseX >= leftPadding && mouseX <= leftPadding + chartW) {
              const relX = mouseX - leftPadding;
              const idx = Math.floor(relX / barSlot);
              if (idx >= 0 && idx < data.length) {
                setHoveredIdx(idx);
              }
            }
          }}
          onMouseLeave={() => setHoveredIdx(null)}
        >
          <defs>
            {/* Gradients */}
            <linearGradient id="rewardZoneGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#22c55e" stopOpacity="0.22" />
              <stop offset="100%" stopColor="#22c55e" stopOpacity="0.04" />
            </linearGradient>
            <linearGradient id="riskZoneGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#ef4444" stopOpacity="0.05" />
              <stop offset="100%" stopColor="#ef4444" stopOpacity="0.22" />
            </linearGradient>
            <linearGradient id="volUpGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#22c55e" stopOpacity="0.6" />
              <stop offset="100%" stopColor="#22c55e" stopOpacity="0.1" />
            </linearGradient>
            <linearGradient id="volDnGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#ef4444" stopOpacity="0.6" />
              <stop offset="100%" stopColor="#ef4444" stopOpacity="0.1" />
            </linearGradient>
            <linearGradient id="rsiZoneGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#a855f7" stopOpacity="0.15" />
              <stop offset="100%" stopColor="#a855f7" stopOpacity="0.03" />
            </linearGradient>
            {/* Markers */}
            <marker id="buyArrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M 5 0 L 10 10 L 0 10 z" fill="#22c55e" />
            </marker>
            <marker id="sellArrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M 5 10 L 10 0 L 0 0 z" fill="#ef4444" />
            </marker>
          </defs>

          {/* ── 2.1 Background Grid & Price Coordinates ──────────────────── */}
          {[0.1, 0.3, 0.5, 0.7, 0.9].map((ratio, i) => {
            const pVal = minPrice + priceRange * ratio;
            const y = getPriceY(pVal);
            return (
              <g key={i}>
                <line
                  x1={leftPadding}
                  y1={y}
                  x2={leftPadding + chartW}
                  y2={y}
                  stroke="#1e293b"
                  strokeWidth={0.8}
                  strokeDasharray="4,4"
                />
                <text
                  x={leftPadding - 8}
                  y={y + 3.5}
                  fill="#64748b"
                  fontSize="10"
                  textAnchor="end"
                  fontFamily="Vazirmatn, system-ui, sans-serif"
                >
                  {formatFa(pVal)}
                </text>
              </g>
            );
          })}

          {/* ── 2.2 Risk / Reward Shaded Zones (Entry->Target & Entry->Stop) */}
          {showRiskRewardZones && showPriceLines && isGoodStock && (
            <>
              {/* Reward Zone (Entry up to Target 2) */}
              <rect
                x={leftPadding}
                y={getPriceY(calcT2)}
                width={chartW}
                height={Math.max(2, getPriceY(effectiveEntry) - getPriceY(calcT2))}
                fill="url(#rewardZoneGrad)"
                stroke="#22c55e"
                strokeWidth={0.5}
                strokeDasharray="2,4"
                opacity={0.7}
              />
              {/* Risk Zone (Entry down to Stop) */}
              <rect
                x={leftPadding}
                y={getPriceY(effectiveEntry)}
                width={chartW}
                height={Math.max(2, getPriceY(calcStop) - getPriceY(effectiveEntry))}
                fill="url(#riskZoneGrad)"
                stroke="#ef4444"
                strokeWidth={0.5}
                strokeDasharray="2,4"
                opacity={0.7}
              />
            </>
          )}

          {/* ── 2.3 Real PriceLine Series (MarkLines on Engine) ─────────── */}
          {showPriceLines && (() => {
            const lines = [
              calcT2 ? {
                id: "t2",
                name: "🏆 هدف دوم",
                price: calcT2,
                y: getPriceY(calcT2),
                distPct: `+${toPersianDigits((((calcT2 - effectiveEntry) / effectiveEntry) * 100).toFixed(1))}٪`,
                rMultiple: `${rMultipleT2}R`,
                color: "#c084fc",
                bg: "#3b0764",
                stroke: "#a855f7",
                text: "#f3e8ff",
                dash: "6,4",
              } : null,
              calcT1 ? {
                id: "t1",
                name: "🎯 هدف اول",
                price: calcT1,
                y: getPriceY(calcT1),
                distPct: `+${toPersianDigits((((calcT1 - effectiveEntry) / effectiveEntry) * 100).toFixed(1))}٪`,
                rMultiple: `${rMultipleT1}R`,
                color: "#22c55e",
                bg: "#052e16",
                stroke: "#22c55e",
                text: "#86efac",
                dash: "6,3",
              } : null,
              effectiveEntry ? {
                id: "entry",
                name: isFilled ? "📍 میانگین خرید واقعی" : "📍 نقطه ورود برنامه‌ریزی",
                price: effectiveEntry,
                y: getPriceY(effectiveEntry),
                distPct: "۰.۰٪",
                rMultiple: "مبنا 0R",
                color: "#38bdf8",
                bg: "#082f49",
                stroke: "#38bdf8",
                text: "#bae6fd",
                dash: "0",
              } : null,
              calcStop ? {
                id: "stop",
                name: "🛑 حد ضرر انضباطی",
                price: calcStop,
                y: getPriceY(calcStop),
                distPct: `-${toPersianDigits((((effectiveEntry - calcStop) / effectiveEntry) * 100).toFixed(1))}٪`,
                rMultiple: "-1.0R",
                color: "#ef4444",
                bg: "#450a0a",
                stroke: "#ef4444",
                text: "#fca5a5",
                dash: "4,4",
              } : null,
              (!isGoodStock && sellAdvicePrice) ? {
                id: "sell",
                name: "⚠️ نقطه خروج اضطراری",
                price: sellAdvicePrice,
                y: getPriceY(sellAdvicePrice),
                distPct: "خروج فوری",
                rMultiple: "اخطار",
                color: "#f97316",
                bg: "#431407",
                stroke: "#f97316",
                text: "#fdba74",
                dash: "3,3",
              } : null,
            ].filter(Boolean) as any[];

            // Sort & apply collision avoidance for right gutter badges
            lines.sort((a, b) => a.y - b.y);
            const badgeY = [...lines.map((l) => l.y)];
            const minGap = 23;
            for (let i = 1; i < badgeY.length; i++) {
              if (badgeY[i] - badgeY[i - 1] < minGap) {
                badgeY[i] = badgeY[i - 1] + minGap;
              }
            }

            return lines.map((lvl, idx) => {
              const adjustedBadgeY = badgeY[idx];
              return (
                <g key={lvl.id}>
                  {/* True Price Coordinate Line */}
                  <line
                    x1={leftPadding}
                    y1={lvl.y}
                    x2={leftPadding + chartW}
                    y2={lvl.y}
                    stroke={lvl.color}
                    strokeWidth={lvl.id === "entry" ? 2.0 : 1.4}
                    strokeDasharray={lvl.dash !== "0" ? lvl.dash : undefined}
                  />

                  {/* Small Anchor Dot on Level Line End */}
                  <circle
                    cx={leftPadding + chartW}
                    cy={lvl.y}
                    r={3}
                    fill={lvl.color}
                  />

                  {/* Leader connector if shifted by collision avoidance */}
                  {Math.abs(adjustedBadgeY - lvl.y) > 2 && (
                    <line
                      x1={leftPadding + chartW}
                      y1={lvl.y}
                      x2={leftPadding + chartW + 6}
                      y2={adjustedBadgeY}
                      stroke={lvl.color}
                      strokeWidth={1}
                      opacity={0.6}
                    />
                  )}

                  {/* Anti-collision Gutter Badge on Price Scale */}
                  <rect
                    x={leftPadding + chartW + 6}
                    y={adjustedBadgeY - 12}
                    width={184}
                    height={24}
                    fill={lvl.bg}
                    rx={6}
                    stroke={lvl.stroke}
                    strokeWidth={1}
                  />
                  <text
                    x={leftPadding + chartW + 6 + 92}
                    y={adjustedBadgeY + 4}
                    fill={lvl.text}
                    fontSize="9.5"
                    fontWeight="bold"
                    fontFamily="Vazirmatn, system-ui, sans-serif"
                    textAnchor="middle"
                  >
                    {`${lvl.name}: ${formatFa(lvl.price)} ﷼ (${lvl.rMultiple})`}
                  </text>
                </g>
              );
            });
          })()}

          {/* ── 2.4 EMA Indicator Curves ─────────────────────────────────── */}
          {showEMA && (
            <>
              <polyline
                points={emaData.ema9
                  .map((val, i) => (val !== null ? `${getBarX(i)},${getPriceY(val)}` : null))
                  .filter(Boolean)
                  .join(" ")}
                fill="none"
                stroke="#38bdf8"
                strokeWidth={1.8}
                opacity={0.85}
              />
              <polyline
                points={emaData.ema21
                  .map((val, i) => (val !== null ? `${getBarX(i)},${getPriceY(val)}` : null))
                  .filter(Boolean)
                  .join(" ")}
                fill="none"
                stroke="#f59e0b"
                strokeWidth={2.0}
                opacity={0.85}
              />
            </>
          )}

          {/* ── 2.5 OHLC Candlestick Series & Execution Markers ──────────── */}
          {data.map((b, i) => {
            const x = getBarX(i);
            const openY = getPriceY(b.open || b.close);
            const closeY = getPriceY(b.close);
            const highY = getPriceY(b.high || b.close);
            const lowY = getPriceY(b.low || b.close);
            const isUp = b.close >= (b.open || b.close);
            const candleColor = isUp ? "#22c55e" : "#ef4444";
            const bodyTop = Math.min(openY, closeY);
            const bodyHeight = Math.max(3, Math.abs(closeY - openY));
            const isHovered = hoveredIdx === i;

            return (
              <g key={`candle-${i}`}>
                {/* Upper/Lower Wicks */}
                <line
                  x1={x}
                  y1={highY}
                  x2={x}
                  y2={lowY}
                  stroke={candleColor}
                  strokeWidth={1.4}
                  opacity={isHovered ? 1 : 0.85}
                />

                {/* Candle Real Body */}
                <rect
                  x={x - barWidth / 2}
                  y={bodyTop}
                  width={barWidth}
                  height={bodyHeight}
                  fill={isUp ? "#22c55e" : "#ef4444"}
                  stroke={isUp ? "#16a34a" : "#dc2626"}
                  strokeWidth={0.8}
                  rx={1}
                />

                {/* Corporate Action Marker (مجمع / افزایش سرمایه) */}
                {b.corporate_action && (
                  <g>
                    <circle
                      cx={x}
                      y={highY - 14}
                      r={7}
                      fill="#eab308"
                      stroke="#713f12"
                      strokeWidth={1}
                    />
                    <text
                      x={x}
                      y={highY - 10}
                      fill="#000"
                      fontSize="9"
                      fontWeight="bold"
                      textAnchor="middle"
                    >
                      D
                    </text>
                  </g>
                )}

                {/* Stage Entry Trade Markers (پله‌های خرید Stage 1/2/3) */}
                {showTradeMarkers && b.stage_entry && (
                  <g>
                    <path
                      d={`M ${x} ${lowY + 8} L ${x - 5} ${lowY + 18} L ${x + 5} ${lowY + 18} Z`}
                      fill="#22c55e"
                      stroke="#14532d"
                      strokeWidth={1}
                    />
                    <rect
                      x={x - 30}
                      y={lowY + 20}
                      width={60}
                      height={16}
                      fill="#052e16"
                      stroke="#22c55e"
                      strokeWidth={0.8}
                      rx={3}
                    />
                    <text
                      x={x}
                      y={lowY + 31}
                      fill="#86efac"
                      fontSize="8.5"
                      fontWeight="bold"
                      textAnchor="middle"
                    >
                      {`پله ${b.stage_entry.stage} (${b.stage_entry.pct}٪)`}
                    </text>
                  </g>
                )}

                {/* Exit Trade Markers */}
                {showTradeMarkers && b.exit_marker && (
                  <g>
                    <path
                      d={`M ${x} ${highY - 8} L ${x - 5} ${highY - 18} L ${x + 5} ${highY - 18} Z`}
                      fill="#ef4444"
                      stroke="#7f1d1d"
                      strokeWidth={1}
                    />
                    <rect
                      x={x - 28}
                      y={highY - 34}
                      width={56}
                      height={16}
                      fill="#450a0a"
                      stroke="#ef4444"
                      strokeWidth={0.8}
                      rx={3}
                    />
                    <text
                      x={x}
                      y={highY - 23}
                      fill="#fca5a5"
                      fontSize="8"
                      fontWeight="bold"
                      textAnchor="middle"
                    >
                      {b.exit_marker.type === "target1" ? "سیو سود T1" : "حد ضرر"}
                    </text>
                  </g>
                )}
              </g>
            );
          })}

          {/* ── 2.6 Independent Volume Pane ─────────────────────────────── */}
          {showVolume && (
            <g>
              {/* Volume Pane Separator & Label */}
              <line
                x1={leftPadding}
                y1={volPaneTop}
                x2={leftPadding + chartW}
                y2={volPaneTop}
                stroke="#1e293b"
                strokeWidth={1}
              />
              <text x={leftPadding - 8} y={volPaneTop + 14} fill="#64748b" fontSize="9.5" textAnchor="end">
                حجم (Vol)
              </text>
              <text x={leftPadding - 8} y={volPaneTop + volPaneHeight} fill="#475569" fontSize="8.5" textAnchor="end">
                {formatFa(maxVol)}
              </text>

              {/* Volume Bars */}
              {data.map((b, i) => {
                const x = getBarX(i);
                const isUp = b.close >= (b.open || b.close);
                const y = getVolY(b.volume || 0);
                const h = Math.max(2, volPaneTop + volPaneHeight - y);

                return (
                  <rect
                    key={`vol-${i}`}
                    x={x - barWidth / 2}
                    y={y}
                    width={barWidth}
                    height={h}
                    fill={isUp ? "url(#volUpGrad)" : "url(#volDnGrad)"}
                    stroke={isUp ? "#22c55e" : "#ef4444"}
                    strokeWidth={0.5}
                    opacity={hoveredIdx === i ? 1 : 0.75}
                  />
                );
              })}
            </g>
          )}

          {/* ── 2.7 Independent RSI Oscillator Pane (0 to 100 Scale) ─────── */}
          {showRSI && (
            <g>
              {/* RSI Pane Separator */}
              <line
                x1={leftPadding}
                y1={rsiPaneTop}
                x2={leftPadding + chartW}
                y2={rsiPaneTop}
                stroke="#1e293b"
                strokeWidth={1}
              />
              
              {/* Overbought 70 Band */}
              <line
                x1={leftPadding}
                y1={getRsiY(70)}
                x2={leftPadding + chartW}
                y2={getRsiY(70)}
                stroke="#ef4444"
                strokeWidth={0.8}
                strokeDasharray="3,3"
                opacity={0.6}
              />
              <text x={leftPadding - 8} y={getRsiY(70) + 3} fill="#ef4444" fontSize="8.5" textAnchor="end">
                70 (اشباع خرید)
              </text>

              {/* Oversold 30 Band */}
              <line
                x1={leftPadding}
                y1={getRsiY(30)}
                x2={leftPadding + chartW}
                y2={getRsiY(30)}
                stroke="#22c55e"
                strokeWidth={0.8}
                strokeDasharray="3,3"
                opacity={0.6}
              />
              <text x={leftPadding - 8} y={getRsiY(30) + 3} fill="#22c55e" fontSize="8.5" textAnchor="end">
                30 (اشباع فروش)
              </text>

              {/* RSI 30-70 Shaded Buffer */}
              <rect
                x={leftPadding}
                y={getRsiY(70)}
                width={chartW}
                height={Math.max(2, getRsiY(30) - getRsiY(70))}
                fill="url(#rsiZoneGrad)"
              />

              {/* RSI Curve Line */}
              <polyline
                points={rsiSeries
                  .map((val, i) => `${getBarX(i)},${getRsiY(val)}`)
                  .join(" ")}
                fill="none"
                stroke="#c084fc"
                strokeWidth={1.8}
              />
            </g>
          )}

          {/* ── 2.8 Interactive Vertical Crosshair Line & Time Marker ─────── */}
          {hoveredIdx !== null && data[hoveredIdx] && (
            <g>
              <line
                x1={getBarX(hoveredIdx)}
                y1={candlePaneTop}
                x2={getBarX(hoveredIdx)}
                y2={totalHeight - 20}
                stroke="#38bdf8"
                strokeWidth={1}
                strokeDasharray="3,3"
                opacity={0.8}
              />
              {/* Date badge at bottom of crosshair */}
              <rect
                x={getBarX(hoveredIdx) - 35}
                y={totalHeight - 18}
                width={70}
                height={16}
                fill="#0c4a6e"
                stroke="#38bdf8"
                strokeWidth={0.8}
                rx={3}
              />
              <text
                x={getBarX(hoveredIdx)}
                y={totalHeight - 6}
                fill="#f0f9ff"
                fontSize="9"
                fontWeight="bold"
                textAnchor="middle"
              >
                {data[hoveredIdx].trading_date}
              </text>
            </g>
          )}

          {/* ── 2.9 Time Axis Labels at Regular Intervals ────────────────── */}
          {data
            .filter((_, idx) => idx % Math.max(1, Math.floor(data.length / 5)) === 0)
            .map((b, idx) => (
              <text
                key={`t-label-${idx}`}
                x={getBarX(data.indexOf(b))}
                y={totalHeight - 4}
                fill="#64748b"
                fontSize="9"
                textAnchor="middle"
                fontFamily="Vazirmatn, system-ui, sans-serif"
              >
                {typeof b.trading_date === "string" ? b.trading_date.slice(5) : String(b.trading_date || "")}
              </text>
            ))}
        </svg>
      </div>
    </div>
  );
};
