"use client";
import React from "react";
import { Layers, ArrowUpRight, TrendingUp, DollarSign } from "lucide-react";

interface SectorsViewProps {
  sectors: any[];
}

export const SectorsView: React.FC<SectorsViewProps> = ({ sectors }) => {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
      {/* Header card */}
      <div className="card-panel">
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.4rem" }}>
          <Layers size={20} color="var(--tse-blue)" />
          <h2 style={{ fontSize: "1.1rem", fontWeight: 800, color: "var(--text-primary)" }}>
            دیده‌بان و ماتریس چرخش نقدینگی صنایع (Sector Rotation Radar)
          </h2>
        </div>
        <p style={{ fontSize: "0.82rem", color: "var(--text-secondary)" }}>
          رتبه‌بندی صنایع بر اساس برآیند ورود پول حقیقی، مومنتوم ۲۰ روزه و وسعت نمادهای صعودی نسبت به شاخص کل بورس.
        </p>
      </div>

      {/* Sectors Grid / Table */}
      <div className="card-panel" style={{ padding: 0, overflow: "hidden" }}>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
            <thead>
              <tr style={{ backgroundColor: "var(--bg-surface)", borderBottom: "1px solid var(--border-subtle)", color: "var(--text-secondary)", textAlign: "right" }}>
                <th style={{ padding: "0.85rem 1rem" }}>رتبه قدرت نسبی</th>
                <th style={{ padding: "0.85rem 1rem" }}>نام صنعت</th>
                <th style={{ padding: "0.85rem 1rem" }}>مومنتوم ۲۰ روزه</th>
                <th style={{ padding: "0.85rem 1rem" }}>وسعت مثبت (Breadth)</th>
                <th style={{ padding: "0.85rem 1rem" }}>ورود پول حقیقی (ریال)</th>
                <th style={{ padding: "0.85rem 1rem" }}>ارزش معاملات روزانه</th>
                <th style={{ padding: "0.85rem 1rem" }}>تعداد فرصت‌های فعال</th>
              </tr>
            </thead>
            <tbody>
              {sectors.map((sec) => (
                <tr key={sec.sector_id} style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                  <td style={{ padding: "0.85rem 1rem" }}>
                    <span style={{
                      backgroundColor: sec.relative_strength_rank <= 3 ? "rgba(46, 160, 67, 0.2)" : "var(--bg-surface)",
                      color: sec.relative_strength_rank <= 3 ? "var(--tse-green)" : "var(--text-secondary)",
                      padding: "0.2rem 0.6rem",
                      borderRadius: "4px",
                      fontWeight: 800,
                    }}>
                      #{sec.relative_strength_rank}
                    </span>
                  </td>
                  <td style={{ padding: "0.85rem 1rem", fontWeight: 700, color: "var(--text-primary)" }}>
                    {sec.name_fa}
                  </td>
                  <td style={{ padding: "0.85rem 1rem", color: "var(--tse-green)", fontWeight: 700 }} className="tabular-num">
                    +{sec.momentum_20d_pct}٪
                  </td>
                  <td style={{ padding: "0.85rem 1rem" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                      <div style={{ width: "60px", height: "6px", backgroundColor: "var(--bg-surface)", borderRadius: "3px", overflow: "hidden" }}>
                        <div style={{ width: `${sec.breadth_pct}%`, height: "100%", backgroundColor: "var(--tse-blue)" }} />
                      </div>
                      <span className="tabular-num" style={{ fontSize: "0.8rem" }}>{sec.breadth_pct}٪</span>
                    </div>
                  </td>
                  <td style={{ padding: "0.85rem 1rem", color: sec.net_real_inflow_rials >= 0 ? "var(--tse-green)" : "var(--tse-red)", fontWeight: 600 }} className="tabular-num">
                    {(sec.net_real_inflow_rials / 1_000_000_000).toLocaleString("fa-IR", { maximumFractionDigits: 1 })} میلیارد
                  </td>
                  <td style={{ padding: "0.85rem 1rem", color: "var(--text-secondary)" }} className="tabular-num">
                    {(sec.turnover_value_rials / 1_000_000_000).toLocaleString("fa-IR", { maximumFractionDigits: 0 })} میلیارد
                  </td>
                  <td style={{ padding: "0.85rem 1rem" }}>
                    <span style={{ backgroundColor: "rgba(56, 139, 253, 0.15)", color: "var(--tse-blue)", padding: "0.15rem 0.5rem", borderRadius: "4px", fontWeight: 700 }}>
                      {sec.opportunity_count} نماد
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
