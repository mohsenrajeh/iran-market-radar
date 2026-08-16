const path = require("path");
const { chromium } = require(path.resolve(__dirname, "../apps/web/node_modules/playwright"));

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  console.log("Navigating directly to http://127.0.0.1:3742/#opportunities...");
  await page.goto("http://127.0.0.1:3742/#opportunities", { waitUntil: "networkidle" });
  await page.waitForTimeout(2000);
  const cards = await page.$$("div:has-text('مشاهده چارت، کدال و تحلیل ۳۶۰°')");
  console.log("Opportunities cards count after direct load/refresh:", cards.length);
  await page.screenshot({ path: path.resolve(__dirname, "../screenshots/verify_opportunities_refresh.png"), fullPage: true });
  await browser.close();
  console.log("Verification screenshot saved successfully!");
})();
