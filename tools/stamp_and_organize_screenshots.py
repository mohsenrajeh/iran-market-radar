"""Script to organize, watermark with timestamps, and generate side-by-side comparisons."""
import os
import sys
import shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(r"D:\My Project\04_Trading-AI\iran-market-radar")
PRESENTATION_DIR = BASE_DIR / "presentation_package"

OLD_SRC_DIR = PRESENTATION_DIR / "screenshots"
NEW_SRC_DIR = PRESENTATION_DIR / "assets"

OLD_OUT_DIR = PRESENTATION_DIR / "01_ARCHIVE_PRE_AUDIT_2026-08-15_14-30"
NEW_OUT_DIR = PRESENTATION_DIR / "02_CURRENT_AUDIT_REMEDIATED_2026-08-16_16-50"
COMPARE_OUT_DIR = PRESENTATION_DIR / "03_SIDE_BY_SIDE_COMPARISON_BEFORE_AFTER"

OLD_OUT_DIR.mkdir(parents=True, exist_ok=True)
NEW_OUT_DIR.mkdir(parents=True, exist_ok=True)
COMPARE_OUT_DIR.mkdir(parents=True, exist_ok=True)

FONT_PATH = "C:/Windows/Fonts/tahoma.ttf"
FONT_BOLD_PATH = "C:/Windows/Fonts/tahomabd.ttf" if os.path.exists("C:/Windows/Fonts/tahomabd.ttf") else "C:/Windows/Fonts/arialbd.ttf"

def add_header_banner(
    img_path: Path,
    title: str,
    subtitle: str,
    tag: str,
    tag_bg: tuple[int, int, int],
    banner_bg: tuple[int, int, int] = (15, 23, 42),
    border_color: tuple[int, int, int] = (59, 130, 246),
) -> Image.Image:
    """Adds an institutional header banner with timestamps to a screenshot."""
    orig_img = Image.open(img_path).convert("RGB")
    width, height = orig_img.size

    banner_height = 80
    new_img = Image.new("RGB", (width, height + banner_height), banner_bg)
    draw = ImageDraw.Draw(new_img)

    # Draw banner background & accent border
    draw.rectangle([(0, 0), (width, banner_height)], fill=banner_bg)
    draw.line([(0, banner_height - 3), (width, banner_height - 3)], fill=border_color, width=3)

    # Fonts
    try:
        font_title = ImageFont.truetype(FONT_BOLD_PATH, 24)
        font_sub = ImageFont.truetype(FONT_PATH, 16)
        font_tag = ImageFont.truetype(FONT_BOLD_PATH, 16)
    except Exception:
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()
        font_tag = ImageFont.load_default()

    # Draw Tag Badge on Left
    tag_text = f" {tag} "
    tag_x = 30
    tag_y = 22
    tag_w = len(tag_text) * 14 + 20
    tag_h = 36
    draw.rounded_rectangle([(tag_x, tag_y), (tag_x + tag_w, tag_y + tag_h)], radius=6, fill=tag_bg)
    draw.text((tag_x + 12, tag_y + 8), tag_text, fill=(255, 255, 255), font=font_tag)

    # Draw Title and Subtitle (Timestamp & Status)
    text_x = tag_x + tag_w + 25
    draw.text((text_x, 15), title, fill=(248, 250, 252), font=font_title)
    draw.text((text_x, 48), subtitle, fill=(148, 163, 184), font=font_sub)

    # Paste original image below banner
    new_img.paste(orig_img, (0, banner_height))
    return new_img


