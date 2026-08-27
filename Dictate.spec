# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, collect_dynamic_libs

block_cipher = None

# Collect sherpa_onnx, onnxruntime, sounddevice assets and DLLs
datas = []
datas += collect_data_files('sherpa_onnx')
datas += collect_data_files('onnxruntime')

# Include LICENSE
if os.path.exists('LICENSE'):
    datas.append(('LICENSE', '.'))

# Include hotwords.txt (custom vocabulary & jargon dictionary)
if os.path.exists('hotwords.txt'):
    datas.append(('hotwords.txt', '.'))

# Include assets (earcons, sounds)
if os.path.exists('assets'):
    datas.append(('assets', 'assets'))


binaries = []
binaries += collect_dynamic_libs('sherpa_onnx')
binaries += collect_dynamic_libs('onnxruntime')
binaries += collect_dynamic_libs('sounddevice')

hiddenimports = [
    'sherpa_onnx',
    'onnxruntime',
    'sounddevice',
    'numpy',
    'pyperclip',
    'huggingface_hub',
    'PyQt6',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
]
hiddenimports += collect_submodules('sherpa_onnx')

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'scipy', 'torch', 'IPython'],
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
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='version_info.txt',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='Dictate',
)
