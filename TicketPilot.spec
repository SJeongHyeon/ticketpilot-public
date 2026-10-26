# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller recipe for the Windows TicketPilot onedir distribution."""

from pathlib import Path
import sys

from PyInstaller.utils.hooks import collect_data_files, collect_submodules


project_root = Path(SPECPATH)
python_root = Path(sys.base_prefix)
asset_data = [(str(project_root / "assets"), "assets")]
customtkinter_data = collect_data_files("customtkinter")
pillow_data = collect_data_files("PIL")
tcl_tk_data = [
    (str(python_root / "tcl" / "tcl8.6"), "_tcl_data"),
    (str(python_root / "tcl" / "tk8.6"), "_tk_data"),
]
tcl_tk_binaries = [
    (str(python_root / "DLLs" / binary_name), ".")
    for binary_name in ("_tkinter.pyd", "tcl86t.dll", "tk86t.dll")
]
hidden_imports = ["tkinter", "_tkinter"] + collect_submodules("customtkinter") + collect_submodules("PIL")


analysis = Analysis(
    [str(project_root / "main.py")],
    pathex=[str(project_root)],
    binaries=tcl_tk_binaries,
    datas=asset_data + customtkinter_data + pillow_data + tcl_tk_data,
    hiddenimports=hidden_imports,
    hookspath=[str(project_root / "pyinstaller_hooks")],
    hooksconfig={},
    runtime_hooks=[str(project_root / "pyi_rth_tcltk.py")],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(analysis.pure)

executable = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="TicketPilot",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=str(project_root / "assets" / "app.ico"),
)

collection = COLLECT(
    executable,
    analysis.binaries,
    analysis.zipfiles,
    analysis.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="TicketPilot",
)
