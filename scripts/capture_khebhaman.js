const { chromium } = require("d:/My Project/04_Trading-AI/iran-market-radar/apps/web/node_modules/playwright");

async function capture() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  
  await page.goto("http://127.0.0.1:3742", { waitUntil: "networkidle" });
  await page.waitForTimeout(1000);

  const searchInput = page.locator("input[placeholder*='جستجو و تحلیل']").first();
  if (await searchInput.isVisible()) {
    await searchInput.fill("خبهمن");
    await page.waitForTimeout(600);
    const item = page.locator("div:has-text('گروه بهمن')").last();
    if (await item.isVisible()) {
      await item.click();
    } else {
      await page.keyboard.press("Enter");
    }
    await page.waitForTimeout(2000);
    await page.screenshot({ path: "screenshots/03_khebhaman_modal_real.png" });
  }

  console.log("Captured Khebhaman modal successfully!");
  await browser.close();
}

capture().catch(console.error);
