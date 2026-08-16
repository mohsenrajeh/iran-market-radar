"""Script to create a complete, self-contained audit-ready ZIP archive for experts and institutions."""
import os
import sys
import zipfile
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
BASE_DIR = Path(r"D:\My Project\04_Trading-AI\iran-market-radar")
PRESENTATION_DIR = BASE_DIR / "presentation_package"
ZIP_OUTPUT = BASE_DIR / "IRAN_MARKET_RADAR_AUDIT_READY_v2.5.zip"

def create_audit_zip():
    print(f"📦 Packaging audit deliverables into: {ZIP_OUTPUT} ...")
    with zipfile.ZipFile(ZIP_OUTPUT, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. Add all files from presentation_package/
        for root, dirs, files in os.walk(PRESENTATION_DIR):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(BASE_DIR)
                zf.write(file_path, arcname)
                print(f"  + Added: {arcname}")

        # 2. Add documentation and audit files
        docs_to_include = [
            "AUDIT_REPORT_IRAN_MARKET_RADAR.md",
            "README_FA.md",
            "START_HERE.md",
            "docker-compose.yml",
            "requirements.txt",
        ]
        for doc in docs_to_include:
            doc_path = BASE_DIR / doc
            if doc_path.exists():
                zf.write(doc_path, f"docs/{doc}")
                print(f"  + Added: docs/{doc}")

    print(f"\n🎉 Archive created successfully! File size: {ZIP_OUTPUT.stat().st_size / (1024*1024):.2f} MB")

if __name__ == "__main__":
    create_audit_zip()
