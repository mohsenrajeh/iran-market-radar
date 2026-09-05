const path = require("path");
const { chromium } = require(path.resolve(__dirname, "../apps/web/node_modules/playwright"));
const fs = require("fs");

const BASE_URL = process.env.RADAR_WEB_URL || "http://127.0.0.1:3742";
const SCREENSHOT_DIR = path.resolve(__dirname, "../output/playwright");

function loadLocalCredential(name) {
  if (process.env[name]) return process.env[name];
  const envPath = path.resolve(__dirname, "../.env");
  if (!fs.existsSync(envPath)) return "";
  const line = fs.readFileSync(envPath, "utf8")
    .split(/\r?\n/)
    .find((item) => item.trim().startsWith(`${name}=`));
  if (!line) return "";
  return line.slice(line.indexOf("=") + 1).trim().replace(/^['"]|['"]$/g, "");
}

// Ensure directories exist
if (!fs.existsSync(SCREENSHOT_DIR)) fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });

async function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function normalizeFinancialText(value) {
  const persian = "۰۱۲۳۴۵۶۷۸۹";
  const arabic = "٠١٢٣٤٥٦٧٨٩";
  return value
    .replace(/[۰-۹]/g, (digit) => String(persian.indexOf(digit)))
    .replace(/[٠-٩]/g, (digit) => String(arabic.indexOf(digit)))
    .replace(/[\u200e\u200f\u2066-\u2069,٬]/g, "");
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

  const username = loadLocalCredential("RADAR_ADMIN_USER");
  const password = loadLocalCredential("RADAR_ADMIN_PASSWORD");
  if (!username || !password) {
    throw new Error("RADAR_ADMIN_USER/RADAR_ADMIN_PASSWORD are required in process env or local .env");
  }
  const loginResponse = await context.request.post(`${BASE_URL}/api/v1/auth/login`, {
    data: { username, password },
    headers: { "Content-Type": "application/json" },
  });
  if (!loginResponse.ok()) {
    throw new Error(`Local browser login failed with HTTP ${loginResponse.status()}`);
  }
  const setCookie = loginResponse.headers()["set-cookie"] || "";
  const sessionMatch = setCookie.match(/(?:^|[,;]\s*)radar_session=([^;]+)/);
  if (!sessionMatch) throw new Error("Login response did not issue radar_session cookie");
  await context.addCookies([{
    name: "radar_session",
    value: sessionMatch[1],
    url: BASE_URL,
    httpOnly: true,
    secure: false,
    sameSite: "Strict",
  }]);
  const expectedPortfolioResponse = await context.request.get(`${BASE_URL}/api/v1/paper/portfolio`);
  if (!expectedPortfolioResponse.ok()) {
    throw new Error(`Could not read the persisted paper portfolio: HTTP ${expectedPortfolioResponse.status()}`);
  }
  const expectedPortfolio = await expectedPortfolioResponse.json();
  // Establish one fresh, provider-bound analysis cycle before visual assertions.
  // Otherwise a valid but expired research cache can make the modal test skip
  // even though the same manual refresh later produces signals.
  const preflightSync = await context.request.post(`${BASE_URL}/api/v1/market/sync-all`, {
    timeout: 60000,
  });
  if (![200, 503, 504].includes(preflightSync.status())) {
    throw new Error(`Preflight market sync returned unexpected HTTP ${preflightSync.status()}`);
  }
  const researchResponse = await context.request.get(`${BASE_URL}/api/v1/opportunities?actionable_only=false&min_score=0`);
  const expectedResearchSignals = researchResponse.ok() ? await researchResponse.json() : [];

  console.log("🌐 Navigating to Iran Market Radar...");
  await page.goto(BASE_URL, { waitUntil: "networkidle", timeout: 30000 });
  await sleep(2500);

  const fontChecks = await page.evaluate(async () => {
    await document.fonts.ready;
    return {
      regular: document.fonts.check('16px Vazirmatn'),
      bold: document.fonts.check('700 16px Vazirmatn'),
    };
  });
  if (!fontChecks.regular || !fontChecks.bold) {
    throw new Error(`Vazirmatn browser font check failed: ${JSON.stringify(fontChecks)}`);
  }
  console.log("✅ Vazirmatn regular/bold loaded in Chromium");

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
    await page.screenshot({ path: localPath, fullPage: true });
  }

  // 1. Overview Dashboard
  console.log("📸 Capturing 01_داشبورد_اصلی_نمای_۳۶۰_درجه_بازار.png...");
  await clickTab("overview");
  await saveScreenshot("01_داشبورد_اصلی_نمای_۳۶۰_درجه_بازار.png");

  // 2. Opportunities Radar
  console.log("📸 Capturing 02_دیده_بان_فرصت_های_معاملاتی_و_رادار_کمی.png...");
  await clickTab("opportunities");
  const referenceTab = page.getByTestId("reference-market-tab");
  await referenceTab.waitFor({ state: "visible", timeout: 15000 });
  await referenceTab.click();
  await page.getByTestId("reference-market-row").first().waitFor({ state: "visible", timeout: 15000 });
  const visibleReferenceRows = await page.getByTestId("reference-market-row").count();
  if (visibleReferenceRows < 1) {
    throw new Error("Opportunities view did not render any received market rows");
  }
  await sleep(1000);
  await saveScreenshot("02_دیده_بان_فرصت_های_معاملاتی_و_رادار_کمی.png");

  // 3. Symbol 360 Modal - Chart & Real Coordinate Levels
  console.log("📸 Capturing 03_تحلیل_۳۶۰_درجه_نماد_بخش_اول_چارت_و_سیگنال.png...");
  const firstCard = page.getByRole("button", { name: /مشاهده چارت، کدال و تحلیل ۳۶۰/ }).first();
  if (expectedResearchSignals.length > 0) {
    await firstCard.waitFor({ state: "visible", timeout: 15000 });
    await firstCard.click();
    await page.getByRole("dialog").waitFor({ state: "visible", timeout: 15000 });
    await sleep(1500);
    const localPath3 = path.join(SCREENSHOT_DIR, "03_تحلیل_۳۶۰_درجه_نماد_بخش_اول_چارت_و_سیگنال.png");
    await page.screenshot({ path: localPath3 });

    // 4. Symbol 360 Modal - Tablo & Codal & Strategies
    console.log("📸 Capturing 04_تحلیل_۳۶۰_درجه_نماد_بخش_دوم_تابلو_کدال_استراتژی_ها.png...");
    const modalContent = await page.$("div[style*='overflow-y: auto'], div[style*='overflowY: auto']");
    if (modalContent) {
      await page.evaluate((el) => { if (el) el.scrollTop = el.scrollHeight; }, modalContent);
      await sleep(1500);
    }
    const localPath4 = path.join(SCREENSHOT_DIR, "04_تحلیل_۳۶۰_درجه_نماد_بخش_دوم_تابلو_کدال_استراتژی_ها.png");
    await page.screenshot({ path: localPath4 });

    // Close 360 modal safely
    await page.keyboard.press("Escape");
    await sleep(1000);
  } else {
    for (const staleName of [
      "03_تحلیل_۳۶۰_درجه_نماد_بخش_اول_چارت_و_سیگنال.png",
      "04_تحلیل_۳۶۰_درجه_نماد_بخش_دوم_تابلو_کدال_استراتژی_ها.png",
    ]) {
      const stalePath = path.join(SCREENSHOT_DIR, staleName);
      if (fs.existsSync(stalePath)) fs.rmSync(stalePath);
    }
    console.log("ℹ️ No research signal exists; 360-degree modal capture is explicitly skipped.");
  }

  // 5. Open Positions Desk
  console.log("📸 Capturing 05_میزکار_معاملات_باز_و_پورتفو.png...");
  await clickTab("open_positions");
  const openPosSubTab = await page.$("button:has-text('معاملات باز (')");
  if (openPosSubTab) {
    await openPosSubTab.click();
    await sleep(1500);
  }
  const openPositionsBody = (await page.locator("body").innerText()).replace(/[\u200e\u200f\u2066-\u2069]/g, "");
  const forbiddenDemoMoney = ["۱,۰۴۲,۰۵۰,۰۰۰ تومان", "۳۱۵,۰۰۰,۰۰۰ تومان", "+۱۶,۸۵۰,۰۰۰ تومان"];
  if (forbiddenDemoMoney.some((value) => openPositionsBody.includes(value))) {
    throw new Error("Open positions desk rendered legacy demo money instead of the persisted campaign ledger");
  }
  const navCardText = await page.locator(".kpi-card").filter({ hasText: "ارزش کل دارایی" }).first().innerText();
  const expectedNavTomans = String(Math.round(expectedPortfolio.total_equity / 10));
  if (!openPositionsBody.includes(expectedPortfolio.campaign_id || expectedPortfolio.id)
      || !normalizeFinancialText(navCardText).includes(expectedNavTomans)) {
    throw new Error("Open positions desk did not render the persisted campaign identity and real 10B-toman NAV");
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
  if (firstHistoryRow && await firstHistoryRow.isVisible()) {
    await firstHistoryRow.click();
    await sleep(2500);
    const localPath7 = path.join(SCREENSHOT_DIR, "07_کشوی_جزئیات_معامله_تایم_لاین_و_کالبدشکافی.png");
    await page.screenshot({ path: localPath7 });

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
    await page.waitForFunction(() => {
      const body = document.body.innerText;
      return body.includes("مشاهده در کدال")
        || body.includes("اطلاعیه رسمی کدال یافت نشد")
        || body.includes("دریافت فید کدال ناموفق بود");
    }, null, { timeout: 15000 });
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
  await page.getByTestId("health-source-receipt").first().waitFor({ state: "visible", timeout: 15000 });
  await saveScreenshot("13_پایش_سلامت_خطوط_داده_تفکیک_کارمزد_و_تنظیمات_ریسک.png");

  console.log("📱 Capturing mobile 390x844 overview...");
  await page.setViewportSize({ width: 390, height: 844 });
  await clickTab("overview");
  await saveScreenshot("14_داشبورد_موبایل_390x844.png");

  console.log("📱 Verifying mobile paper portfolio KPIs remain readable...");
  const mobilePortfolioPage = await context.newPage();
  await mobilePortfolioPage.setViewportSize({ width: 390, height: 844 });
  await mobilePortfolioPage.goto(`${BASE_URL}/?audit=open_positions#open_positions`, { waitUntil: "networkidle", timeout: 30000 });
  const mobileKpis = mobilePortfolioPage.getByTestId("open-portfolio-kpi");
  await mobileKpis.first().waitFor({ state: "visible", timeout: 10000 });
  if (await mobileKpis.count() !== 4) {
    const debugState = await mobilePortfolioPage.evaluate(() => ({
      hash: window.location.hash,
      savedTab: localStorage.getItem("radar_active_tab"),
      activeTab: document.querySelector("button[data-tab][style*='rgb(59, 130, 246)']")?.getAttribute("data-tab") || null,
      body: document.body.innerText.slice(0, 800),
    }));
    await mobilePortfolioPage.screenshot({ path: path.join(SCREENSHOT_DIR, "debug_mobile_open_positions.png"), fullPage: true });
    throw new Error(`Mobile open-positions view did not render all four portfolio KPIs: ${JSON.stringify(debugState)}`);
  }
  const mobileKpiBoxes = await mobileKpis.evaluateAll((nodes) => nodes.map((node) => {
    const rect = node.getBoundingClientRect();
    return { width: rect.width, left: rect.left, right: rect.right };
  }));
  if (mobileKpiBoxes.some((box) => box.width < 220 || box.left < 0 || box.right > 390)) {
    throw new Error(`Mobile portfolio KPI cards are compressed or clipped: ${JSON.stringify(mobileKpiBoxes)}`);
  }
  const mobilePortfolioBody = await mobilePortfolioPage.locator("body").innerText();
  if (!mobilePortfolioBody.includes("ارزش کل دارایی") || !normalizeFinancialText(mobilePortfolioBody).includes(String(Math.round(expectedPortfolio.total_equity / 10)))) {
    throw new Error("Mobile open-positions view does not expose the persisted NAV readably");
  }
  await mobilePortfolioPage.screenshot({ path: path.join(SCREENSHOT_DIR, "19_پورتفوی_موبایل_خوانا_390x844.png"), fullPage: true });
  await mobilePortfolioPage.close();
  console.log("✅ Mobile paper portfolio KPIs are readable and remain inside the viewport");

  // 15. The one-provider policy must refresh CDN or fail closed with no fallback.
  console.log("🛡️ Verifying the sole TSETMC CDN provider path...");
  await page.setViewportSize({ width: 1920, height: 1080 });
  const refreshButton = page.getByRole("button", { name: "بروزرسانی دستی" });
  const syncResponsePromise = page.waitForResponse((response) =>
    response.url().includes("/api/v1/market/sync-all")
      && response.request().method() === "POST",
  { timeout: 60000 });
  await refreshButton.click();
  const syncResponse = await syncResponsePromise;
  if (![200, 503, 504].includes(syncResponse.status())) {
    throw new Error(`Manual sync returned unexpected HTTP ${syncResponse.status()}`);
  }
  await clickTab("overview");
  await page.waitForFunction(() => {
    const body = document.body.innerText;
    return body.includes("تلاش مجدد")
      || body.includes("هیچ معامله‌ای در این مرحله اجرا نشد")
      || body.includes("خرید تا تأیید داده رسمی مسدود است")
      || body.includes("داده مستقیم CDN رسمی TSETMC");
  }, null, { timeout: 15000 });
  const syncBody = await page.locator("body").innerText();
  if (syncBody.includes('"detail"') || syncBody.includes("خطای سرور (401)")) {
    throw new Error("Manual sync exposed a raw server/auth error to the operator");
  }
  if (!syncBody.includes("آخرین نتیجه به‌روزرسانی") || !syncBody.includes("نماد جمع شده است")) {
    throw new Error("Manual refresh did not leave a persistent, inspectable provider-progress result");
  }
  await saveScreenshot("15_مسیر_تک_منبع_TSETMC_CDN.png");
  console.log("✅ Manual sync used only TSETMC CDN or failed closed; no hidden fallback/raw 401 exposed");

  console.log("📒 Capturing auditable zero-state paper campaign...");
  await page.goto(`${BASE_URL}/paper-trading`, { waitUntil: "networkidle", timeout: 30000 });
  await sleep(1500);
  const paperBody = await page.locator("body").innerText();
  const bidiSafePaperBody = paperBody.replace(/[\u200e\u200f\u2066-\u2069]/g, "");
  if (!bidiSafePaperBody.includes("معاملات اجراشده در این کمپین") || !/سرمایه درگیر:\s*۰(?:[٫.]۰)?/.test(bidiSafePaperBody)) {
    throw new Error("Paper campaign did not render explicit execution count and zero invested capital");
  }
  await saveScreenshot("16_کمپین_کاغذی_صفر_معامله_و_تفکیک_سرمایه.png");
  console.log("✅ Paper campaign separates initial cash from executed trades and invested capital");

  console.log("📈 Verifying the equity curve starts from the persisted campaign capital...");
  const equityTab = page.getByRole("button", { name: /نمودار رشد سرمایه/ });
  await equityTab.click();
  await sleep(800);
  const openingCapitalText = await page.getByText("سرمایه اولیه:", { exact: true }).locator("..").innerText();
  if (!normalizeFinancialText(openingCapitalText).includes(String(Math.round(expectedPortfolio.initial_cash / 10)))) {
    throw new Error("Equity curve opening capital does not match the persisted campaign initial_cash");
  }
  const openingPoint = page.getByTestId("equity-opening-point");
  if (!(await openingPoint.isVisible())) {
    throw new Error("Equity curve did not render a distinct opening marker for its single persisted snapshot");
  }
  const openingPointLabel = await openingPoint.getAttribute("aria-label");
  if (!normalizeFinancialText(openingPointLabel || "").includes(String(Math.round(expectedPortfolio.initial_cash / 10)))) {
    throw new Error("Equity opening marker does not carry the persisted campaign capital");
  }
  await saveScreenshot("18_نمودار_سرمایه_با_نقطه_افتتاحیه_واقعی.png");
  console.log("✅ Equity curve uses the persisted opening snapshot and campaign capital");

  console.log("🔒 Verifying unauthenticated paper page never fabricates a zero-state campaign...");
  const unauthContext = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: "fa-IR" });
  const unauthPage = await unauthContext.newPage();
  await unauthPage.goto(`${BASE_URL}/paper-trading`, { waitUntil: "networkidle", timeout: 30000 });
  await sleep(1200);
  const unauthBody = await unauthPage.locator("body").innerText();
  if (!unauthBody.includes("وضعیت مالی کمپین تأیید نشده است") || unauthBody.includes("معاملات اجراشده در این کمپین")) {
    throw new Error("Unauthenticated paper page fabricated or exposed campaign financial metrics");
  }
  await unauthPage.screenshot({ path: path.join(SCREENSHOT_DIR, "17_کمپین_بدون_نشست_بدون_عدد_ساختگی.png"), fullPage: true });
  await unauthContext.close();
  console.log("✅ Unauthenticated API failures render an unverified state with no fabricated metrics");

  console.log(`🎉 All visual screenshots captured successfully in: ${SCREENSHOT_DIR}`);
  await browser.close();

}

runCapture().catch((err) => {
  console.error("Fatal capture error:", err);
  process.exit(1);
});
