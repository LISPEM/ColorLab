# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — builds ColorLab into a single-file windowed executable."""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = [
    ('dataManager/illuminants.csv', 'dataManager'),
    ('dataManager/white_point.csv', 'dataManager'),
]
datas += collect_data_files('customtkinter')

hiddenimports = collect_submodules('customtkinter')

a = Analysis(
    ['clgui.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt5', 'PyQt6', 'PySide2', 'PySide6', 'tests'],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ColorLab',
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
)
