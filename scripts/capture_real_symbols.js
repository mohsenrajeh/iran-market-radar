const { chromium } = require("d:/My Project/04_Trading-AI/iran-market-radar/apps/web/node_modules/playwright");

async function capture() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  
  // 1. Overview dashboard
  await page.goto("http://127.0.0.1:3742", { waitUntil: "networkidle" });
  await page.waitForTimeout(1500);
  await page.screenshot({ path: "screenshots/01_dashboard_real_prices.png" });

  // 2. Open Shavan Modal
  const searchInput = page.locator("input[placeholder*='جستجو و تحلیل']").first();
  if (await searchInput.isVisible()) {
    await searchInput.fill("شاوان");
    await page.waitForTimeout(600);
    const item = page.locator("div:has-text('پالایش نفت لاوان')").last();
    if (await item.isVisible()) {
      await item.click();
    } else {
      await page.keyboard.press("Enter");
    }
    await page.waitForTimeout(2000);
    await page.screenshot({ path: "screenshots/03_shavan_modal_real.png" });
  }

  // 3. Open Nouri Modal
  await page.goto("http://127.0.0.1:3742", { waitUntil: "networkidle" });
  await page.waitForTimeout(1000);
  const searchInput2 = page.locator("input[placeholder*='جستجو و تحلیل']").first();
  if (await searchInput2.isVisible()) {
    await searchInput2.fill("نوری");
    await page.waitForTimeout(600);
    const item2 = page.locator("div:has-text('پتروشیمی نوری')").last();
    if (await item2.isVisible()) {
      await item2.click();
    } else {
      await page.keyboard.press("Enter");
    }
    await page.waitForTimeout(2000);
    await page.screenshot({ path: "screenshots/03_nouri_modal_real.png" });
  }

  console.log("Captured real prices screenshots successfully!");
  await browser.close();
}

capture().catch(console.error);
