# -*- mode: python ; coding: utf-8 -*-
# PyInstaller 打包配置：python -m PyInstaller --clean GUI-ADB.spec
# 打包前请先运行 python build_icon.py 生成 adb.ico（Windows exe 图标必须用 .ico）
# 图标不显示时：已关闭 exe 的 UPX，并用 --clean 重新打包

import os

block_cipher = None

# 图标用绝对路径，避免打包时找不到导致 exe 使用默认图标（任务管理器会显示为 Python 默认）
SPEC_DIR = os.path.dirname(os.path.abspath(SPEC))
ICON_PATH = os.path.join(SPEC_DIR, 'adb.ico')

# 将 platform-tools 整个目录打进包，运行时解压到 _MEIPASS/platform-tools
# Analysis.datas 需要 (源路径, 目标路径) 的 2 元组列表，不能直接用 Tree()
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('platform-tools', 'platform-tools'),
        ('adb.png', '.'),
        ('adb.ico', '.'),
    ],
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
# contents_directory 必须写在 EXE 里，bootloader 才会按该目录找资源；只写 COLLECT 不生效
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='GUI-ADB',
    debug=False,
    icon=ICON_PATH,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # UPX 会破坏 exe 内嵌的图标资源，导致任务管理器显示默认图标
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    contents_directory='runtime',  # 打包后资源目录名，默认 _internal；bootloader 据此找资源
)

# 与 EXE 的 contents_directory 保持一致，COLLECT 才会把文件放进同名子目录
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ADB-GUI',
    contents_directory='runtime',
)
