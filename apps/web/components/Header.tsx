"use client";
import React, { useState, useEffect, useRef } from "react";
import {
  Activity,
  ShieldCheck,
  Clock,
  TrendingUp,
  RefreshCw,
  Sparkles,
  Search,
  ChevronDown,
} from "lucide-react";

interface HeaderProps {
  currentViewTitle: string;
  regime: string;
  regimeFa: string;
  jalaliTime: string;
  tradingMode: string;
  isRefreshing?: boolean;
  onRefreshAll?: () => void;
  lastUpdatedTime?: string;
  onSelectSymbol?: (symbol: string) => void;
  isAutoRefreshEnabled?: boolean;
  onToggleAutoRefresh?: () => void;
  cadenceSeconds?: number;
}

export const Header: React.FC<HeaderProps> = ({
  currentViewTitle,
  regime,
  regimeFa,
  jalaliTime,
  tradingMode,
  isRefreshing = false,
  onRefreshAll,
  lastUpdatedTime,
  onSelectSymbol,
  isAutoRefreshEnabled = true,
  onToggleAutoRefresh,
  cadenceSeconds = 10,
}) => {
  const [searchQuery, setSearchQuery] = useState("");
  const [symbolsList, setSymbolsList] = useState<any[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetch("/api/v1/fundamentals/symbols")
      .then((res) => res.json())
      .then((data) => {
        if (Array.isArray(data)) setSymbolsList(data);
      })
      .catch((err) => console.error(err));
  }, []);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const filtered = searchQuery.trim()
    ? symbolsList.filter(
        (s) =>
          s.symbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
          (s.name_fa && s.name_fa.includes(searchQuery))
      )
    : [];

  const handleSelect = (sym: string) => {
    if (onSelectSymbol) onSelectSymbol(sym);
    setSearchQuery("");
    setIsOpen(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && filtered.length > 0) {
      handleSelect(filtered[0].symbol);
    } else if (e.key === "Enter" && searchQuery.trim()) {
      handleSelect(searchQuery.trim());
    }
  };

  return (
    <header
      style={{
        backgroundColor: "var(--bg-secondary)",
        borderBottom: "1px solid var(--border-subtle)",
        padding: "0.85rem 1.75rem",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        position: "sticky",
        top: 0,
        zIndex: 40,
        flexWrap: "wrap",
        gap: "0.75rem",
      }}
    >
      {/* ── Title & Quick Symbol Search ─────────────────────────────── */}
      <div style={{ display: "flex", alignItems: "center", gap: "1.25rem", flexWrap: "wrap" }}>
        <h1 style={{ fontSize: "1.15rem", fontWeight: 800, color: "var(--text-primary)", margin: 0 }}>
          {currentViewTitle}
        </h1>

        {/* Global Quick Search Input */}
        <div ref={dropdownRef} style={{ position: "relative", minWidth: "240px" }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.4rem",
              backgroundColor: "var(--bg-surface)",
              padding: "0.35rem 0.75rem",
              borderRadius: "6px",
              border: "1px solid var(--border-subtle)",
            }}
          >
            <Search size={15} color="var(--text-muted)" />
            <input
              type="text"
              placeholder="جستجو و تحلیل هر نماد..."
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setIsOpen(true);
              }}
              onFocus={() => setIsOpen(true)}
              onKeyDown={handleKeyDown}
              style={{
                background: "none",
                border: "none",
                color: "var(--text-primary)",
                fontFamily: "inherit",
                fontSize: "0.82rem",
                outline: "none",
                width: "100%",
              }}
            />
          </div>

          {/* Quick Dropdown Results */}
          {isOpen && filtered.length > 0 && (
            <div
              style={{
                position: "absolute",
                top: "110%",
                right: 0,
                left: 0,
                backgroundColor: "var(--bg-secondary)",
                border: "1px solid var(--border-active)",
                borderRadius: "8px",
                boxShadow: "0 8px 24px rgba(0,0,0,0.5)",
                maxHeight: "260px",
                overflowY: "auto",
                zIndex: 100,
                padding: "0.3rem",
              }}
            >
              {filtered.slice(0, 8).map((s) => (
                <div
                  key={s.symbol}
                  onClick={() => handleSelect(s.symbol)}
                  style={{
                    padding: "0.5rem 0.75rem",
                    borderRadius: "4px",
                    cursor: "pointer",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    transition: "background 0.15s ease",
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = "var(--bg-surface)")}
                  onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "transparent")}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                    <span style={{ fontWeight: 800, color: "var(--text-primary)", fontSize: "0.9rem" }}>{s.symbol}</span>
                    <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>{s.name_fa}</span>
                  </div>
                  <span style={{ fontSize: "0.72rem", color: "var(--tse-green)", fontWeight: 700 }}>
                    نمره: {s.fundamental_score || 80}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* ── Real-time Status & Global Actions ───────────────────────── */}
      <div style={{ display: "flex", alignItems: "center", gap: "1rem", flexWrap: "wrap" }}>
        {/* Unified Global Refresh Button */}
        {onRefreshAll && (
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            {onToggleAutoRefresh && (
              <button
                onClick={onToggleAutoRefresh}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "0.4rem",
                  padding: "0.45rem 0.85rem",
                  borderRadius: "6px",
                  fontSize: "0.78rem",
                  fontWeight: 700,
                  backgroundColor: isAutoRefreshEnabled ? "rgba(34, 197, 94, 0.12)" : "rgba(239, 68, 68, 0.12)",
                  color: isAutoRefreshEnabled ? "#22c55e" : "#ef4444",
                  border: `1px solid ${isAutoRefreshEnabled ? "rgba(34, 197, 94, 0.35)" : "rgba(239, 68, 68, 0.35)"}`,
                  cursor: "pointer",
                  fontFamily: "inherit",
                  transition: "all 0.15s ease",
                }}
                title={isAutoRefreshEnabled ? "توقف موقت بروزرسانی خودکار برای مطالعه و اسکرول بدون جابجایی صفحه" : "فعال‌سازی مجدد بروزرسانی خودکار زنده"}
              >
                <span
                  style={{
                    width: "8px",
                    height: "8px",
                    borderRadius: "50%",
                    backgroundColor: isAutoRefreshEnabled ? "#22c55e" : "#ef4444",
                    display: "inline-block",
                  }}
                />
                <span>{isAutoRefreshEnabled ? `خودکار: روشن (${(cadenceSeconds || 10).toLocaleString("fa-IR")}ث)` : "خودکار: متوقف"}</span>
              </button>
            )}

            <button
              onClick={onRefreshAll}
              disabled={isRefreshing}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.45rem",
                padding: "0.45rem 1rem",
                fontSize: "0.84rem",
                fontWeight: 700,
                backgroundColor: isRefreshing ? "var(--bg-surface)" : "var(--tse-green)",
                color: "#ffffff",
                border: isRefreshing ? "1px solid var(--border-subtle)" : "none",
                borderRadius: "6px",
                cursor: isRefreshing ? "not-allowed" : "pointer",
                boxShadow: isRefreshing ? "none" : "0 2px 10px rgba(46, 160, 67, 0.35)",
                transition: "all 0.2s ease",
                fontFamily: "inherit",
              }}
              title="بروزرسانی یکپارچه و همزمان تمامی داده‌های بورس، چارت‌ها، رادار و پورتفوی آزمایشی"
            >
              <RefreshCw size={15} className={isRefreshing ? "animate-spin" : ""} />
              <span>{isRefreshing ? "در حال همگام‌سازی..." : "بروزرسانی دستی"}</span>
            </button>

            {lastUpdatedTime && (
              <span
                style={{
                  fontSize: "0.72rem",
                  color: "var(--text-muted)",
                  display: "flex",
                  alignItems: "center",
                  gap: "0.25rem",
                  backgroundColor: "var(--bg-surface)",
                  padding: "0.3rem 0.6rem",
                  borderRadius: "4px",
                  border: "1px solid var(--border-subtle)",
                }}
                className="tabular-num"
              >
                <span>همگام‌سازی:</span>
                <strong style={{ color: "var(--text-secondary)" }}>{lastUpdatedTime}</strong>
              </span>
            )}
          </div>
        )}

        {/* Market Regime Badge */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.4rem",
            backgroundColor: regime === "risk_on" ? "var(--tse-green-subtle)" : "var(--tse-amber-subtle)",
            color: regime === "risk_on" ? "var(--tse-green)" : "var(--tse-amber)",
            border: `1px solid ${regime === "risk_on" ? "rgba(46, 160, 67, 0.4)" : "rgba(210, 153, 34, 0.4)"}`,
            padding: "0.35rem 0.75rem",
            borderRadius: "var(--radius-sm)",
            fontSize: "0.8rem",
            fontWeight: 600,
          }}
        >
          <TrendingUp size={14} />
          <span>رژیم بازار: {regimeFa || "رونق (ریسک‌پذیر)"}</span>
        </div>

        {/* Trading Mode Badge */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.4rem",
            backgroundColor: "var(--bg-surface)",
            color: "var(--text-secondary)",
            border: "1px solid var(--border-subtle)",
            padding: "0.35rem 0.75rem",
            borderRadius: "var(--radius-sm)",
            fontSize: "0.8rem",
          }}
        >
          <ShieldCheck size={14} color="var(--tse-blue)" />
          <span>پورتفوی ۱ میلیارد تومانی (کاغذی)</span>
        </div>

        {/* Jalali Clock */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.4rem",
            color: "var(--text-muted)",
            fontSize: "0.8rem",
            fontFamily: "var(--font-vazir)",
          }}
        >
          <Clock size={14} />
          <span className="tabular-num">{jalaliTime || "۱۴۰۵/۰۵/۲۴ ۱۲:۳۰"}</span>
        </div>
      </div>
    </header>
  );
};
