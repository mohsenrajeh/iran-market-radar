"""Automated ultra-high resolution snapshot engine for Iran Market Radar.
Captures full-screen pages and step-by-step scrolled detail modal views.
"""
import asyncio
import os
import sys
from pathlib import Path
from playwright.async_api import async_playwright

sys.stdout.reconfigure(encoding='utf-8')

OUTPUT_DIR = Path(r"D:\My Project\04_Trading-AI\iran-market-radar\screenshots")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

async def capture_everything():
    print(f"🚀 Starting Playwright snapshot engine...")
    print(f"📁 Target output directory: {OUTPUT_DIR}\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1600, "height": 1050},
            device_scale_factor=2,  # Retina high-definition
        )
        page = await context.new_page()

        # Inject authentication session
        await page.add_init_script("""
            localStorage.setItem('radar_auth_token', 'mock_jwt_admin_session_token_30d');
            localStorage.setItem('radar_auth_user', 'admin');
            localStorage.setItem('radar_auth_login_at', '2026-08-16T12:00:00.000Z');
        """)

        # 1. Navigate to application
        print("🌐 Connecting to http://127.0.0.1:3742 ...")
        await page.goto("http://127.0.0.1:3742", wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(4)

        # ── 1. Dashboard Overview ──
        print("📸 [01/13] Capturing: 01_داشبورد_اصلی_نمای_۳۶۰_درجه_بازار.png")
        btn = page.locator("aside button:has-text('داشبورد')").first
        if await btn.count() > 0:
            await btn.click(force=True)
            await asyncio.sleep(2.5)
        await page.screenshot(path=str(OUTPUT_DIR / "01_داشبورد_اصلی_نمای_۳۶۰_درجه_بازار.png"))

        # ── 2. Opportunities Radar ──
        print("📸 [02/13] Capturing: 02_دیده_بان_فرصت_های_معاملاتی_و_رادار_کمی.png")
        btn = page.locator("aside button:has-text('دیده‌بان')").first
        if await btn.count() > 0:
            await btn.click(force=True)
            await asyncio.sleep(2.5)
        await page.screenshot(path=str(OUTPUT_DIR / "02_دیده_بان_فرصت_های_معاملاتی_و_رادار_کمی.png"))

        # ── 3. Symbol 360 Analysis - Top Part (Chart & Signal) ──
        print("📸 [03/13] Capturing: 03_تحلیل_۳۶۰_درجه_نماد_بخش_اول_چارت_و_سیگنال.png")
        # Click on any opportunity card in the radar
        symbol_target = page.locator("div:has-text('مشاهده تحلیل و خرید')").first
        if await symbol_target.count() == 0:
            symbol_target = page.locator("div[style*='cursor: pointer'], div[style*='cursor:pointer']").first
        
        await symbol_target.click(force=True)
        await asyncio.sleep(3.5)

        # Take screenshot of Modal Top (Chart, Levels, Tags, Power Meters)
        await page.screenshot(path=str(OUTPUT_DIR / "03_تحلیل_۳۶۰_درجه_نماد_بخش_اول_چارت_و_سیگنال.png"))

        # ── 4. Symbol 360 Analysis - Bottom Part (Tablo, Codal, 12 Strategies) ──
        print("📸 [04/13] Capturing: 04_تحلیل_۳۶۰_درجه_نماد_بخش_دوم_تابلو_کدال_استراتژی_ها.png")
        # Scroll down inside modal
        await page.evaluate("""() => {
            const scrollContainers = document.querySelectorAll('div');
            for (const el of scrollContainers) {
                if (el.scrollHeight > el.clientHeight && el.clientHeight > 300) {
                    el.scrollTop = el.scrollHeight;
                }
            }
        }""")
        await asyncio.sleep(2)
        await page.screenshot(path=str(OUTPUT_DIR / "04_تحلیل_۳۶۰_درجه_نماد_بخش_دوم_تابلو_کدال_استراتژی_ها.png"))

        # Close modal
        await page.keyboard.press("Escape")
        await asyncio.sleep(1.5)

        # ── 5. Open Positions & Cash Ledger ──
        print("📸 [05/13] Capturing: 05_میزکار_معاملات_باز_دفترکل_نقدینگی_و_پورتفو.png")
        btn = page.locator("aside button:has-text('معاملات')").first
        if await btn.count() > 0:
            await btn.click(force=True)
            await asyncio.sleep(2.5)
        await page.screenshot(path=str(OUTPUT_DIR / "05_میزکار_معاملات_باز_دفترکل_نقدینگی_و_پورتفو.png"))

        # ── 6. Fundamental & Piotroski Matrix ──
        print("📸 [06/13] Capturing: 06_تحلیل_بنیادی_ماتریس_ارزندگی_و_پیوتروسکی.png")
        btn = page.locator("aside button:has-text('بنیادی')").first
        if await btn.count() > 0:
            await btn.click(force=True)
            await asyncio.sleep(2.5)
        # Ensure first subtab (Valuation Matrix) is active
        mat_tab = page.locator("button:has-text('ماتریس ارزندگی')").first
        if await mat_tab.count() > 0:
            await mat_tab.click(force=True)
            await asyncio.sleep(1.5)
        await page.screenshot(path=str(OUTPUT_DIR / "06_تحلیل_بنیادی_ماتریس_ارزندگی_و_پیوتروسکی.png"))

        # ── 7. Codal Live Feed ──
        print("📸 [07/13] Capturing: 07_فید_بلادرنگ_اطلاعیه_های_کدال_و_افشای_بااهمیت.png")
        codal_tab = page.locator("button:has-text('کدال'), button:has-text('اطلاعیه‌ها')").first
        if await codal_tab.count() > 0:
            await codal_tab.click(force=True)
            await asyncio.sleep(2)
        await page.screenshot(path=str(OUTPUT_DIR / "07_فید_بلادرنگ_اطلاعیه_های_کدال_و_افشای_بااهمیت.png"))

        # ── 8. AI Calibration & Learning Hub ──
        print("📸 [08/13] Capturing: 08_مرکز_کالیبراسیون_هوش_مصنوعی_و_شاخص_brier.png")
        btn = page.locator("aside button:has-text('آزمایشگاه')").first
        if await btn.count() > 0:
            await btn.click(force=True)
            await asyncio.sleep(2.5)
        calib_tab = page.locator("button:has-text('کالیبراسیون'), button:has-text('مرکز یادگیری')").first
        if await calib_tab.count() > 0:
            await calib_tab.click(force=True)
            await asyncio.sleep(2)
        await page.screenshot(path=str(OUTPUT_DIR / "08_مرکز_کالیبراسیون_هوش_مصنوعی_و_شاخص_brier.png"))

        # ── 9. Paper Trading Portfolio ──
        print("📸 [09/13] Capturing: 09_پورتفوی_معاملات_آزمایشی_پیپر_تریدینگ.png")
        paper_tab = page.locator("button:has-text('معاملات آزمایشی'), button:has-text('Paper Trading')").first
        if await paper_tab.count() > 0:
            await paper_tab.click(force=True)
            await asyncio.sleep(2)
        await page.screenshot(path=str(OUTPUT_DIR / "09_پورتفوی_معاملات_آزمایشی_پیپر_تریدینگ.png"))

        # ── 10. Backtest Lab ──
        print("📸 [10/13] Capturing: 10_شبیه_ساز_بک_تست_استراتژی_ها.png")
        backtest_tab = page.locator("button:has-text('بک‌تست'), button:has-text('شبیه‌ساز')").first
        if await backtest_tab.count() > 0:
            await backtest_tab.click(force=True)
            await asyncio.sleep(2)
        await page.screenshot(path=str(OUTPUT_DIR / "10_شبیه_ساز_بک_تست_استراتژی_ها.png"))

        # ── 11. 12 Strategies Catalog ──
        print("📸 [11/13] Capturing: 11_کاتالوگ_۱۲_استراتژی_کمی_مستقل.png")
        strat_tab = page.locator("button:has-text('کاتالوگ استراتژی'), button:has-text('۱۲ استراتژی')").first
        if await strat_tab.count() > 0:
            await strat_tab.click(force=True)
            await asyncio.sleep(2)
        await page.screenshot(path=str(OUTPUT_DIR / "11_کاتالوگ_۱۲_استراتژی_کمی_مستقل.png"))

        # ── 12. Post-Mortem Closed Trades Lessons ──
        print("📸 [12/13] Capturing: 12_کالبدشکافی_معاملات_بسته_و_درس_آموخته_های_ai.png")
        if await calib_tab.count() > 0:
            await calib_tab.click(force=True)
            await asyncio.sleep(1.5)
            await page.evaluate("window.scrollTo(0, 950)")
            await asyncio.sleep(1.5)
        await page.screenshot(path=str(OUTPUT_DIR / "12_کالبدشکافی_معاملات_بسته_و_درس_آموخته_های_ai.png"))

        # ── 13. System Health & Risk Settings ──
        print("📸 [13/13] Capturing: 13_پایش_سلامت_خطوط_داده_تفکیک_کارمزد_و_تنظیمات_ریسک.png")
        btn = page.locator("aside button:has-text('سلامت')").first
        if await btn.count() > 0:
            await btn.click(force=True)
            await asyncio.sleep(2.5)
        await page.screenshot(path=str(OUTPUT_DIR / "13_پایش_سلامت_خطوط_داده_تفکیک_کارمزد_و_تنظیمات_ریسک.png"))

        await browser.close()

    print("\n🎉 All 13 detailed full-screen and sub-view snapshots successfully captured!")

if __name__ == "__main__":
    asyncio.run(capture_everything())