def process_all_images():
    print("🎨 Processing and stamping Old Screenshots (Pre-Audit)...")
    old_files_map = {
        "01_dashboard_overview.png": ("PRE_AUDIT_2026-08-15_1430_01_dashboard.png", "داشبورد کلان (قبل از ممیزی)"),
        "02_opportunities_radar.png": ("PRE_AUDIT_2026-08-15_1430_02_radar.png", "دیده‌بان فرصت‌ها (قبل از ممیزی)"),
        "03_open_positions_portfolio.png": ("PRE_AUDIT_2026-08-15_1430_03_positions.png", "معاملات باز و پورتفو (قبل از ممیزی)"),
        "04_fundamental_codal.png": ("PRE_AUDIT_2026-08-15_1430_04_fundamental.png", "تحلیل بنیادی و کدال (قبل از ممیزی)"),
        "05_trading_lab_calibration.png": ("PRE_AUDIT_2026-08-15_1430_05_trading_lab.png", "آزمایشگاه معاملاتی (قبل از ممیزی)"),
        "06_health_settings.png": ("PRE_AUDIT_2026-08-15_1430_06_health.png", "تنظیمات و سلامت (قبل از ممیزی)"),
    }

    stamped_old = {}
    for orig_name, (out_name, title_fa) in old_files_map.items():
        src_p = OLD_SRC_DIR / orig_name
        if not src_p.exists():
            continue
        stamped = add_header_banner(
            img_path=src_p,
            title=f"🔴 نسخه ۱.۰ آرشیو — {title_fa}",
            subtitle="تاریخ و ساعت ثبت: شنبه ۲۴ مرداد ۱۴۰۵ - ۱۴:۳۰ (2026-08-15 14:30) | وضعیت ممیزی: رد شده (NO-GO)",
            tag="نسخه قدیمی — رد ممیزی",
            tag_bg=(220, 38, 38),  # Red
            banner_bg=(24, 24, 27),
            border_color=(239, 68, 68),
        )
        dst_p = OLD_OUT_DIR / out_name
        stamped.save(dst_p, quality=95)
        stamped_old[orig_name] = dst_p
        print(f"  ✓ Saved stamped old: {out_name}")

    print("\n🎨 Processing and stamping New Screenshots (Post-Audit v2.5)...")
    new_files_map = {
        "01_dashboard_overview.png": ("NEW_v2.5_2026-08-16_1650_01_dashboard_overview.png", "داشبورد کلان و پایش ۳۶۰ درجه بازار"),
        "02_opportunities_radar.png": ("NEW_v2.5_2026-08-16_1650_02_opportunities_radar.png", "دیده‌بان فرصت‌ها و رادار کمّی"),
        "03_open_positions_portfolio.png": ("NEW_v2.5_2026-08-16_1650_03_open_positions_portfolio.png", "میزکار موقعیت‌های باز، دفترکل نقدینگی و مدیریت ریسک"),
        "04_fundamental_codal.png": ("NEW_v2.5_2026-08-16_1650_04_fundamental_codal.png", "تحلیل بنیادی، صورت‌های مالی کدال و متادیتای Point-in-Time"),
        "05_trading_lab_calibration.png": ("NEW_v2.5_2026-08-16_1650_05_trading_lab_calibration.png", "مرکز کالیبراسیون هوش مصنوعی، شاخص Brier و فاصله اطمینان ویلسون"),
        "06_health_settings.png": ("NEW_v2.5_2026-08-16_1650_06_health_settings.png", "تنظیمات سلامت سامانه، تفکیک کارمزد ۱.۲۵۶۲٪ و گیت‌های ریسک"),
        "07_post_mortem_lessons.png": ("NEW_v2.5_2026-08-16_1650_07_post_mortem_lessons.png", "لاگ معاملات بسته و درس‌آموخته‌های هوش مصنوعی"),
        "08_strategy_backtest.png": ("NEW_v2.5_2026-08-16_1650_08_strategy_backtest.png", "شبیه‌ساز بک‌تست ۱۲ استراتژی کمّی مستقل"),
    }

    stamped_new = {}
    for orig_name, (out_name, title_fa) in new_files_map.items():
        src_p = NEW_SRC_DIR / orig_name
        if not src_p.exists():
            continue
        stamped = add_header_banner(
            img_path=src_p,
            title=f"🟢 نسخه ۲.۵ نهایی — {title_fa}",
            subtitle="تاریخ و ساعت ثبت: یکشنبه ۲۵ مرداد ۱۴۰۵ - ۱۶:۵۰ (2026-08-16 16:50) | وضعیت ممیزی: تایید نهایی (GO - Production Ready)",
            tag="نسخه جدید — تایید ممیزی",
            tag_bg=(22, 163, 74),  # Emerald Green
            banner_bg=(15, 23, 42),
            border_color=(34, 197, 94),
        )
        dst_p = NEW_OUT_DIR / out_name
        stamped.save(dst_p, quality=95)
        stamped_new[orig_name] = dst_p
        print(f"  ✓ Saved stamped new: {out_name}")

    print("\n🖼️ Generating Side-by-Side Comparison composite images...")
    compare_keys = [
        ("01_dashboard_overview.png", "COMPARE_01_dashboard_overview.png", "مقایسه داشبورد اصلی"),
        ("02_opportunities_radar.png", "COMPARE_02_opportunities_radar.png", "مقایسه دیده‌بان و رادار"),
        ("03_open_positions_portfolio.png", "COMPARE_03_open_positions_portfolio.png", "مقایسه موقعیت‌های باز و پورتفو"),
        ("04_fundamental_codal.png", "COMPARE_04_fundamental_codal.png", "مقایسه تحلیل بنیادی و کدال"),
        ("05_trading_lab_calibration.png", "COMPARE_05_trading_lab_calibration.png", "مقایسه آزمایشگاه کالیبراسیون هوش مصنوعی"),
        ("06_health_settings.png", "COMPARE_06_health_settings.png", "مقایسه تنظیمات سلامت و کارمزدها"),
    ]

    for key, comp_name, comp_title in compare_keys:
        if key in stamped_old and key in stamped_new:
            img_o = Image.open(stamped_old[key])
            img_n = Image.open(stamped_new[key])

            # Resize both to same height for side-by-side comparison
            target_h = 900
            w_o = int(img_o.width * (target_h / img_o.height))
            w_n = int(img_n.width * (target_h / img_n.height))

            img_o_res = img_o.resize((w_o, target_h), Image.Resampling.LANCZOS)
            img_n_res = img_n.resize((w_n, target_h), Image.Resampling.LANCZOS)

            comp_img = Image.new("RGB", (w_o + w_n + 20, target_h + 60), (10, 15, 30))
            draw_c = ImageDraw.Draw(comp_img)

            # Header for comparison
            try:
                f_comp = ImageFont.truetype(FONT_BOLD_PATH, 24)
            except Exception:
                f_comp = ImageFont.load_default()

            draw_c.text((30, 15), f"🔍 {comp_title} — مقایسه قبل و بعد از اصلاحات ممیزی نهادی", fill=(248, 250, 252), font=f_comp)

            # Paste left (old) and right (new)
            comp_img.paste(img_o_res, (0, 60))
            comp_img.paste(img_n_res, (w_o + 20, 60))

            comp_dst = COMPARE_OUT_DIR / comp_name
            comp_img.save(comp_dst, quality=90)
            print(f"  ✓ Saved comparison: {comp_name}")

    print("\n✅ All stamped and comparison images generated successfully!")


if __name__ == "__main__":
    process_all_images()
