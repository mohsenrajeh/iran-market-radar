"""Capture 360 modal screenshot with direct symbol click."""
import asyncio
import sys
from pathlib import Path
from playwright.async_api import async_playwright

OUTPUT_DIR = Path(r"C:\Users\byet\.gemini\antigravity\brain\5f9a2824-c4f0-4734-9d38-1958cb440da1\screenshots")

async def capture_modal():
    sys.stdout.reconfigure(encoding='utf-8')
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1600, "height": 1000}, device_scale_factor=2)
        page = await context.new_page()
        await page.goto("http://127.0.0.1:3000", wait_until="domcontentloaded", timeout=15000)
        await asyncio.sleep(3)

        # Login if modal exists
        login_btn = page.locator("button:has-text('ورود امن به سامانه')")
        if await login_btn.count() > 0:
            await login_btn.click()
            await asyncio.sleep(2)

        # Go to open positions or opportunities and click on symbol detail
        opp_btn = page.locator("aside button:has-text('دیده‌بان')").first
        if await opp_btn.count() > 0:
            await opp_btn.click()
            await asyncio.sleep(2)

        # Click the first card
        first_card = page.locator("div[style*='cursor: pointer']").first
        if await first_card.count() > 0:
            await first_card.click()
            await asyncio.sleep(3)
            await page.screenshot(path=str(OUTPUT_DIR / "07_unified_symbol_360_modal.png"))
            print("Modal captured successfully.")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(capture_modal())
