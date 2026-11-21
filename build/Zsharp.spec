# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包配置（onedir 模式）。

用法（在仓库根目录）：
    pyinstaller build/Zsharp.spec --noconfirm --clean
"""

import os

ROOT = os.path.dirname(SPECPATH)

# 界面资源必须和 exe 同级，程序用 BASE/<文件名> 直接读取
ASSETS = [
    "icon.png",
    "ic_play.png",
    "ic_pause.png",
    "ic_replay.png",
]

datas = [(os.path.join(ROOT, f), ".") for f in ASSETS if os.path.exists(os.path.join(ROOT, f))]

# 明显用不到的重量级库，排除掉能显著减小体积
EXCLUDES = [
    "tkinter",
    "unittest",
    "pydoc",
    "doctest",
    "numpy",
    "scipy",
    "pandas",
    "matplotlib",
    "PIL",
    "cv2",
    "IPython",
    "pytest",
    "setuptools",
    "pip",
]

a = Analysis(
    [os.path.join(ROOT, "app_qt.py")],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Zsharp",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,          # 无控制台窗口
    disable_windowed_traceback=False,
    icon=os.path.join(ROOT, "icon.ico") if os.path.exists(os.path.join(ROOT, "icon.ico")) else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Zsharp",
)
