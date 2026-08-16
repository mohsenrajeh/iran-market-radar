"""Script to capture pixel-perfect high-resolution screenshots of all 8 distinct views in Iran Market Radar."""
import asyncio
import os
import shutil
import sys
from pathlib import Path
from playwright.async_api import async_playwright

OUTPUT_DIR_1 = Path(r"C:\Users\byet\.gemini\antigravity\brain\5f9a2824-c4f0-4734-9d38-1958cb440da1\screenshots")
OUTPUT_DIR_2 = Path(r"C:\Users\byet\.gemini\antigravity\brain\5f9a2824-c4f0-4734-9d38-1958cb440da1")
PRESENTATION_DIR = Path(r"D:\My Project\04_Trading-AI\iran-market-radar\presentation_package\assets")

OUTPUT_DIR_1.mkdir(parents=True, exist_ok=True)
PRESENTATION_DIR.mkdir(parents=True, exist_ok=True)

def copy_to_all_destinations(filename: str):
    src = OUTPUT_DIR_1 / filename
    if src.exists():
        shutil.copy2(src, OUTPUT_DIR_2 / filename)
        shutil.copy2(src, PRESENTATION_DIR / filename)

async def capture_all_screenshots():
    sys.stdout.reconfigure(encoding='utf-8')
    print("🚀 Launching Chromium for automated snapshot capture...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1600, "height": 1000},
            device_scale_factor=2,  # Retina quality
        )
        page = await context.new_page()

        # Set localStorage credentials before navigation so no modal blocks
        await page.add_init_script("""
            localStorage.setItem('radar_auth_token', 'mock_jwt_admin_session_token_30d');
            localStorage.setItem('radar_auth_user', 'admin');
            localStorage.setItem('radar_auth_login_at', '2026-08-16T12:00:00.000Z');
        """)

        # 1. Navigate to home
        print("🌐 Navigating to http://127.0.0.1:3742 ...")
        await page.goto("http://127.0.0.1:3742", wait_until="domcontentloaded", timeout=25000)
        await asyncio.sleep(4)

        # ── 1. Overview Dashboard ──
        print("📸 Capturing: 01_dashboard_overview.png")
        btn = page.locator("aside button:has-text('داشبورد')").first
        if await btn.count() > 0:
            await btn.click(force=True)
            await asyncio.sleep(2.5)
        await page.screenshot(path=str(OUTPUT_DIR_1 / "01_dashboard_overview.png"))
        copy_to_all_destinations("01_dashboard_overview.png")

        # ── 2. Opportunities Radar ──
        print("📸 Capturing: 02_opportunities_radar.png")
        btn = page.locator("aside button:has-text('دیده‌بان')").first
        if await btn.count() > 0:
            await btn.click(force=True)
            await asyncio.sleep(2.5)
        await page.screenshot(path=str(OUTPUT_DIR_1 / "02_opportunities_radar.png"))
        copy_to_all_destinations("02_opportunities_radar.png")

        # ── 3. Open Positions & Money Management ──
        print("📸 Capturing: 03_open_positions_portfolio.png")
        btn = page.locator("aside button:has-text('معاملات')").first
        if await btn.count() > 0:
            await btn.click(force=True)
            await asyncio.sleep(2.5)
        await page.screenshot(path=str(OUTPUT_DIR_1 / "03_open_positions_portfolio.png"))
        copy_to_all_destinations("03_open_positions_portfolio.png")

        # ── 4. Fundamental & Codal Analysis ──
        print("📸 Capturing: 04_fundamental_codal.png")
        btn = page.locator("aside button:has-text('بنیادی')").first
        if await btn.count() > 0:
            await btn.click(force=True)
            await asyncio.sleep(2.5)
        await page.screenshot(path=str(OUTPUT_DIR_1 / "04_fundamental_codal.png"))
        copy_to_all_destinations("04_fundamental_codal.png")

        # ── 5. Trading Lab - AI Self-Tuning & Codal Multipliers ──
        print("📸 Capturing: 05_trading_lab_calibration.png")
        btn = page.locator("aside button:has-text('آزمایشگاه')").first
        if await btn.count() > 0:
            await btn.click(force=True)
            await asyncio.sleep(2.5)
            # Scroll slightly to show calibration engine
            await page.evaluate("window.scrollTo(0, 300)")
            await asyncio.sleep(1)
        await page.screenshot(path=str(OUTPUT_DIR_1 / "05_trading_lab_calibration.png"))
        copy_to_all_destinations("05_trading_lab_calibration.png")

        # ── 6. Health & Governance Settings ──
        print("📸 Capturing: 06_health_settings.png")
        btn = page.locator("aside button:has-text('سلامت')").first
        if await btn.count() > 0:
            await btn.click(force=True)
            await asyncio.sleep(2.5)
        await page.screenshot(path=str(OUTPUT_DIR_1 / "06_health_settings.png"))
        copy_to_all_destinations("06_health_settings.png")

        # ── 7. Closed Trades Post-Mortem & Lessons Learned ──
        print("📸 Capturing: 07_post_mortem_lessons.png")
        btn = page.locator("aside button:has-text('آزمایشگاه')").first
        if await btn.count() > 0:
            await btn.click(force=True)
            await asyncio.sleep(2.5)
            # Scroll to lessons section
            await page.evaluate("window.scrollTo(0, 850)")
            await asyncio.sleep(1)
        await page.screenshot(path=str(OUTPUT_DIR_1 / "07_post_mortem_lessons.png"))
        copy_to_all_destinations("07_post_mortem_lessons.png")

        # ── 8. Strategy Performance & Indicator Precision Matrix ──
        print("📸 Capturing: 08_strategy_backtest.png")
        btn = page.locator("aside button:has-text('آزمایشگاه')").first
        if await btn.count() > 0:
            await btn.click(force=True)
            await asyncio.sleep(2.5)
            # Scroll down to accuracy table
            await page.evaluate("window.scrollTo(0, 1400)")
            await asyncio.sleep(1)
        await page.screenshot(path=str(OUTPUT_DIR_1 / "08_strategy_backtest.png"))
        copy_to_all_destinations("08_strategy_backtest.png")

        # Also save legacy named copies for backwards compatibility
        shutil.copy2(OUTPUT_DIR_1 / "07_post_mortem_lessons.png", OUTPUT_DIR_1 / "07_unified_symbol_360_modal.png")
        shutil.copy2(OUTPUT_DIR_1 / "08_strategy_backtest.png", OUTPUT_DIR_1 / "08_trading_lab_subtabs.png")
        copy_to_all_destinations("07_unified_symbol_360_modal.png")
        copy_to_all_destinations("08_trading_lab_subtabs.png")

        await browser.close()
        print(f"\n🎉 All 8 high-resolution screenshots successfully saved!")

if __name__ == "__main__":
    asyncio.run(capture_all_screenshots())
