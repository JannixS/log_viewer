# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for Java Log Viewer — builds a single Windows .exe that
bundles Python, Flask, pywin32 and all templates.

Build (on Windows, from the project root):
    pip install pyinstaller pywin32 flask
    pyinstaller log_viewer.spec
The output is: dist\log-viewer.exe
"""

import sys
from pathlib import Path

block_cipher = None

a = Analysis(
    ["service.py"],
    pathex=["."],
    binaries=[],
    datas=[
        # Bundle the Jinja2 templates into the exe
        ("templates", "templates"),
        # Bundle the default sample logs if present
        ("logs", "logs"),
    ],
    hiddenimports=[
        # pywin32 service internals
        "win32serviceutil",
        "win32service",
        "win32event",
        "servicemanager",
        "pywintypes",
        # Werkzeug internals referenced at runtime
        "werkzeug.serving",
        "werkzeug.debug",
        # Flask / Jinja2
        "flask",
        "jinja2",
        "jinja2.ext",
        "win32timezone",
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

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="log-viewer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # no console window when running as a service
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # Embed a manifest so Windows UAC prompts correctly
    uac_admin=True,
    version=None,
    icon=None,
)
