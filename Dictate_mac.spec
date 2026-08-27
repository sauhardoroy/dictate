# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller specification for building Dictate.app on macOS."""
import os
import sys
from PyInstaller.utils.hooks import collect_dynamic_libs

block_cipher = None

datas = []
if os.path.exists('hotwords.txt'):
    datas.append(('hotwords.txt', '.'))

if os.path.exists('assets'):
    datas.append(('assets', 'assets'))

binaries = []
try:
    binaries += collect_dynamic_libs('sherpa_onnx')
    binaries += collect_dynamic_libs('onnxruntime')
    binaries += collect_dynamic_libs('sounddevice')
except Exception:
    pass

hiddenimports = [
    'sherpa_onnx',
    'onnxruntime',
    'sounddevice',
    'numpy',
    'pyperclip',
    'pynput',
    'huggingface_hub',
    'PyQt6',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'scipy',
        'torch',
        'torchvision',
        'torchaudio',
        'faster_whisper',
        'ctranslate2',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Dictate',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.icns' if os.path.exists('assets/icon.icns') else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Dictate',
)

app = BUNDLE(
    coll,
    name='Dictate.app',
    icon='assets/icon.icns' if os.path.exists('assets/icon.icns') else None,
    bundle_identifier='com.dictate.app',
    info_plist={
        'CFBundleDisplayName': 'Dictate',
        'CFBundleName': 'Dictate',
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1.0.0',
        'NSMicrophoneUsageDescription': 'Dictate requires microphone access for offline speech-to-text dictation.',
        'NSAppleEventsUsageDescription': 'Dictate requires accessibility access to paste transcribed text into active applications.',
        'LSUIElement': True,  # Runs as menu bar & floating tool app without docking icon clutter
        'NSHighResolutionCapable': True,
    }
)
