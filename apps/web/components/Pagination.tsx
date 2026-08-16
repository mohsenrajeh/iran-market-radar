"use client";

import React from "react";
import { ChevronRight, ChevronLeft } from "lucide-react";

interface PaginationProps {
  currentPage: number;
  totalItems: number;
  pageSize: number;
  onPageChange: (page: number) => void;
  onPageSizeChange?: (pageSize: number) => void;
  pageSizeOptions?: number[];
}

export const Pagination: React.FC<PaginationProps> = ({
  currentPage,
  totalItems,
  pageSize,
  onPageChange,
  onPageSizeChange,
  pageSizeOptions = [9, 18, 36],
}) => {
  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));
  const safePage = Math.min(Math.max(1, currentPage), totalPages);

  const startItem = totalItems === 0 ? 0 : (safePage - 1) * pageSize + 1;
  const endItem = Math.min(safePage * pageSize, totalItems);

  // Generate page numbers to show (with ellipsis if large)
  const getPageNumbers = () => {
    const pages: (number | string)[] = [];
    if (totalPages <= 7) {
      for (let i = 1; i <= totalPages; i++) pages.push(i);
    } else {
      if (safePage <= 3) {
        pages.push(1, 2, 3, 4, "...", totalPages);
      } else if (safePage >= totalPages - 2) {
        pages.push(1, "...", totalPages - 3, totalPages - 2, totalPages - 1, totalPages);
      } else {
        pages.push(1, "...", safePage - 1, safePage, safePage + 1, "...", totalPages);
      }
    }
    return pages;
  };

  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        flexWrap: "wrap",
        gap: "1rem",
        padding: "0.85rem 1.25rem",
        backgroundColor: "#0d1322",
        borderRadius: "8px",
        border: "1px solid #1e293b",
        marginTop: "1.25rem",
        fontSize: "0.82rem",
        color: "#94a3b8",
      }}
    >
      {/* Left / Info & Page Size */}
      <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
        <span>
          نمایش <strong style={{ color: "#f8fafc" }}>{startItem.toLocaleString("fa-IR")}</strong> تا{" "}
          <strong style={{ color: "#f8fafc" }}>{endItem.toLocaleString("fa-IR")}</strong> از مجموع{" "}
          <strong style={{ color: "#38bdf8" }}>{totalItems.toLocaleString("fa-IR")}</strong> مورد
        </span>

        {onPageSizeChange && (
          <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
            <span style={{ fontSize: "0.75rem" }}>تعداد در صفحه:</span>
            <select
              value={pageSize}
              onChange={(e) => {
                onPageSizeChange(Number(e.target.value));
                onPageChange(1);
              }}
              style={{
                backgroundColor: "#131b2e",
                color: "#f8fafc",
                border: "1px solid #334155",
                borderRadius: "4px",
                padding: "2px 6px",
                fontSize: "0.78rem",
                fontFamily: "inherit",
                cursor: "pointer",
              }}
            >
              {pageSizeOptions.map((opt) => (
                <option key={opt} value={opt}>
                  {opt.toLocaleString("fa-IR")}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Right / Page navigation buttons */}
      <div style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
        <button
          onClick={() => onPageChange(safePage - 1)}
          disabled={safePage <= 1}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "2px",
            padding: "4px 10px",
            borderRadius: "5px",
            backgroundColor: safePage <= 1 ? "rgba(30, 41, 59, 0.4)" : "#1e293b",
            color: safePage <= 1 ? "#475569" : "#cbd5e1",
            border: "1px solid #334155",
            cursor: safePage <= 1 ? "not-allowed" : "pointer",
            fontFamily: "inherit",
            fontSize: "0.78rem",
            fontWeight: 700,
          }}
        >
          <ChevronRight size={15} />
          <span>قبلی</span>
        </button>

        {getPageNumbers().map((p, idx) => {
          if (p === "...") {
            return (
              <span key={`dots-${idx}`} style={{ padding: "0 4px", color: "#64748b" }}>
                ...
              </span>
            );
          }
          const isCurrent = p === safePage;
          return (
            <button
              key={`page-${p}`}
              onClick={() => onPageChange(p as number)}
              style={{
                width: "30px",
                height: "30px",
                borderRadius: "5px",
                backgroundColor: isCurrent ? "#38bdf8" : "#131b2e",
                color: isCurrent ? "#0f172a" : "#cbd5e1",
                border: isCurrent ? "1px solid #38bdf8" : "1px solid #334155",
                fontWeight: 800,
                cursor: "pointer",
                fontFamily: "inherit",
                fontSize: "0.82rem",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              {(p as number).toLocaleString("fa-IR")}
            </button>
          );
        })}

        <button
          onClick={() => onPageChange(safePage + 1)}
          disabled={safePage >= totalPages}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "2px",
            padding: "4px 10px",
            borderRadius: "5px",
            backgroundColor: safePage >= totalPages ? "rgba(30, 41, 59, 0.4)" : "#1e293b",
            color: safePage >= totalPages ? "#475569" : "#cbd5e1",
            border: "1px solid #334155",
            cursor: safePage >= totalPages ? "not-allowed" : "pointer",
            fontFamily: "inherit",
            fontSize: "0.78rem",
            fontWeight: 700,
          }}
        >
          <span>بعدی</span>
          <ChevronLeft size={15} />
        </button>
      </div>
    </div>
  );
};
