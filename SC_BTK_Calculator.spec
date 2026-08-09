# -*- mode: python ; coding: utf-8 -*-
# PyInstaller 配置：WebView2 UI 版（入口 main.py）
# 打包产物：SC_BTK_Calculator.exe（放项目根目录，依赖在 _internal/）

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('ui', 'ui'),
        ('assets/icons', 'assets/icons'),
    ],
    hiddenimports=[
        'webview.platforms.edgechromium',
        'backend',
        'btk_core',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='SC_BTK_Calculator',
    debug=False,
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
    icon='assets/icons/app_icon_black.ico',
)
