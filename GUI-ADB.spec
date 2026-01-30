# -*- mode: python ; coding: utf-8 -*-
# PyInstaller 打包配置：python -m PyInstaller GUI-ADB.spec

block_cipher = None

# 将 platform-tools 整个目录打进包，运行时解压到 _MEIPASS/platform-tools
# Analysis.datas 需要 (源路径, 目标路径) 的 2 元组列表，不能直接用 Tree()
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('platform-tools', 'platform-tools')],
    hiddenimports=[
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'zeroconf',
        'qrcode',
        'qrcode.image.pil',
        'PIL',
        'PIL.Image',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# 目录模式（onedir）：exe 与依赖在同一文件夹，启动快、无需每次解压
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='GUI-ADB',
    debug=False,
    icon='adb.png',
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='GUI-ADB',
)
