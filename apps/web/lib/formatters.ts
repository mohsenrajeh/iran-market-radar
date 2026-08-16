/**
 * Persian Number & Financial Formatting Utilities
 * Iran Market Radar — Typography & Financial Aesthetics
 */

const PERSIAN_DIGITS = ["۰", "۱", "۲", "۳", "۴", "۵", "۶", "۷", "۸", "۹"];

/**
 * Converts English digits to Persian digits
 */
export function toPersianDigits(num: number | string | null | undefined): string {
  if (num === null || num === undefined || num === "") return "۰";
  const str = String(num);
  return str.replace(/[0-9]/g, (d) => PERSIAN_DIGITS[parseInt(d, 10)]);
}

/**
 * Formats a number with thousand separators (e.g. 10,000,000 -> ۱۰,۰۰۰,۰۰۰)
 */
export function formatNumberFa(num: number | string | null | undefined): string {
  if (num === null || num === undefined || isNaN(Number(num))) return "۰";
  const n = typeof num === "number" ? num : parseFloat(num);
  const parts = Math.round(n).toString().split(".");
  parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  return toPersianDigits(parts.join("."));
}

/**
 * Formats decimal numbers (e.g. 79.4 -> ۷۹.۴)
 */
export function formatDecimalFa(num: number | string | null | undefined, decimals = 1): string {
  if (num === null || num === undefined || isNaN(Number(num))) return "۰";
  const n = typeof num === "number" ? num : parseFloat(num);
  return toPersianDigits(n.toFixed(decimals));
}

/**
 * Formats currency in Tomans with Persian digits
 */
export function formatToman(num: number | string | null | undefined): string {
  return `${formatNumberFa(num)} تومان`;
}

/**
 * Formats currency in Rials with Persian digits
 */
export function formatRial(num: number | string | null | undefined): string {
  return `${formatNumberFa(num)} ریال`;
}

/**
 * Formats percentage with Persian digits and safe LTR isolation so + / - / % don't scramble
 */
export function formatPercentFa(num: number | string | null | undefined, decimals = 1, showSign = true): string {
  if (num === null || num === undefined || isNaN(Number(num))) return "\u200E۰.۰٪\u200E";
  const n = typeof num === "number" ? num : parseFloat(num);
  const sign = showSign ? (n > 0 ? "+" : n < 0 ? "-" : "") : "";
  const absFormatted = Math.abs(n).toFixed(decimals);
  return `\u200E${sign}${toPersianDigits(absFormatted)}٪\u200E`;
}

/**
 * Formats R-Multiple with Persian digits (e.g. +۲.۱R or -۱.۰R)
 */
export function formatRFa(num: number | string | null | undefined, decimals = 2): string {
  if (num === null || num === undefined || isNaN(Number(num))) return "\u200E۰.۰۰R\u200E";
  const n = typeof num === "number" ? num : parseFloat(num);
  const sign = n > 0 ? "+" : n < 0 ? "-" : "";
  const absFormatted = Math.abs(n).toFixed(decimals);
  return `\u200E${sign}${toPersianDigits(absFormatted)}R\u200E`;
}

/**
 * Formats multiplier like 1.45x -> ۱.۴۵x with safe bidi
 */
export function formatMultipleFa(num: number | string | null | undefined, decimals = 2): string {
  if (num === null || num === undefined || isNaN(Number(num))) return "\u200E۱.۰۰x\u200E";
  const n = typeof num === "number" ? num : parseFloat(num);
  return `\u200E${toPersianDigits(n.toFixed(decimals))}x\u200E`;
}

/**
 * Formats ratio like 1:2.0 -> ۱ : ۲.۰
 */
export function formatRatioFa(ratio: string | number | null | undefined): string {
  if (!ratio) return "\u200E۱ : ۲.۰\u200E";
  const str = String(ratio);
  return `\u200E${toPersianDigits(str)}\u200E`;
}
