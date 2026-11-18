# -*- mode: python ; coding: utf-8 -*-
import os

from PyInstaller.utils.hooks import collect_all

# Все пути считаются от папки этого spec-файла, поэтому проект можно переносить.
BASE = SPECPATH
MKVMERGE = os.environ.get("MKVMERGE", r"C:\Program Files\MKVToolNix\mkvmerge.exe")

datas = [
    (os.path.join(BASE, "LICENSES"), "LICENSES"),
    (os.path.join(BASE, "app.ico"), "."),
    (os.path.join(BASE, "mkv_muxer.py"), "."),
]
binaries = [(MKVMERGE, "MKVToolNix")]
hiddenimports = []
tmp_ret = collect_all("customtkinter")
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]


a = Analysis(
    [os.path.join(BASE, "mkv_muxer.py")],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name="MKV_Muxer",
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
    icon=[os.path.join(BASE, "app.ico")],
)
