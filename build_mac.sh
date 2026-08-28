#!/usr/bin/env bash
set -e

echo "=========================================="
echo "      Building Dictate for macOS          "
echo "=========================================="

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

# 1. Prepare virtual environment
if [ ! -d ".venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv .venv
fi

source .venv/bin/activate

echo "Installing/updating dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

# 2. Clean previous build artifacts
echo "Cleaning previous builds..."
rm -rf build dist/Dictate.app dist/Dictate-macOS.dmg dist/Dictate-macOS-Universal.zip

# 3. Build Dictate.app with PyInstaller
echo "Compiling Dictate.app using Dictate_mac.spec..."
pyinstaller --noconfirm --clean Dictate_mac.spec

if [ ! -d "dist/Dictate.app" ]; then
    echo "❌ Error: dist/Dictate.app was not created."
    exit 1
fi

echo "✅ Successfully built dist/Dictate.app"

# 4. Ad-hoc codesign if on macOS to pass basic system security checks
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "Applying ad-hoc code signature..."
    codesign --force --deep --sign - "dist/Dictate.app" || true

    # 5. Create DMG installer
    echo "Creating Apple Disk Image (DMG)..."
    DMG_TEMP="dist/dmg_pack"
    rm -rf "$DMG_TEMP"
    mkdir -p "$DMG_TEMP"
    cp -R "dist/Dictate.app" "$DMG_TEMP/"
    ln -s /Applications "$DMG_TEMP/Applications"

    hdiutil create -volname "Dictate" \
        -srcfolder "$DMG_TEMP" \
        -ov -format UDZO \
        "dist/Dictate-macOS.dmg"

    rm -rf "$DMG_TEMP"
    echo "✅ Successfully packaged: dist/Dictate-macOS.dmg"

    # Also package a portable zip
    cd dist
    zip -r -y "Dictate-macOS.zip" "Dictate.app"
    cd "$ROOT_DIR"
    echo "✅ Successfully packaged: dist/Dictate-macOS.zip"
fi

echo "=========================================="
echo "       macOS Build Complete!              "
echo "=========================================="
