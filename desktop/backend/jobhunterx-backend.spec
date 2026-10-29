# PyInstaller spec: the JobHunterX backend as one folder (fast start; a one-file build unpacks itself on every launch).
# Build with `python desktop/scripts/build_backend.py`, which also copies the result into the Tauri resources.
# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

ROOT = Path(SPECPATH).resolve().parents[1]          # repository root
PROJECT = ROOT / "jobhunterx"                         # the Python project (pyproject.toml lives here)
PKG = PROJECT / "jobhunterx"

datas = [
    (str(PKG / "web"), "jobhunterx/web"),
    (str(PKG / "templates"), "jobhunterx/templates"),
    (str(PKG / "watchlist"), "jobhunterx/watchlist"),
]
binaries = []
hiddenimports = collect_submodules("jobhunterx") + collect_submodules("uvicorn")

# Packages that read data files at run time or import plugins by name.
for name in ("litellm", "browser_use", "trafilatura", "justext", "htmldate", "courlan", "dateparser", "xhtml2pdf",
             "reportlab", "ddgs", "curl_cffi", "selectolax", "tiktoken", "tiktoken_ext", "certifi", "pymupdf", "fitz",
             "google.genai", "structlog", "diskcache", "aiosqlite", "lxml", "bs4", "jinja2", "multipart", "psutil"):
    try:
        d, b, h = collect_all(name)
    except Exception:                                  # optional or absent on this platform
        continue
    datas += d
    binaries += b
    hiddenimports += h

a = Analysis(
    [str(ROOT / "desktop" / "backend" / "launcher.py")],
    pathex=[str(PROJECT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["tkinter", "pytest", "IPython", "matplotlib", "notebook"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="jobhunterx-backend",
    console=True,            # the window reads our stdout; the desktop shell hides the console on Windows
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="jobhunterx-backend")
