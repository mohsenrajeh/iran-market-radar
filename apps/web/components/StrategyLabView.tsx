"use client";

import React, { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, FlaskConical, Loader2 } from "lucide-react";

type Strategy = {
  key: string;
  name_fa: string;
  enabled: boolean;
  version: string;
  description_fa: string;
  supported_horizons: string[];
  historical_win_rate_pct: number | null;
  historical_brier_score: number | null;
  historical_trades: number;
  validation_status: "COMPLETED" | "NOT_RUN" | string;
  latest_backtest_id: string | null;
};

const metric = (value: number | null, suffix = "") => value == null ? "—" : `${value.toFixed(2)}${suffix}`;

export const StrategyLabView: React.FC = () => {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    fetch("/api/v1/strategies", { credentials: "include", cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();
      })
      .then((data) => { if (active) setStrategies(Array.isArray(data) ? data : []); })
      .catch((reason) => { if (active) setError(String(reason)); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  const validated = strategies.filter((item) => item.validation_status === "COMPLETED");

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem", direction: "rtl" }}>
      <div className="card-panel">
        <div style={{ display: "flex", justifyContent: "space-between", gap: "1rem", flexWrap: "wrap" }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <FlaskConical size={22} color="#a371f7" />
              <h2 style={{ margin: 0, fontSize: "1.15rem", fontWeight: 800 }}>کاتالوگ موتورهای استراتژی</h2>
            </div>
            <p style={{ color: "var(--text-secondary)", fontSize: "0.82rem", marginBottom: 0 }}>
              معیارهای عملکرد فقط از بک‌تست ذخیره‌شده نمایش داده می‌شوند؛ عدد تخمینی یا ماتریس همبستگی ساختگی تولید نمی‌شود.
            </p>
          </div>
          <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
            <span className="badge">{strategies.length} موتور ثبت‌شده</span>
            <span className="badge">{validated.length} موتور اعتبارسنجی‌شده</span>
          </div>
        </div>
      </div>

      {loading && (
        <div className="card-panel" style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <Loader2 size={18} /> در حال دریافت شواهد بک‌تست…
        </div>
      )}
      {error && (
        <div className="card-panel" style={{ color: "var(--tse-red)", display: "flex", gap: "0.5rem" }}>
          <AlertTriangle size={18} /> دریافت کاتالوگ ناموفق بود: {error}
        </div>
      )}

      {!loading && !error && (
        <div className="card-panel" style={{ padding: 0, overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "right", fontSize: "0.82rem" }}>
            <thead style={{ backgroundColor: "#131b2e", borderBottom: "1px solid #1e293b" }}>
              <tr style={{ color: "var(--text-muted)" }}>
                <th style={{ padding: "0.75rem 1rem" }}>استراتژی</th>
                <th style={{ padding: "0.75rem" }}>خانواده/افق</th>
                <th style={{ padding: "0.75rem" }}>وضعیت اعتبارسنجی</th>
                <th style={{ padding: "0.75rem" }}>Win Rate</th>
                <th style={{ padding: "0.75rem" }}>Brier</th>
                <th style={{ padding: "0.75rem" }}>N</th>
              </tr>
            </thead>
            <tbody>
              {strategies.map((strategy) => {
                const isValidated = strategy.validation_status === "COMPLETED";
                return (
                  <tr key={strategy.key} style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                    <td style={{ padding: "0.8rem 1rem" }}>
                      <div style={{ fontWeight: 800 }}>{strategy.name_fa}</div>
                      <div style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>
                        {strategy.key} · v{strategy.version}
                      </div>
                    </td>
                    <td style={{ padding: "0.8rem" }}>{strategy.supported_horizons.join("، ")}</td>
                    <td style={{ padding: "0.8rem", color: isValidated ? "var(--tse-green)" : "#f59e0b" }}>
                      <span style={{ display: "inline-flex", gap: "0.35rem", alignItems: "center" }}>
                        {isValidated ? <CheckCircle2 size={15} /> : <AlertTriangle size={15} />}
                        {isValidated ? "دارای بک‌تست ثبت‌شده" : "هنوز بک‌تست معتبر ثبت نشده"}
                      </span>
                    </td>
                    <td className="tabular-num" style={{ padding: "0.8rem" }}>{metric(strategy.historical_win_rate_pct, "٪")}</td>
                    <td className="tabular-num" style={{ padding: "0.8rem" }}>{metric(strategy.historical_brier_score)}</td>
                    <td className="tabular-num" style={{ padding: "0.8rem" }}>{strategy.historical_trades || "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {strategies.length === 0 && (
            <div style={{ padding: "1.5rem", color: "var(--text-muted)" }}>هیچ موتور استراتژی ثبت نشده است.</div>
          )}
        </div>
      )}

      <div className="card-panel" style={{ color: "var(--text-secondary)", fontSize: "0.82rem" }}>
        ماتریس همبستگی زمانی نمایش داده می‌شود که بازده خارج‌ازنمونه‌ی هم‌دوره برای حداقل دو استراتژی ذخیره شده باشد.
      </div>
    </div>
  );
};
