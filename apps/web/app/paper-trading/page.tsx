"use client";
import React from "react";
import Link from "next/link";
import { PaperTradingView } from "../../components/PaperTradingView";
import { ArrowRight, Radar } from "lucide-react";

export default function StandalonePaperTradingPage() {
  return (
    <div style={{ minHeight: "100vh", backgroundColor: "var(--bg-primary)", color: "var(--text-primary)" }}>
      {/* Top Navbar */}
      <nav
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "1rem 2rem",
          backgroundColor: "var(--bg-surface)",
          borderBottom: "1px solid var(--border-subtle)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <Radar size={24} color="var(--tse-blue)" />
          <span style={{ fontSize: "1.1rem", fontWeight: 800 }}>رادار بازار سرمایه ایران (Iran Market Radar)</span>
        </div>

        <Link
          href="/"
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.4rem",
            color: "var(--tse-blue)",
            textDecoration: "none",
            fontSize: "0.85rem",
            fontWeight: 700,
          }}
        >
          <span>بازگشت به داشبورد اصلی رادار</span>
          <ArrowRight size={16} />
        </Link>
      </nav>

      {/* Main Container */}
      <div style={{ maxWidth: "1440px", margin: "0 auto", padding: "1.5rem" }}>
        <PaperTradingView />
      </div>
    </div>
  );
}
