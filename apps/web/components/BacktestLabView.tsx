"use client";
import React, { useState, useEffect } from "react";
import { History, Play, CheckCircle2, TrendingUp, ShieldAlert, Award } from "lucide-react";

export const BacktestLabView: React.FC = () => {
  const [backtests, setBacktests] = useState<any[]>([]);
  const [selectedRun, setSelectedRun] = useState<any | null>(null);
  const [trades, setTrades] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  // Form State
  const [strategyKey, setStrategyKey] = useState("cross_sectional_momentum");
  const [horizon, setHorizon] = useState("5d");
  const [capital, setCapital] = useState("1000000000");

  useEffect(() => {
    fetchBacktests();
  }, []);

  const fetchBacktests = async () => {
    try {
      const res = await fetch("/api/v1/backtests");
      if (res.ok) {
        const list = await res.json();
        setBacktests(list);
        if (list.length > 0) {
          selectBacktest(list[0].id);
        }
      }
    } catch (e) {
      console.error(e);
    }
  };

  const selectBacktest = async (id: string) => {
    try {
      const resDetail = await fetch(`/api/v1/backtests/${id}`);
      const dataDetail = await resDetail.json();
      setSelectedRun(dataDetail);

      const resTrades = await fetch(`/api/v1/backtests/${id}/trades`);
      const dataTrades = await resTrades.json();
      setTrades(dataTrades);
    } catch (e) {
      console.error(e);
    }
  };

  const handleLaunchBacktest = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await fetch("/api/v1/backtests", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: `بک‌تست ${strategyKey === "cross_sectional_momentum" ? "مومنتوم" : "پولبک"} افق ${horizon}`,
          strategy_key: strategyKey,
          horizon: horizon,
          initial_capital: parseFloat(capital),
        }),
      });
      if (res.ok) {
        await fetchBacktests();
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
      {/* Header card */}
      <div className="card-panel">
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.4rem" }}>
          <History size={20} color="var(--tse-green)" />
          <h2 style={{ fontSize: "1.1rem", fontWeight: 800, color: "var(--text-primary)" }}>
            شبیه‌ساز معاملات و آزمایشگاه بک‌تست (Event-Driven Backtester)
          </h2>
        </div>
        <p style={{ fontSize: "0.82rem", color: "var(--text-secondary)" }}>
          شبیه‌سازی دقیق و بدون نگاه به آینده (Next-Bar Fill) با کسر واقعی ۱.۲۵٪ کارمزد و مالیات بورس تهران، دامنه نوسان و شبیه‌سازی احتمال انجام سفارش در صف.
        </p>
      </div>

      {/* Backtest Launch Configuration Form */}
      <div className="card-panel">
        <form onSubmit={handleLaunchBacktest} style={{ display: "flex", flexWrap: "wrap", alignItems: "flex-end", gap: "1rem" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.3rem" }}>
            <label style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>استراتژی معاملاتی</label>
            <select
              value={strategyKey}
              onChange={(e) => setStrategyKey(e.target.value)}
              style={{
                backgroundColor: "var(--bg-surface)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "var(--radius-sm)",
                color: "var(--text-primary)",
                padding: "0.45rem 0.75rem",
                fontFamily: "inherit",
                fontSize: "0.85rem",
              }}
            >
              <option value="cross_sectional_momentum">مومنتوم مقطعی و قدرت نسبی</option>
              <option value="time_series_trend">روند زمانی و چینش میانگین‌ها</option>
              <option value="breakout_volume">شکست سقف با افزایش حجم</option>
              <option value="trend_pullback">پولبک در روند صعودی</option>
              <option value="client_flow">ورود پول هوشمند حقیقی</option>
            </select>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "0.3rem" }}>
            <label style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>افق خروج</label>
            <select
              value={horizon}
              onChange={(e) => setHorizon(e.target.value)}
              style={{
                backgroundColor: "var(--bg-surface)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "var(--radius-sm)",
                color: "var(--text-primary)",
                padding: "0.45rem 0.75rem",
                fontFamily: "inherit",
                fontSize: "0.85rem",
              }}
            >
              <option value="3d">۳ جلسه معاملاتی</option>
              <option value="5d">۵ جلسه معاملاتی</option>
              <option value="10d">۱۰ جلسه معاملاتی</option>
            </select>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "0.3rem" }}>
            <label style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>سرمایه اولیه (ریال)</label>
            <input
              type="number"
              value={capital}
              onChange={(e) => setCapital(e.target.value)}
              style={{
                backgroundColor: "var(--bg-surface)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "var(--radius-sm)",
                color: "var(--text-primary)",
                padding: "0.45rem 0.75rem",
                fontFamily: "inherit",
                fontSize: "0.85rem",
                width: "160px",
              }}
            />
          </div>

          <button type="submit" className="btn-primary" disabled={loading} style={{ padding: "0.55rem 1.25rem" }}>
            <Play size={16} />
            <span>{loading ? "در حال شبیه‌سازی..." : "اجرای شبیه‌سازی بک‌تست"}</span>
          </button>
        </form>
      </div>

      {/* Selected Backtest Performance Scorecard */}
      {selectedRun && (
        <>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "1rem" }}>
            <div className="card-panel">
              <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>بازده کل دوره (پس از هزینه)</div>
              <div style={{ fontSize: "1.4rem", fontWeight: 800, color: selectedRun.total_return_pct >= 0 ? "var(--tse-green)" : "var(--tse-red)", marginTop: "0.25rem" }} className="tabular-num">
                {selectedRun.total_return_pct >= 0 ? "+" : ""}{selectedRun.total_return_pct}٪
              </div>
            </div>

            <div className="card-panel">
              <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>نسبت شارپ (Sharpe Ratio)</div>
              <div style={{ fontSize: "1.4rem", fontWeight: 800, color: "var(--tse-blue)", marginTop: "0.25rem" }} className="tabular-num">
                {selectedRun.sharpe_ratio}
              </div>
            </div>

            <div className="card-panel">
              <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>نسبت سورتینو (Sortino)</div>
              <div style={{ fontSize: "1.4rem", fontWeight: 800, color: "var(--tse-blue)", marginTop: "0.25rem" }} className="tabular-num">
                {selectedRun.sortino_ratio}
              </div>
            </div>

            <div className="card-panel">
              <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>حداکثر افت سرمایه (Max Drawdown)</div>
              <div style={{ fontSize: "1.4rem", fontWeight: 800, color: "var(--tse-red)", marginTop: "0.25rem" }} className="tabular-num">
                {selectedRun.max_drawdown_pct}٪
              </div>
            </div>

            <div className="card-panel">
              <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>نرخ برد (Win Rate)</div>
              <div style={{ fontSize: "1.4rem", fontWeight: 800, color: "var(--tse-green)", marginTop: "0.25rem" }} className="tabular-num">
                {selectedRun.win_rate_pct}٪
              </div>
            </div>

            <div className="card-panel">
              <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>تعداد معاملات شبیه‌سازی شده</div>
              <div style={{ fontSize: "1.4rem", fontWeight: 800, color: "var(--text-primary)", marginTop: "0.25rem" }} className="tabular-num">
                {selectedRun.trade_count}
              </div>
            </div>
          </div>

          {/* Auditable Trade Logs Table */}
          <div className="card-panel" style={{ padding: 0, overflow: "hidden" }}>
            <div style={{ padding: "0.85rem 1rem", backgroundColor: "var(--bg-surface)", borderBottom: "1px solid var(--border-subtle)", fontWeight: 700, fontSize: "0.9rem" }}>
              دفترچه ثبت معاملات شبیه‌سازی شده (Auditable Trade Logs)
            </div>
            <div style={{ overflowX: "auto", maxHeight: "300px" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.82rem" }}>
                <thead>
                  <tr style={{ color: "var(--text-muted)", textAlign: "right", borderBottom: "1px solid var(--border-subtle)" }}>
                    <th style={{ padding: "0.6rem 0.8rem" }}>نماد</th>
                    <th style={{ padding: "0.6rem 0.8rem" }}>تاریخ ورود</th>
                    <th style={{ padding: "0.6rem 0.8rem" }}>قیمت ورود</th>
                    <th style={{ padding: "0.6rem 0.8rem" }}>تاریخ خروج</th>
                    <th style={{ padding: "0.6rem 0.8rem" }}>قیمت خروج</th>
                    <th style={{ padding: "0.6rem 0.8rem" }}>بازده خالص</th>
                    <th style={{ padding: "0.6rem 0.8rem" }}>سود/زیان خالص (ریال)</th>
                    <th style={{ padding: "0.6rem 0.8rem" }}>علت خروج</th>
                  </tr>
                </thead>
                <tbody>
                  {trades.map((tr) => {
                    const isWin = tr.net_pnl >= 0;
                    return (
                      <tr key={tr.id} style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                        <td style={{ padding: "0.6rem 0.8rem", fontWeight: 700 }}>{tr.symbol}</td>
                        <td style={{ padding: "0.6rem 0.8rem" }} className="tabular-num">{tr.entry_date}</td>
                        <td style={{ padding: "0.6rem 0.8rem" }} className="tabular-num">{tr.entry_price?.toLocaleString("fa-IR")}</td>
                        <td style={{ padding: "0.6rem 0.8rem" }} className="tabular-num">{tr.exit_date}</td>
                        <td style={{ padding: "0.6rem 0.8rem" }} className="tabular-num">{tr.exit_price?.toLocaleString("fa-IR")}</td>
                        <td style={{ padding: "0.6rem 0.8rem", color: isWin ? "var(--tse-green)" : "var(--tse-red)", fontWeight: 700 }} className="tabular-num">
                          {isWin ? "+" : ""}{tr.return_pct}٪
                        </td>
                        <td style={{ padding: "0.6rem 0.8rem", color: isWin ? "var(--tse-green)" : "var(--tse-red)" }} className="tabular-num">
                          {tr.net_pnl?.toLocaleString("fa-IR")}
                        </td>
                        <td style={{ padding: "0.6rem 0.8rem", color: "var(--text-secondary)" }}>{tr.exit_reason}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
