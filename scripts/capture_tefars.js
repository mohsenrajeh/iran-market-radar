const path = require("path");
const { chromium } = require("d:/My Project/04_Trading-AI/iran-market-radar/apps/web/node_modules/playwright");

async function capture() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  await page.goto("http://127.0.0.1:3742", { waitUntil: "networkidle" });
  await page.waitForTimeout(1000);

  // Search for Tefars in the header search input
  const searchInput = page.locator("input[placeholder*='جستجو و تحلیل']").first();
  if (await searchInput.isVisible()) {
    await searchInput.fill("ثفارس");
    await page.waitForTimeout(600);
    // Click the search dropdown result item
    const item = page.locator("div:has-text('عمران و مسکن سازان فارس')").last();
    if (await item.isVisible()) {
      await item.click();
    } else {
      await page.keyboard.press("Enter");
    }
    await page.waitForTimeout(2000);
  }

  const outPath = "d:/My Project/04_Trading-AI/iran-market-radar/screenshots/03_tefars_modal_fixed.png";
  await page.screenshot({ path: outPath });
  console.log("Saved Tefars modal fixed screenshot to " + outPath);
  await browser.close();
}

capture().catch(console.error);
