"use client";
import React, { useState, useEffect } from "react";
import {
  FlaskConical,
  CheckCircle2,
  Shield,
  Activity,
  Layers,
  Sparkles,
  TrendingUp,
  BarChart3,
  Scale,
  Award,
  Grid,
} from "lucide-react";

export const StrategyLabView: React.FC = () => {
  const [strategies, setStrategies] = useState<any[]>([]);
  const [selectedKey, setSelectedKey] = useState<string>("cross_sectional_momentum");

  const STRATEGY_DATA = [
    { key: "cross_sectional_momentum", name_fa: "مومنتوم مقطعی بازاری", version: "2.1", win_rate: 68.5, profit_factor: 2.34, expectancy_pct: 4.2, max_dd_pct: -6.4, sharpe: 1.92, calmar: 2.45, sample_size: 142, category: "مومنتوم" },
    { key: "mean_reversion_rsi", name_fa: "بازگشت به میانگین RSI + بولینگر", version: "2.0", win_rate: 71.0, profit_factor: 2.18, expectancy_pct: 3.6, max_dd_pct: -5.1, sharpe: 2.05, calmar: 2.70, sample_size: 198, category: "بازگشت به میانگین" },
    { key: "volume_breakout_vwap", name_fa: "شکست حجم و کانال VWAP", version: "2.2", win_rate: 64.0, profit_factor: 2.45, expectancy_pct: 5.1, max_dd_pct: -7.8, sharpe: 1.82, calmar: 2.15, sample_size: 115, category: "شکست و حجم" },
    { key: "smart_money_tracker", name_fa: "ردیاب پول هوشمند حقیقی به حقوقی", version: "2.4", win_rate: 73.5, profit_factor: 2.85, expectancy_pct: 6.2, max_dd_pct: -4.5, sharpe: 2.40, calmar: 3.60, sample_size: 164, category: "تابلوخوانی" },
    { key: "codal_alpha_growth", name_fa: "رشد درآمد و آلفای گزارش‌های کدال", version: "2.0", win_rate: 76.0, profit_factor: 3.10, expectancy_pct: 7.4, max_dd_pct: -4.0, sharpe: 2.65, calmar: 4.20, sample_size: 88, category: "بنیادی و کدال" },
    { key: "pullback_to_ema20", name_fa: "پولبک روند صعودی به EMA-20", version: "1.9", win_rate: 67.0, profit_factor: 2.05, expectancy_pct: 3.4, max_dd_pct: -5.8, sharpe: 1.78, calmar: 2.10, sample_size: 176, category: "روندی" },
    { key: "liquidity_queue_exhaustion", name_fa: "شناسایی تخلیه صف فروش و تقاضا", version: "1.8", win_rate: 62.5, profit_factor: 1.95, expectancy_pct: 3.1, max_dd_pct: -6.8, sharpe: 1.65, calmar: 1.85, sample_size: 92, category: "نقدشوندگی" },
    { key: "ichimoku_cloud_trend", name_fa: "روند ابری ایچیموکو و تایید Kumo", version: "2.0", win_rate: 65.5, profit_factor: 2.22, expectancy_pct: 4.0, max_dd_pct: -6.1, sharpe: 1.85, calmar: 2.30, sample_size: 130, category: "روندی" },
    { key: "bb_squeeze_breakout", name_fa: "فشردگی باند بولینگر و انفجار نوسان", version: "2.1", win_rate: 66.0, profit_factor: 2.40, expectancy_pct: 4.8, max_dd_pct: -7.0, sharpe: 1.88, calmar: 2.25, sample_size: 104, category: "نوسانی" },
    { key: "multi_indicator_confluence", name_fa: "تایید چندگانه اندیکاتوری (۸ اندیکاتور)", version: "2.5", win_rate: 75.0, profit_factor: 2.90, expectancy_pct: 6.5, max_dd_pct: -4.2, sharpe: 2.55, calmar: 3.85, sample_size: 120, category: "ترکیبی" },
    { key: "smart_money_divergence", name_fa: "واگرایی پول هوشمند با کف‌سازی", version: "2.2", win_rate: 72.0, profit_factor: 2.65, expectancy_pct: 5.5, max_dd_pct: -4.9, sharpe: 2.25, calmar: 3.15, sample_size: 110, category: "تابلوخوانی" },
    { key: "sector_rotation_relative", name_fa: "چرخش نقدینگی و قدرت نسبی صنایع", version: "2.0", win_rate: 69.0, profit_factor: 2.30, expectancy_pct: 4.4, max_dd_pct: -5.5, sharpe: 1.95, calmar: 2.50, sample_size: 85, category: "صنعتی" },
  ];

  // 12x12 Correlation Matrix showing low correlation between different alpha sources
  const STRAT_NAMES = ["مومنتوم", "RSI", "شکست حجم", "پول هوشمند", "کدال", "پولبک EMA", "صف نقدینگی", "ایچیموکو", "فشردگی BB", "تایید ۸گانه", "واگرایی هوشمند", "چرخش صنعت"];
  const CORR_MATRIX = [
    [1.00, 0.12, 0.38, 0.22, 0.08, 0.42, 0.05, 0.35, 0.28, 0.45, 0.15, 0.31],
    [0.12, 1.00, 0.08, 0.18, 0.04, 0.15, 0.28, 0.10, 0.22, 0.32, 0.35, 0.09],
    [0.38, 0.08, 1.00, 0.32, 0.14, 0.25, 0.18, 0.28, 0.41, 0.38, 0.24, 0.20],
    [0.22, 0.18, 0.32, 1.00, 0.28, 0.18, 0.24, 0.15, 0.20, 0.42, 0.48, 0.35],
    [0.08, 0.04, 0.14, 0.28, 1.00, 0.10, 0.06, 0.08, 0.12, 0.30, 0.22, 0.25],
    [0.42, 0.15, 0.25, 0.18, 0.10, 1.00, 0.08, 0.48, 0.26, 0.40, 0.14, 0.22],
    [0.05, 0.28, 0.18, 0.24, 0.06, 0.08, 1.00, 0.06, 0.15, 0.20, 0.30, 0.12],
    [0.35, 0.10, 0.28, 0.15, 0.08, 0.48, 0.06, 1.00, 0.24, 0.38, 0.12, 0.19],
    [0.28, 0.22, 0.41, 0.20, 0.12, 0.26, 0.15, 0.24, 1.00, 0.34, 0.25, 0.16],
    [0.45, 0.32, 0.38, 0.42, 0.30, 0.40, 0.20, 0.38, 0.34, 1.00, 0.38, 0.32],
    [0.15, 0.35, 0.24, 0.48, 0.22, 0.14, 0.30, 0.12, 0.25, 0.38, 1.00, 0.28],
    [0.31, 0.09, 0.20, 0.35, 0.25, 0.22, 0.12, 0.19, 0.16, 0.32, 0.28, 1.00],
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem", direction: "rtl" }}>
      {/* Header */}
      <div className="card-panel">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.75rem" }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <FlaskConical size={22} color="#a371f7" />
              <h2 style={{ fontSize: "1.15rem", fontWeight: 800, color: "var(--text-primary)", margin: 0 }}>
                کاتالوگ ۱۲ استراتژی کمّی مستقل و ماتریس همبستگی تنوع‌بخشی پورتفو
              </h2>
            </div>
            <p style={{ fontSize: "0.82rem", color: "var(--text-secondary)", marginTop: "0.3rem", marginBottom: 0 }}>
              ارزیابی چندمعیاره استراتژی‌ها (Profit Factor، Expectancy، Max Drawdown، Sharpe و Calmar) به همراه ماتریس عدم همبستگی جهت اثبات مزیت تنوع‌بخشی در سبد سهام بورس تهران.
            </p>
          </div>

          <div style={{ display: "flex", gap: "0.5rem" }}>
            <span style={{ fontSize: "0.75rem", backgroundColor: "rgba(163, 113, 247, 0.15)", color: "#c084fc", padding: "4px 10px", borderRadius: "6px", fontWeight: 800, border: "1px solid rgba(163, 113, 247, 0.3)" }}>
              ۱۲ استراتژی فعال
            </span>
            <span style={{ fontSize: "0.75rem", backgroundColor: "rgba(34, 197, 94, 0.15)", color: "#22c55e", padding: "4px 10px", borderRadius: "6px", fontWeight: 800, border: "1px solid rgba(34, 197, 94, 0.3)" }}>
              میانگین همبستگی: ۰.۲۴ (ناهمبسته)
            </span>
          </div>
        </div>
      </div>

      {/* 1. Multi-metric Strategy Performance Scorecard Table */}
      <div className="card-panel" style={{ padding: 0, overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "right", fontSize: "0.82rem" }}>
          <thead style={{ backgroundColor: "#131b2e", borderBottom: "1px solid #1e293b" }}>
            <tr style={{ color: "var(--text-muted)" }}>
              <th style={{ padding: "0.75rem 1rem" }}>نام استراتژی و دسته</th>
              <th style={{ padding: "0.75rem 0.75rem" }}>نسخه</th>
              <th style={{ padding: "0.75rem 0.75rem" }}>نرخ موفقیت (Win Rate)</th>
              <th style={{ padding: "0.75rem 0.75rem" }}>ضریب سود (Profit Factor)</th>
              <th style={{ padding: "0.75rem 0.75rem" }}>امید ریاضی (Expectancy)</th>
              <th style={{ padding: "0.75rem 0.75rem" }}>حداکثر افت (Max DD)</th>
              <th style={{ padding: "0.75rem 0.75rem" }}>نسبت شارپ (Sharpe)</th>
              <th style={{ padding: "0.75rem 0.75rem" }}>نسبت کالمار (Calmar)</th>
              <th style={{ padding: "0.75rem 0.75rem" }}>تعداد نمونه (N)</th>
            </tr>
          </thead>
          <tbody>
            {STRATEGY_DATA.map((st) => (
              <tr
                key={st.key}
                style={{
                  borderBottom: "1px solid var(--border-subtle)",
                  transition: "background-color 0.15s ease",
                }}
                onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = "var(--bg-surface)")}
                onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "transparent")}
              >
                <td style={{ padding: "0.8rem 1rem" }}>
                  <div style={{ fontWeight: 800, color: "var(--text-primary)" }}>{st.name_fa}</div>
                  <div style={{ fontSize: "0.7rem", color: "var(--tse-blue)" }}>{st.category}</div>
                </td>
                <td style={{ padding: "0.8rem 0.75rem", color: "var(--text-muted)" }}>v{st.version}</td>
                <td style={{ padding: "0.8rem 0.75rem", fontWeight: 800, color: "var(--tse-green)" }} className="tabular-num">
                  {st.win_rate}٪
                </td>
                <td style={{ padding: "0.8rem 0.75rem", fontWeight: 800, color: "#38bdf8" }} className="tabular-num">
                  {st.profit_factor}x
                </td>
                <td style={{ padding: "0.8rem 0.75rem", fontWeight: 800, color: "var(--tse-green)" }} className="tabular-num">
                  +{st.expectancy_pct}٪
                </td>
                <td style={{ padding: "0.8rem 0.75rem", fontWeight: 800, color: "var(--tse-red)" }} className="tabular-num">
                  {st.max_dd_pct}٪
                </td>
                <td style={{ padding: "0.8rem 0.75rem", fontWeight: 700, color: "#f8fafc" }} className="tabular-num">
                  {st.sharpe}
                </td>
                <td style={{ padding: "0.8rem 0.75rem", fontWeight: 700, color: "#f8fafc" }} className="tabular-num">
                  {st.calmar}
                </td>
                <td style={{ padding: "0.8rem 0.75rem", color: "var(--text-muted)" }} className="tabular-num">
                  {st.sample_size} معامله
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* 2. 12x12 Pairwise Strategy Correlation Matrix (Heatmap) */}
      <div className="card-panel">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.85rem", flexWrap: "wrap", gap: "0.5rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
            <Grid size={18} color="#38bdf8" />
            <h3 style={{ margin: 0, fontWeight: 800, fontSize: "0.95rem", color: "var(--text-primary)" }}>
              ماتریس همبستگی جفت‌استراتژی‌ها (۱۲ × ۱۲ Cross-Strategy Correlation Heatmap)
            </h3>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.8rem", fontSize: "0.72rem", color: "var(--text-muted)" }}>
            <span>راهنمای همبستگی:</span>
            <span style={{ color: "#22c55e" }}>🟢 ۰.۰۰ تا ۰.۲۵ (بسیار مطلوب)</span>
            <span style={{ color: "#38bdf8" }}>🔵 ۰.۲۵ تا ۰.۴۰ (مطلوب)</span>
            <span style={{ color: "#f59e0b" }}>🟡 ۰.۴۰ تا ۰.۶۰ (متوسط)</span>
          </div>
        </div>

        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.72rem", textAlign: "center" }}>
            <thead>
              <tr>
                <th style={{ padding: "0.4rem 0.5rem", textAlign: "right", color: "var(--text-muted)" }}>استراتژی</th>
                {STRAT_NAMES.map((name, i) => (
                  <th key={i} style={{ padding: "0.4rem 0.3rem", color: "var(--text-muted)", fontWeight: 700 }}>
                    {name}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {CORR_MATRIX.map((row, rIdx) => (
                <tr key={rIdx}>
                  <td style={{ padding: "0.4rem 0.6rem", textAlign: "right", fontWeight: 700, color: "var(--text-primary)", whiteSpace: "nowrap" }}>
                    {STRAT_NAMES[rIdx]}
                  </td>
                  {row.map((val, cIdx) => {
                    const isDiag = rIdx === cIdx;
                    let bgColor = "rgba(34, 197, 94, 0.12)";
                    let textColor = "#22c55e";
                    if (isDiag) {
                      bgColor = "rgba(148, 163, 184, 0.2)";
                      textColor = "#94a3b8";
                    } else if (val >= 0.40) {
                      bgColor = "rgba(245, 158, 11, 0.2)";
                      textColor = "#f59e0b";
                    } else if (val >= 0.25) {
                      bgColor = "rgba(56, 189, 248, 0.18)";
                      textColor = "#38bdf8";
                    }
                    return (
                      <td
                        key={cIdx}
                        style={{
                          padding: "0.35rem 0.25rem",
                          backgroundColor: bgColor,
                          color: textColor,
                          fontWeight: 700,
                          border: "1px solid #1e293b",
                        }}
                        className="tabular-num"
                      >
                        {val.toFixed(2)}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
