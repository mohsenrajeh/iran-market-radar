"use client";

import React, { useState, useEffect } from "react";

interface CodalFilingItem {
  id: string;
  source_filing_id: string;
  symbol: string;
  title: string;
  filing_type: string;
  filing_type_fa: string;
  sentiment: string;
  sentiment_fa: string;
  impact_score: number;
  summary_fa: string;
  published_at: string;
  url: string;
}

export default function CodalFeedView() {
  const [filings, setFilings] = useState<CodalFilingItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterType, setFilterType] = useState<string>("ALL");
  const [filterSentiment, setFilterSentiment] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    fetchFeed();
  }, []);

  const fetchFeed = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/fundamentals/codal-feed?limit=50");
      if (res.ok) {
        const data = await res.json();
        setFilings(data);
      }
    } catch (e) {
      console.error("Failed to load codal feed", e);
    } finally {
      setLoading(false);
    }
  };

  const filteredFilings = filings.filter((f) => {
    if (filterType !== "ALL" && f.filing_type !== filterType) return false;
    if (filterSentiment !== "ALL" && f.sentiment !== filterSentiment) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return (
        f.symbol.toLowerCase().includes(q) ||
        f.title.toLowerCase().includes(q) ||
        f.summary_fa.toLowerCase().includes(q)
      );
    }
    return true;
  });

  return (
    <div className="space-y-6 animate-fadeIn font-sans">
      {/* Header & Controls */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-900/60 p-5 rounded-2xl border border-slate-800 backdrop-blur-md">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold text-slate-100">
              فید بلادرنگ اطلاعیه‌ها و صورت‌های مالی کدال (Codal / SEDRA)
            </h2>
            <span className="bg-emerald-500/10 text-emerald-400 text-xs px-2.5 py-0.5 rounded-full border border-emerald-500/20 font-medium">
              ● استریم زنده
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            پردازش زبان طبیعی (NLP)، طبقه‌بندی هوشمند افشاهای الف/ب و استخراج فوری سیگنال‌های مالیاتی و سودآوری
          </p>
        </div>

        {/* Filter Pills */}
        <div className="flex flex-wrap items-center gap-2">
          <input
            type="text"
            placeholder="جستجوی نماد یا موضوع..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="bg-slate-800/80 border border-slate-700 text-xs text-slate-200 px-3 py-2 rounded-xl focus:outline-none focus:border-cyan-500 w-48"
          />
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="bg-slate-800/80 border border-slate-700 text-xs text-slate-200 px-3 py-2 rounded-xl focus:outline-none focus:border-cyan-500"
          >
            <option value="ALL">همه دسته‌بندی‌ها</option>
            <option value="monthly_sales">گزارش فعالیت ماهانه</option>
            <option value="material_disclosure_a">افشای بااهمیت الف</option>
            <option value="material_disclosure_b">افشای بااهمیت ب</option>
            <option value="interim_statement">صورت‌های مالی میاندوره‌ای</option>
            <option value="capital_increase">افزایش سرمایه</option>
            <option value="general_meeting">تصمیمات مجمع</option>
          </select>
          <select
            value={filterSentiment}
            onChange={(e) => setFilterSentiment(e.target.value)}
            className="bg-slate-800/80 border border-slate-700 text-xs text-slate-200 px-3 py-2 rounded-xl focus:outline-none focus:border-cyan-500"
          >
            <option value="ALL">همه اثرات</option>
            <option value="positive">اثر مثبت بر سود</option>
            <option value="neutral">خنثی / اطلاع‌رسانی</option>
            <option value="negative">اثر منفی / کاهشی</option>
          </select>
          <button
            onClick={fetchFeed}
            className="bg-slate-800 hover:bg-slate-700 text-slate-200 p-2 rounded-xl border border-slate-700 transition-colors"
            title="بروزرسانی فید"
          >
            🔄
          </button>
        </div>
      </div>

      {/* Feed Stream */}
      {loading ? (
        <div className="py-20 text-center space-y-3 bg-slate-900/30 rounded-2xl border border-slate-800">
          <div className="w-10 h-10 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-sm text-slate-400">در حال دریافت و تجزیه اطلاعیه‌های کدال...</p>
        </div>
      ) : filteredFilings.length === 0 ? (
        <div className="py-16 text-center text-slate-400 bg-slate-900/30 rounded-2xl border border-slate-800">
          اطلاعیه‌ای با فیلترهای انتخابی یافت نشد.
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {filteredFilings.map((filing) => {
            const isPositive = filing.sentiment === "positive";
            const isNegative = filing.sentiment === "negative";

            return (
              <div
                key={filing.id}
                className="bg-slate-900/60 p-5 rounded-2xl border border-slate-800/80 hover:border-slate-700 transition-all hover:shadow-lg space-y-3"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800/60 pb-3">
                  <div className="flex items-center gap-3">
                    <span className="bg-cyan-500/10 text-cyan-400 px-3 py-1 rounded-xl font-bold text-sm border border-cyan-500/20 font-mono">
                      {filing.symbol}
                    </span>
                    <span className="text-xs bg-slate-800 text-slate-300 px-2.5 py-1 rounded-lg border border-slate-700">
                      {filing.filing_type_fa}
                    </span>
                    <span
                      className={`text-xs px-2.5 py-1 rounded-lg border ${
                        isPositive
                          ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                          : isNegative
                          ? "bg-rose-500/10 text-rose-400 border-rose-500/20"
                          : "bg-slate-800 text-slate-300 border-slate-700"
                      }`}
                    >
                      {filing.sentiment_fa}
                    </span>
                  </div>
                  <div className="text-xs text-slate-400 flex items-center gap-3">
                    <span className="font-mono">🕒 {filing.published_at}</span>
                    <span className="bg-slate-800 text-cyan-400 px-2 py-0.5 rounded font-mono text-[11px]">
                      امتیاز اثر: {filing.impact_score} / 10
                    </span>
                  </div>
                </div>

                <div className="space-y-1.5">
                  <h4 className="text-sm font-semibold text-slate-100 leading-relaxed">
                    {filing.title}
                  </h4>
                  <p className="text-xs text-slate-300 leading-relaxed bg-slate-800/40 p-3 rounded-xl border border-slate-800">
                    <span className="font-semibold text-cyan-400 ml-1">💡 تحلیل خلاصه هوش مصنوعی:</span>
                    {filing.summary_fa}
                  </p>
                </div>

                <div className="flex items-center justify-between pt-1 text-xs">
                  <div className="text-slate-400 text-[11px] font-mono">
                    شناسه نامه: {filing.source_filing_id}
                  </div>
                  <a
                    href={filing.url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-cyan-400 hover:text-cyan-300 flex items-center gap-1 font-medium hover:underline"
                  >
                    <span>مشاهده متن کامل در سامانه کدال</span>
                    <span>↗</span>
                  </a>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
