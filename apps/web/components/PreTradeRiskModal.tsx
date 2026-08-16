"use client";

import React, { useEffect, useState } from "react";
import { toPersianDigits } from "../lib/formatters";

interface PreTradeRiskTicketData {
  symbol: string;
  decision: string;
  decision_reason_fa: string;
  current_price: number;
  planned_entry: number;
  stop_price: number;
  target1_price: number;
  target2_price: number;
  gross_reward_risk_ratio: number;
  net_reward_risk_ratio: number;
  current_r: number;
  chase_status: string;
  portfolio_nav_rials: number;
  risk_budget_rials: number;
  risk_pct_nav: number;
  effective_loss_pct: number;
  recommended_position_rials: number;
  recommended_quantity: number;
  recommended_weight_pct: number;
  stage1_quantity: number;
  stage1_amount_rials: number;
  stage2_quantity: number;
  stage2_amount_rials: number;
  stage3_quantity: number;
  stage3_amount_rials: number;
  estimated_fees_rials: number;
  estimated_tax_rials: number;
  estimated_slippage_rials: number;
  total_execution_cost_rials: number;
  cash_after_trade_rials: number;
  cash_pct_after_trade: number;
  gross_exposure_after_trade_pct: number;
  sector_exposure_after_trade_pct: number;
  cluster_exposure_after_trade_pct: number;
  total_open_risk_after_trade_pct: number;
  daily_new_risk_after_trade_pct: number;
  policy_version: string;
  regime: string;
  is_kill_switch_active: boolean;
}

interface PreTradeRiskModalProps {
  isOpen: boolean;
  onClose: () => void;
  signalId: string | null;
  symbol: string;
  onOrderSuccess?: (msg: string) => void;
}

