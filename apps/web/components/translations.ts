/**
 * دیکشنری جامع ترجمه‌ها و اصطلاحات تخصصی مالی به فارسی روان و حرفه‌ای
 */

export const STRATEGY_NAMES_FA: Record<string, string> = {
  cross_sectional_momentum: "مومنتوم مقطعی (پیشتاز بازار)",
  time_series_trend: "روند میانگین‌های متحرک (EMA)",
  breakout_volume: "شکست سقف قیمتی با حجم سنگین",
  trend_pullback: "پولبک معتبر در روند صعودی",
  selective_mean_reversion: "بازگشت از اشباع فروش (RSI)",
  volume_anomaly: "حجم مشکوک و غیرعادی",
  client_flow: "انباشت پول حقیقی و هوشمند",
  ichimoku_cloud_trend: "ایچیموکو (روند بالای ابر کومو)",
  sector_rotation: "چرخش نقدینگی به سمت صنعت",
  bb_squeeze_breakout: "فشردگی بولینگر (انفجار نوسان)",
  multi_indicator_confluence: "همگرایی و تأیید چند اندیکاتوری",
  smart_money_divergence: "واگرایی مثبت پول هوشمند",
};

export const STRATEGY_SHORT_NAMES_FA: Record<string, string> = {
  cross_sectional_momentum: "مومنتوم",
  time_series_trend: "روند EMA",
  breakout_volume: "شکست حجم",
  trend_pullback: "پولبک روند",
  selective_mean_reversion: "بازگشت میانگین",
  volume_anomaly: "حجم مشکوک",
  client_flow: "پول حقیقی",
  ichimoku_cloud_trend: "ایچیموکو",
  sector_rotation: "چرخش صنعت",
  bb_squeeze_breakout: "فشردگی بولینگر",
  multi_indicator_confluence: "تأیید چندگانه",
  smart_money_divergence: "واگرایی هوشمند",
};

export const INDICATOR_NAMES_FA: Record<string, string> = {
  ema_trend: "روند میانگین‌های متحرک نمایی (EMA)",
  rsi_14: "شاخص قدرت نسبی (RSI)",
  macd_hist: "هیستوگرام مکدی (MACD)",
  supertrend: "سوپرترند (Supertrend)",
  ichimoku_cloud: "ابر کومو ایچیموکو",
  adx_14: "قدرت روند (ADX)",
  mfi_14: "شاخص جریان نقدینگی (MFI)",
  obv_slope: "شیب حجم تعادلی (OBV)",
  cmf_20: "جریان پول چایکین (CMF)",
  volume_z: "امتیاز حجم غیرعادی (Z-Score)",
  bb_squeeze: "فشردگی باندهای بولینگر",
  client_flow: "قدرت خریدار حقیقی / سرانه",
  stoch_rsi: "RSI تصادفی (Stochastic RSI)",
  williams_r: "شاخص ویلیامز (%R)",
  cci_20: "شاخص کانال کالا (CCI)",
};

export const MARKET_REGIME_FA: Record<string, string> = {
  risk_on: "رونق و تقاضای پرقدرت (ریسک‌پذیر)",
  neutral: "خنثی و تعادلی",
  risk_off: "اصلاحی و کم‌ریسک (ریسک‌گریز)",
  distribution: "مشکوک به توزیع و پرریسک",
};

export const EXIT_REASON_FA: Record<string, string> = {
  stop_hit: "فعال شدن حد ضرر",
  target_hit: "رسیدن به هدف قیمتی (سود)",
  time_stop: "اتمام زمان مجاز نگهداری (چرخش سرمایه)",
  manual: "خروج دستی توسط کاربر",
  open: "معامله باز و فعال",
};

export function getStrategyFa(key: string): string {
  return STRATEGY_NAMES_FA[key] || key;
}

export function getStrategyShortFa(key: string): string {
  return STRATEGY_SHORT_NAMES_FA[key] || key;
}

export function getIndicatorFa(key: string): string {
  return INDICATOR_NAMES_FA[key] || key;
}

export function getRegimeFa(key: string): string {
  return MARKET_REGIME_FA[key] || key;
}

export function getExitReasonFa(key: string): string {
  return EXIT_REASON_FA[key] || key;
}
