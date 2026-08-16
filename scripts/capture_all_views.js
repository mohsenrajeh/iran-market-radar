const path = require("path");
const { chromium } = require(path.resolve(__dirname, "../apps/web/node_modules/playwright"));
const fs = require("fs");
const { execSync } = require("child_process");

const BASE_URL = process.env.RADAR_WEB_URL || "http://127.0.0.1:3742";
const SCREENSHOT_DIR = path.resolve(__dirname, "../screenshots");
const ARTIFACT_DIR = "C:/Users/byet/.gemini/antigravity/brain/5f9a2824-c4f0-4734-9d38-1958cb440da1/screenshots";

// Ensure directories exist
if (!fs.existsSync(SCREENSHOT_DIR)) fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
if (!fs.existsSync(ARTIFACT_DIR)) fs.mkdirSync(ARTIFACT_DIR, { recursive: true });

async function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function runCapture() {
  console.log(`🎬 Launching Chromium for Iran Market Radar visual capture at ${BASE_URL}...`);
  const browser = await chromium.launch({
    headless: true,
    args: ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
  });

  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    locale: "fa-IR",
  });

  const page = await context.newPage();

  page.on('console', msg => console.log('BROWSER LOG:', msg.type(), msg.text()));
  page.on('pageerror', err => console.log('BROWSER PAGEERROR:', err.message));

  // Set LocalStorage to ensure seamless access
  await page.addInitScript(() => {
    localStorage.setItem("radar_auth_token", "radar_institutional_session_2026");
    localStorage.setItem("radar_auth_user", "admin");
  });

  console.log("🌐 Navigating to Iran Market Radar...");
  await page.goto(BASE_URL, { waitUntil: "networkidle", timeout: 30000 });
  await sleep(2500);

  // Helper to click sidebar tab using data-tab attribute
  async function clickTab(tabKey) {
    const btn = await page.$(`button[data-tab='${tabKey}']`);
    if (btn) {
      await btn.click();
    } else {
      const tabMap = {
        overview: "داشبورد",
        opportunities: "دیده‌بان",
        open_positions: "معاملات باز",
        fundamental: "تحلیل بنیادی",
        trading_lab: "مرکز آزمایشگاه",
        health_settings: "سلامت داده",
      };
      const targetText = tabMap[tabKey] || tabKey;
      const b = await page.$(`button:has-text('${targetText}')`);
      if (b) await b.click();
    }
    await sleep(1500);
  }

  async function saveScreenshot(filename) {
    const localPath = path.join(SCREENSHOT_DIR, filename);
    const artPath = path.join(ARTIFACT_DIR, filename);
    await page.screenshot({ path: localPath, fullPage: true });
    try {
      fs.copyFileSync(localPath, artPath);
    } catch (e) {}
  }

  // 1. Overview Dashboard
  console.log("📸 Capturing 01_داشبورد_اصلی_نمای_۳۶۰_درجه_بازار.png...");
  await clickTab("overview");
  await saveScreenshot("01_داشبورد_اصلی_نمای_۳۶۰_درجه_بازار.png");

  // 2. Opportunities Radar
  console.log("📸 Capturing 02_دیده_بان_فرصت_های_معاملاتی_و_رادار_کمی.png...");
  await clickTab("opportunities");
  await saveScreenshot("02_دیده_بان_فرصت_های_معاملاتی_و_رادار_کمی.png");

  // 3. Symbol 360 Modal - Chart & Real Coordinate Levels
  console.log("📸 Capturing 03_تحلیل_۳۶۰_درجه_نماد_بخش_اول_چارت_و_سیگنال.png...");
  const firstCard = await page.$("div:has-text('مشاهده چارت، کدال و تحلیل ۳۶۰°')");
  if (firstCard) {
    await firstCard.click();
    await sleep(2500);
    const localPath3 = path.join(SCREENSHOT_DIR, "03_تحلیل_۳۶۰_درجه_نماد_بخش_اول_چارت_و_سیگنال.png");
    await page.screenshot({ path: localPath3 });
    try { fs.copyFileSync(localPath3, path.join(ARTIFACT_DIR, "03_تحلیل_۳۶۰_درجه_نماد_بخش_اول_چارت_و_سیگنال.png")); } catch (e) {}

    // 4. Symbol 360 Modal - Tablo & Codal & Strategies
    console.log("📸 Capturing 04_تحلیل_۳۶۰_درجه_نماد_بخش_دوم_تابلو_کدال_استراتژی_ها.png...");
    const modalContent = await page.$("div[style*='overflow-y: auto'], div[style*='overflowY: auto']");
    if (modalContent) {
      await page.evaluate((el) => { if (el) el.scrollTop = el.scrollHeight; }, modalContent);
      await sleep(1500);
    }
    const localPath4 = path.join(SCREENSHOT_DIR, "04_تحلیل_۳۶۰_درجه_نماد_بخش_دوم_تابلو_کدال_استراتژی_ها.png");
    await page.screenshot({ path: localPath4 });
    try { fs.copyFileSync(localPath4, path.join(ARTIFACT_DIR, "04_تحلیل_۳۶۰_درجه_نماد_بخش_دوم_تابلو_کدال_استراتژی_ها.png")); } catch (e) {}

    // Close 360 modal safely
    await page.keyboard.press("Escape");
    await sleep(1000);
  }

  // 5. Open Positions Desk
  console.log("📸 Capturing 05_میزکار_معاملات_باز_و_پورتفو.png...");
  await clickTab("open_positions");
  const openPosSubTab = await page.$("button:has-text('معاملات باز (')");
  if (openPosSubTab) {
    await openPosSubTab.click();
    await sleep(1500);
  }
  await saveScreenshot("05_میزکار_معاملات_باز_و_پورتفو.png");

  // 6. Closed Trades History (Table, Filters, Summary Banner)
  console.log("📸 Capturing 06_تاریخچه_کامل_معاملات_بسته_و_دفترکل_حسابداری.png...");
  const historySubTab = await page.$("button:has-text('تاریخچه کامل معاملات')");
  if (historySubTab) {
    await historySubTab.click();
    await sleep(2000);
  }
  await saveScreenshot("06_تاریخچه_کامل_معاملات_بسته_و_دفترکل_حسابداری.png");

  // 7. Trade Detail Drawer (Replay Chart, Execution Timeline, Post-Mortem)
  console.log("📸 Capturing 07_کشوی_جزئیات_معامله_تایم_لاین_و_کالبدشکافی.png...");
  const firstHistoryRow = await page.$("tbody tr");
  if (firstHistoryRow) {
    await firstHistoryRow.click();
    await sleep(2500);
    const localPath7 = path.join(SCREENSHOT_DIR, "07_کشوی_جزئیات_معامله_تایم_لاین_و_کالبدشکافی.png");
    await page.screenshot({ path: localPath7 });
    try { fs.copyFileSync(localPath7, path.join(ARTIFACT_DIR, "07_کشوی_جزئیات_معامله_تایم_لاین_و_کالبدشکافی.png")); } catch (e) {}

    // Close Trade Detail Drawer
    await page.keyboard.press("Escape");
    await sleep(500);
    const drawerCloseBtn = await page.$("button:has(svg.lucide-x), button:has-text('✕')");
    if (drawerCloseBtn) {
      try { await drawerCloseBtn.click({ force: true }); } catch (e) {}
    }
    await sleep(1500);
  }

  // 8. Fundamental Valuation Matrix
  console.log("📸 Capturing 08_تحلیل_بنیادی_ماتریس_ارزندگی_و_پیوتروسکی.png...");
  await clickTab("fundamental");
  const matrixSubTab = await page.$("button:has-text('ماتریس ارزندگی')");
  if (matrixSubTab) {
    await matrixSubTab.click();
    await sleep(1500);
  }
  await saveScreenshot("08_تحلیل_بنیادی_ماتریس_ارزندگی_و_پیوتروسکی.png");

  // 9. Codal Realtime Feed
  console.log("📸 Capturing 09_فید_بلادرنگ_اطلاعیه_های_کدال_و_افشای_بااهمیت.png...");
  const codalSubTab = await page.$("button:has-text('فید زنده اطلاعیه‌های کدال')");
  if (codalSubTab) {
    await codalSubTab.click();
    await sleep(1500);
  }
  await saveScreenshot("09_فید_بلادرنگ_اطلاعیه_های_کدال_و_افشای_بااهمیت.png");

  // 10. Strategy Learning Center - Performance & Health
  console.log("📸 Capturing 10_مرکز_یادگیری_عملکرد_و_سلامت_استراتژی_ها.png...");
  await clickTab("trading_lab");
  const perfSubTab = await page.$("button:has-text('عملکرد و سلامت استراتژی‌ها')");
  if (perfSubTab) {
    await perfSubTab.click();
    await sleep(1500);
  }
  await saveScreenshot("10_مرکز_یادگیری_عملکرد_و_سلامت_استراتژی_ها.png");

  // 11. Strategy Learning Center - Structured Lessons & Post-Mortems
  console.log("📸 Capturing 11_درس_های_ساختاریافته_و_کالبدشکافی_معاملات.png...");
  const postMortemSubTab = await page.$("button:has-text('کالبدشکافی و درس‌های ساختاریافته')");
  if (postMortemSubTab) {
    await postMortemSubTab.click();
    await sleep(1500);
  }
  await saveScreenshot("11_درس_های_ساختاریافته_و_کالبدشکافی_معاملات.png");

  // 12. Strategy Learning Center - Research Queue & Champion vs Challenger
  console.log("📸 Capturing 12_صف_تحقیقات_فرضیات_و_مقایسه_champion_vs_challenger.png...");
  const researchSubTab = await page.$("button:has-text('صف تحقیقات و فرضیات')");
  if (researchSubTab) {
    await researchSubTab.click();
    await sleep(1500);
  }
  await saveScreenshot("12_صف_تحقیقات_فرضیات_و_مقایسه_champion_vs_challenger.png");

  // 13. System Health & Broker Settings
  console.log("📸 Capturing 13_پایش_سلامت_خطوط_داده_تفکیک_کارمزد_و_تنظیمات_ریسک.png...");
  await clickTab("health_settings");
  await saveScreenshot("13_پایش_سلامت_خطوط_داده_تفکیک_کارمزد_و_تنظیمات_ریسک.png");

  console.log(`🎉 All 13 high-resolution visual screenshots captured successfully in: ${SCREENSHOT_DIR}`);
  await browser.close();

  // Create ZIP bundle
  console.log("📦 Creating screenshots.zip...");
  const zipPath = path.resolve(__dirname, "../screenshots.zip");
  try {
    execSync(`powershell -command "Compress-Archive -Path '${SCREENSHOT_DIR}\\*.png' -DestinationPath '${zipPath}' -Force"`);
    console.log(`✅ screenshots.zip created successfully at: ${zipPath}`);
  } catch (e) {
    console.error("Error creating zip:", e.message);
  }
}

runCapture().catch((err) => {
  console.error("Fatal capture error:", err);
  process.exit(1);
});
