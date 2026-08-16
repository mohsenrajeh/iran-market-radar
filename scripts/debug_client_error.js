const path = require("path");
const { chromium } = require(path.resolve(__dirname, "../apps/web/node_modules/playwright"));

(async () => {
  const browser = await chromium.launch({
    headless: true,
    args: ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
  });
  const page = await browser.newPage();
  
  page.on('console', msg => console.log('BROWSER CONSOLE:', msg.type(), msg.text()));
  page.on('pageerror', err => console.log('BROWSER PAGEERROR:', err.message, '\nSTACK:\n', err.stack));

  console.log('Navigating to http://127.0.0.1:3742/ ...');
  await page.goto('http://127.0.0.1:3742/', { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);

  console.log('Clicking Open Positions sidebar button...');
  const openPosBtn = await page.$('button:has-text("معاملات باز")');
  if (openPosBtn) {
    await openPosBtn.click();
    await page.waitForTimeout(1000);
  }

  console.log('Clicking Closed Trade History subtab button...');
  const historyBtn = await page.$('button:has-text("تاریخچه کامل معاملات")');
  if (historyBtn) {
    console.log('Found history button, clicking...');
    await historyBtn.click();
    await page.waitForTimeout(2000);
  } else {
    console.log('History button NOT found! Listing all button texts:');
    const buttons = await page.$$eval('button', btns => btns.map(b => b.innerText));
    console.log(buttons);
  }
  
  await page.screenshot({ path: path.resolve(__dirname, '../debug_screenshot.png'), fullPage: true });
  console.log('Debug screenshot saved.');
  await browser.close();
})();
