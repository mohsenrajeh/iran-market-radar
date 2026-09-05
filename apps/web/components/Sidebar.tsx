"use client";
import React from "react";
import {
  LayoutDashboard,
  Layers,
  PieChart,
  FlaskConical,
  Sliders,
  Radar,
  Sparkles,
  Briefcase,
  LogOut,
} from "lucide-react";
import { toPersianDigits } from "../lib/formatters";

export type NavTab =
  | "overview"
  | "opportunities"
  | "open_positions"
  | "fundamental"
  | "trading_lab"
  | "health_settings";

interface SidebarProps {
  activeTab: NavTab;
  onSelectTab: (tab: NavTab) => void;
  opportunityCount: number;
  openPositionsCount?: number;
  ownerName?: string;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  onSelectTab,
  opportunityCount,
  openPositionsCount = 0,
  ownerName = "",
}) => {
  const menuItems = [
    { id: "overview", label: "داشبورد اجرایی", icon: LayoutDashboard },
    { id: "opportunities", label: "دیده‌بان و فیلتر سهام", icon: Layers, badge: opportunityCount },
    { id: "open_positions", label: "معاملات باز و پورتفو", icon: Briefcase, badge: openPositionsCount, highlight: true },
    { id: "fundamental", label: "تحلیل بنیادی و کدال", icon: PieChart },
    { id: "trading_lab", label: "مرکز آزمایشگاه و یادگیری", icon: FlaskConical },
    { id: "health_settings", label: "سلامت داده و تنظیمات", icon: Sliders },
  ];

  return (
    <aside
      className="app-sidebar"
      style={{
        width: "260px",
        backgroundColor: "var(--bg-secondary)",
        borderLeft: "1px solid var(--border-subtle)",
        display: "flex",
        flexDirection: "column",
        height: "100vh",
        position: "sticky",
        top: 0,
        flexShrink: 0,
      }}
    >
      {/* Brand Header */}
      <div
        style={{
          padding: "1.25rem 1.5rem",
          borderBottom: "1px solid var(--border-subtle)",
          display: "flex",
          alignItems: "center",
          gap: "0.75rem",
        }}
      >
        <div
          style={{
            width: "38px",
            height: "38px",
            borderRadius: "10px",
            backgroundColor: "var(--tse-green)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "#fff",
            boxShadow: "0 4px 12px rgba(34, 197, 94, 0.3)",
          }}
        >
          <Radar size={22} />
        </div>
        <div>
          <div style={{ fontWeight: 900, fontSize: "1.05rem", color: "var(--text-primary)" }}>
            رادار بازار سرمایه
          </div>
          <div style={{ fontSize: "0.7rem", color: "var(--text-secondary)" }}>
            سامانه هوشمند پایش و ترید بورس
          </div>
        </div>
      </div>

      {/* Navigation Links */}
      <nav className="app-sidebar-nav" style={{ padding: "1rem 0.75rem", display: "flex", flexDirection: "column", gap: "0.35rem", flex: 1 }}>
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              data-tab={item.id}
              onClick={() => onSelectTab(item.id as NavTab)}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "0.75rem 1rem",
                borderRadius: "var(--radius-sm)",
                border: "none",
                backgroundColor: isActive ? "var(--tse-blue)" : "transparent",
                color: isActive ? "#ffffff" : "var(--text-secondary)",
                fontWeight: isActive ? 700 : 500,
                fontSize: "0.88rem",
                cursor: "pointer",
                transition: "all 0.15s ease",
                textAlign: "right",
                width: "100%",
                fontFamily: "inherit",
              }}
              onMouseEnter={(e) => {
                if (!isActive) {
                  e.currentTarget.style.backgroundColor = "var(--bg-surface)";
                  e.currentTarget.style.color = "var(--text-primary)";
                }
              }}
              onMouseLeave={(e) => {
                if (!isActive) {
                  e.currentTarget.style.backgroundColor = "transparent";
                  e.currentTarget.style.color = "var(--text-secondary)";
                }
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                <Icon size={18} />
                <span>{item.label}</span>
              </div>
              {typeof item.badge === "number" && item.badge > 0 && (
                <span
                  style={{
                    fontSize: "0.7rem",
                    padding: "2px 8px",
                    borderRadius: "10px",
                    backgroundColor: isActive ? "rgba(255,255,255,0.25)" : (item.highlight ? "rgba(34, 197, 94, 0.2)" : "var(--bg-surface)"),
                    color: isActive ? "#ffffff" : (item.highlight ? "var(--tse-green)" : "var(--text-muted)"),
                    fontWeight: 700,
                  }}
                  className="tabular-num"
                >
                  {toPersianDigits(item.badge)}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Footer Info & Logout */}
      <div
        className="app-sidebar-footer"
        style={{
          padding: "1rem 1.25rem",
          borderTop: "1px solid var(--border-subtle)",
          backgroundColor: "rgba(0,0,0,0.15)",
          display: "flex",
          flexDirection: "column",
          gap: "0.6rem",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <div style={{ width: 8, height: 8, borderRadius: "50%", backgroundColor: "var(--tse-green)" }} />
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
              گردآوری داده فعال • معامله تابع گیت‌ها
            </span>
          </div>
          <button
            onClick={async () => {
              try {
                await fetch("/api/v1/auth/logout", { method: "POST" });
              } catch (_) {}
              window.location.reload();
            }}
            title="خروج از حساب کاربری"
            style={{
              background: "transparent",
              border: "none",
              color: "#94a3b8",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "4px",
              fontSize: "0.72rem",
              padding: "2px 6px",
              borderRadius: "4px",
            }}
          >
            <LogOut size={13} color="#ef4444" />
            <span style={{ color: "#ef4444" }}>خروج</span>
          </button>
        </div>
        <div style={{ fontSize: "0.72rem", color: "var(--text-secondary)" }}>
          مالک سامانه: <strong style={{ color: "var(--text-primary)" }}>{ownerName || "نشست تأیید نشده"}</strong>
        </div>
        <div style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>
          ورژن ۲.۵ • بورس اوراق بهادار تهران
        </div>
      </div>
    </aside>
  );
};
