# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec file for Viper Terminal
#
# Usage:
#   pyinstaller scripts/build/viper.spec
#
# Output:
#   dist/viper (or dist/viper.exe on Windows)
#

import sys
from pathlib import Path

block_cipher = None

# Get the project root
spec_dir = Path(SPECPATH)
project_root = spec_dir.parent.parent

a = Analysis(
    [str(project_root / 'viper' / '__main__.py')],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        # Include any data files if needed
        # (str(project_root / 'viper' / 'data'), 'viper/data'),
    ],
    hiddenimports=[
        # Textual and Rich dependencies
        'textual',
        'textual.app',
        'textual.widgets',
        'textual.containers',
        'textual.binding',
        'textual.screen',
        'rich',
        'rich.console',
        'rich.text',
        'rich.markup',
        'rich.style',
        # yfinance and dependencies
        'yfinance',
        'pandas',
        'numpy',
        'requests',
        'urllib3',
        # httpx for async
        'httpx',
        'httpcore',
        'anyio',
        'sniffio',
        # trafilatura for article reading
        'trafilatura',
        # Other potential hidden imports
        'certifi',
        'charset_normalizer',
        'idna',
        'dateutil',
        'pytz',
        'lxml',
        'bs4',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude dev dependencies
        'pytest',
        'pytest_asyncio',
        'pytest_cov',
        'pytest_mock',
        'mypy',
        'ruff',
        'respx',
        # Exclude unnecessary large packages
        'matplotlib',
        'scipy',
        'PIL',
        'tkinter',
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='viper',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Terminal application
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
