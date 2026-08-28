"""Package the built Dictate directory into a clean distributable ZIP file."""
import os
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST_DIR = ROOT / "dist"
APP_DIR = DIST_DIR / "Dictate"
ZIP_OUTPUT = DIST_DIR / "Dictate-Windows-x64.zip"

def main():
    if not APP_DIR.exists():
        print(f"Error: {APP_DIR} does not exist. Run build.py first.")
        sys.exit(1)

    print(f"Creating distribution archive: {ZIP_OUTPUT.name}...")
    if ZIP_OUTPUT.exists():
        ZIP_OUTPUT.unlink()

    with zipfile.ZipFile(ZIP_OUTPUT, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in APP_DIR.rglob("*"):
            if file.is_file():
                arcname = file.relative_to(DIST_DIR)
                zf.write(file, arcname)

    size_mb = ZIP_OUTPUT.stat().st_size / (1024 * 1024)
    print(f"Created {ZIP_OUTPUT} ({size_mb:.2f} MB)")

if __name__ == "__main__":
    main()