export default function PreTradeRiskModal({
  isOpen,
  onClose,
  signalId,
  symbol,
  onOrderSuccess,
}: PreTradeRiskModalProps) {
  const [ticket, setTicket] = useState<PreTradeRiskTicketData | null>(null);
  const [loading, setLoading] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && signalId) {
      fetchTicket(signalId);
    } else {
      setTicket(null);
      setError(null);
    }
  }, [isOpen, signalId]);

  const fetchTicket = async (sigId: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/v1/paper/pre-trade-ticket/${sigId}`);
      if (!res.ok) {
        throw new Error("خطا در محاسبه و صدور برگه ارزیابی ریسک قبل از معامله.");
      }
      const data = await res.json();
      setTicket(data);
    } catch (err: any) {
      setError(err.message || "خطای نامشخص در دریافت اطلاعات مدیریت سرمایه");
    } finally {
      setLoading(false);
    }
  };

  const handleExecuteOrder = async () => {
    if (!signalId || !ticket || ticket.decision !== "APPROVED") return;
    setExecuting(true);
    try {
      const res = await fetch("/api/paper/orders/from-signal", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          signal_id: signalId,
          quantity: ticket.stage1_quantity || ticket.recommended_quantity,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "خطا در ثبت سفارش آزمایشی");
      }
      if (onOrderSuccess) {
        onOrderSuccess(data.message || `سفارش پله اول خرید نماد ${symbol} با موفقیت ثبت شد.`);
      }
      onClose();
    } catch (err: any) {
      setError(err.message || "خطا در اجرای سفارش");
    } finally {
      setExecuting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4 animate-fadeIn">
      <div className="bg-[#111827] border border-slate-700/80 rounded-2xl w-full max-w-3xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden text-slate-100 font-sans">
        {/* Header */}
        <div className="p-4 sm:p-5 border-b border-slate-800 flex items-center justify-between bg-gradient-to-r from-slate-900 to-[#111827]">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400 text-lg font-bold">
              🛡️
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-lg font-bold text-slate-100">
                  تیکت اعتبارسنجی ریسک قبل از معامله (Pre-Trade Risk Ticket)
                </h3>
                <span className="text-xs bg-cyan-500/10 text-cyan-400 px-2 py-0.5 rounded border border-cyan-500/20 font-mono">
                  {symbol}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                تخصیص سرمایه چندعاملی، کنترل همبستگی، گیت‌های نقدشوندگی و محاسبه پله‌های ورود
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-200 hover:bg-slate-800/80 p-2 rounded-lg transition-colors text-lg"
          >
            ✕
          </button>
        </div>

        {/* Content Body */}
        <div className="p-5 overflow-y-auto space-y-5 flex-1 custom-scrollbar">
          {loading ? (
            <div className="py-16 text-center space-y-3">
              <div className="w-10 h-10 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin mx-auto" />
              <p className="text-sm text-slate-400">
                در حال حل مدل بهینه‌سازی چندمحدودیتی و بررسی گیت‌های مدیریت ریسک...
              </p>
            </div>
          ) : error ? (
            <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-sm">
              {error}
            </div>
          ) : ticket ? (
            <>
              {/* Decision Banner */}
              <div
                className={`p-4 rounded-xl border flex items-center justify-between ${
                  ticket.decision === "APPROVED"
                    ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-300"
                    : ticket.decision === "WAIT_CHASE"
                    ? "bg-amber-500/10 border-amber-500/30 text-amber-300"
                    : "bg-rose-500/10 border-rose-500/30 text-rose-300"
                }`}
              >
                <div className="flex items-center gap-3">
                  <span className="text-2xl">
                    {ticket.decision === "APPROVED" ? "✅" : ticket.decision === "WAIT_CHASE" ? "⚠️" : "⛔"}
                  </span>
                  <div>
                    <div className="font-bold text-sm">
                      وضعیت تأیید گیت ریسک:{" "}
                      {ticket.decision === "APPROVED"
                        ? "تأیید کامل (مجاز برای معامله آزمایشی)"
                        : ticket.decision === "WAIT_CHASE"
                        ? "فرار قیمت (Chase Blocked — ورود معلق)"
                        : "رد سفارش توسط گیت ریسک (Blocked)"}
                    </div>
                    <div className="text-xs mt-0.5 opacity-90">{ticket.decision_reason_fa}</div>
                  </div>
                </div>
                <div className="text-right font-mono text-xs">
                  <div className="text-slate-400">سیاست ریسک</div>
                  <div className="font-semibold text-slate-200">{ticket.policy_version}</div>
                </div>
              </div>

              {/* 1. Price Levels & R-Multiples */}
              <div className="bg-slate-900/60 p-4 rounded-xl border border-slate-800">
                <div className="text-xs font-semibold text-slate-400 mb-3 flex items-center gap-1.5">
                  <span>📊</span> سطوح قیمتی و ضرایب ریسک (R-Multiple)
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
                  <div className="bg-slate-800/50 p-2.5 rounded-lg border border-slate-700/50">
                    <div className="text-[11px] text-slate-400">قیمت جاری</div>
                    <div className="text-sm font-bold text-slate-100 mt-1">
                      {ticket.current_price.toLocaleString()} ریال
                    </div>
                    <div className="text-[10px] text-slate-400 mt-0.5 font-mono">
                      فاصله: {ticket.current_r > 0 ? `+${ticket.current_r}R` : `${ticket.current_r}R`}
                    </div>
                  </div>
                  <div className="bg-rose-500/5 p-2.5 rounded-lg border border-rose-500/20">
                    <div className="text-[11px] text-rose-400">حد ضرر (Stop)</div>
                    <div className="text-sm font-bold text-rose-300 mt-1">
                      {ticket.stop_price.toLocaleString()} ریال
                    </div>
                    <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "0.2rem" }} className="tabular-num">
                      فاصله: {toPersianDigits((((ticket.stop_price - ticket.planned_entry) / ticket.planned_entry) * 100).toFixed(1))}٪
                    </div>
                  </div>
                  <div className="bg-emerald-500/5 p-2.5 rounded-lg border border-emerald-500/20">
                    <div className="text-[11px] text-emerald-400">هدف اول (Target 1)</div>
                    <div className="text-sm font-bold text-emerald-300 mt-1">
                      {ticket.target1_price.toLocaleString()} ریال
                    </div>
                    <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "0.2rem" }} className="tabular-num">
                      فاصله: +{toPersianDigits((((ticket.target1_price - ticket.planned_entry) / ticket.planned_entry) * 100).toFixed(1))}٪
                    </div>
                  </div>
                  <div className="bg-cyan-500/5 p-2.5 rounded-lg border border-cyan-500/20">
                    <div className="text-[11px] text-cyan-400">نسبت سود به ریسک خالص</div>
                    <div className="text-sm font-bold text-cyan-300 mt-1 font-mono">
                      1:{ticket.net_reward_risk_ratio}
                    </div>
                    <div className="text-[10px] text-slate-400 mt-0.5">
                      ناخالص: 1:{ticket.gross_reward_risk_ratio}
                    </div>
                  </div>
                </div>
              </div>

              {/* 2. Position Sizing Solver Output */}
              <div className="bg-slate-900/60 p-4 rounded-xl border border-slate-800">
                <div className="text-xs font-semibold text-slate-400 mb-3 flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <span>⚖️</span> تخصیص سرمایه و مدیریت ریسک موقعیت
                  </div>
                  <span className="text-[11px] text-cyan-400 font-mono">
                    ریسک مجاز: {ticket.risk_pct_nav}٪ ارزش پورتفو
                  </span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                  <div className="bg-slate-800/40 p-3 rounded-lg border border-slate-700/40">
                    <div className="text-[11px] text-slate-400">حجم کل پیشنهادی</div>
                    <div className="text-base font-bold text-slate-100 mt-1 font-mono">
                      {ticket.recommended_quantity.toLocaleString()} سهم
                    </div>
                    <div className="text-[10px] text-slate-400 mt-0.5">
                      {(ticket.recommended_position_rials / 10_000_000).toLocaleString(undefined, {
                        maximumFractionDigits: 1,
                      })}{" "}
                      میلیون تومان ({ticket.recommended_weight_pct}٪ NAV)
                    </div>
                  </div>
                  <div className="bg-slate-800/40 p-3 rounded-lg border border-slate-700/40">
                    <div className="text-[11px] text-slate-400">بودجه ریسک معامله (1R)</div>
                    <div className="text-base font-bold text-amber-300 mt-1 font-mono">
                      {(ticket.risk_budget_rials / 10_000_000).toLocaleString(undefined, {
                        maximumFractionDigits: 1,
                      })}{" "}
                      میلیون تومان
                    </div>
                    <div className="text-[10px] text-slate-400 mt-0.5">
                      زیان مؤثر کل: {ticket.effective_loss_pct}٪
                    </div>
                  </div>
                  <div className="bg-slate-800/40 p-3 rounded-lg border border-slate-700/40 col-span-2 sm:col-span-1">
                    <div className="text-[11px] text-slate-400">هزینه‌های معاملاتی و اسلیپیج</div>
                    <span style={{ fontSize: "0.85rem", fontWeight: 700, color: "var(--text-primary)" }} className="tabular-num">
                      {toPersianDigits((ticket.total_execution_cost_rials / 10_000_000).toFixed(2))} م تومان
                    </span>
                    <div className="text-[10px] text-slate-400 mt-0.5">
                      کارمزد بورس (۱.۲۵۶٪) + اسلیپیج
                    </div>
                  </div>
                </div>
              </div>

              {/* 3. Staged Entry Strategy (40% / 35% / 25%) */}
              <div className="bg-slate-900/60 p-4 rounded-xl border border-slate-800">
                <div className="text-xs font-semibold text-slate-400 mb-3 flex items-center gap-1.5">
                  <span>🪜</span> برنامه ورود پله‌ای کنترل‌شده (Staged Scale-In)
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div className="p-3 rounded-lg bg-emerald-500/5 border border-emerald-500/20">
                    <div className="flex items-center justify-between text-xs font-bold text-emerald-400">
                      <span>پله ۱: ورود اولیه (۴۰٪)</span>
                      <span className="text-[10px] bg-emerald-500/20 px-1.5 py-0.5 rounded">هم‌اکنون</span>
                    </div>
                    <div className="text-sm font-bold text-slate-100 mt-2 font-mono">
                      {ticket.stage1_quantity.toLocaleString()} سهم
                    </div>
                    <span style={{ fontSize: "0.85rem", fontWeight: 700, color: "var(--text-primary)" }} className="tabular-num">
                      {toPersianDigits((ticket.stage1_amount_rials / 10_000_000).toFixed(1))} میلیون تومان
                    </span>
                  </div>

                  <div className="p-3 rounded-lg bg-slate-800/40 border border-slate-700/40">
                    <div className="flex items-center justify-between text-xs font-bold text-slate-300">
                      <span>پله ۲: تأیید سود (۳۵٪)</span>
                      <span className="text-[10px] text-slate-400">در سود +0.5R</span>
                    </div>
                    <div className="text-sm font-bold text-slate-300 mt-2 font-mono">
                      {ticket.stage2_quantity.toLocaleString()} سهم
                    </div>
                    <span style={{ fontSize: "0.85rem", fontWeight: 700, color: "var(--text-primary)" }} className="tabular-num">
                      {toPersianDigits((ticket.stage2_amount_rials / 10_000_000).toFixed(1))} میلیون تومان
                    </span>
                  </div>

                  <div className="p-3 rounded-lg bg-slate-800/40 border border-slate-700/40">
                    <div className="flex items-center justify-between text-xs font-bold text-slate-300">
                      <span>پله ۳: جهش نهایی (۲۵٪)</span>
                      <span className="text-[10px] text-slate-400">در سود +1.0R</span>
                    </div>
                    <div className="text-sm font-bold text-slate-300 mt-2 font-mono">
                      {ticket.stage3_quantity.toLocaleString()} سهم
                    </div>
                    <span style={{ fontSize: "0.85rem", fontWeight: 700, color: "var(--text-primary)" }} className="tabular-num">
                      {toPersianDigits((ticket.stage3_amount_rials / 10_000_000).toFixed(1))} میلیون تومان
                    </span>
                  </div>
                </div>
              </div>

              {/* 4. Portfolio Impact Post-Trade */}
              <div className="bg-slate-900/60 p-4 rounded-xl border border-slate-800">
                <div className="text-xs font-semibold text-slate-400 mb-2 flex items-center gap-1.5">
                  <span>🌐</span> پیش‌بینی وضعیت سبد دارایی پس از انجام معامله
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center text-xs">
                  <div className="bg-slate-800/30 p-2 rounded border border-slate-800">
                    <div className="text-slate-400">نقدینگی پس از خرید</div>
                    <div className="font-bold text-slate-200 mt-1 font-mono">
                      {ticket.cash_pct_after_trade}٪ (کف ۳۰٪)
                    </div>
                  </div>
                  <div className="bg-slate-800/30 p-2 rounded border border-slate-800">
                    <div className="text-slate-400">درگیری ناخالص سهام</div>
                    <div className="font-bold text-slate-200 mt-1 font-mono">
                      {ticket.gross_exposure_after_trade_pct}٪ (سقف ۷۰٪)
                    </div>
                  </div>
                  <div className="bg-slate-800/30 p-2 rounded border border-slate-800">
                    <div className="text-slate-400">تمرکز در صنعت</div>
                    <div className="font-bold text-slate-200 mt-1 font-mono">
                      {ticket.sector_exposure_after_trade_pct}٪ (سقف ۱۸٪)
                    </div>
                  </div>
                  <div className="bg-slate-800/30 p-2 rounded border border-slate-800">
                    <div className="text-slate-400">ریسک باز کل سبد</div>
                    <div className="font-bold text-slate-200 mt-1 font-mono">
                      {ticket.total_open_risk_after_trade_pct}٪ (سقف ۲.۵٪)
                    </div>
                  </div>
                </div>
              </div>
            </>
          ) : null}
        </div>

        {/* Footer Actions */}
        <div className="p-4 border-t border-slate-800 bg-slate-900/80 flex items-center justify-between">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl text-sm font-semibold text-slate-300 hover:bg-slate-800 transition-colors"
          >
            انصراف و بازگشت
          </button>
          <div className="flex items-center gap-3">
            {ticket?.decision === "APPROVED" && (
              <button
                onClick={handleExecuteOrder}
                disabled={executing}
                className="px-6 py-2.5 rounded-xl text-sm font-bold bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white shadow-lg shadow-emerald-500/20 transition-all flex items-center gap-2 disabled:opacity-50"
              >
                {executing ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    <span>در حال ثبت در دفترکل...</span>
                  </>
                ) : (
                  <>
                    <span>⚡ ثبت سفارش پله اول خرید ({ticket?.stage1_quantity.toLocaleString()} سهم)</span>
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
