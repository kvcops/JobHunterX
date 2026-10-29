"""
Freeze the Python backend and put it where the desktop app bundles it.

    python desktop/scripts/build_backend.py            # build + self-test
    python desktop/scripts/build_backend.py --no-test  # build only

Needs the project's packages and PyInstaller in the current Python (`pip install -e ./jobhunterx pyinstaller`).
Output: desktop/src-tauri/backend/ (the folder Tauri ships as a resource; it is not committed).
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

DESKTOP = Path(__file__).resolve().parents[1]
WORK = DESKTOP / "build"
TARGET = DESKTOP / "src-tauri" / "backend"
EXE = "jobhunterx-backend.exe" if sys.platform == "win32" else "jobhunterx-backend"


def main() -> int:
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
                    "--distpath", str(WORK / "dist"), "--workpath", str(WORK / "work"),
                    str(DESKTOP / "backend" / "jobhunterx-backend.spec")], check=True)
    built = WORK / "dist" / "jobhunterx-backend"
    if TARGET.exists():
        shutil.rmtree(TARGET)
    shutil.copytree(built, TARGET, symlinks=True)
    print(f"backend copied to {TARGET}")
    if "--no-test" in sys.argv:
        return 0
    print("self-test of the frozen backend:")
    return subprocess.run([str(TARGET / EXE), "--self-test"], timeout=300).returncode


if __name__ == "__main__":
    sys.exit(main())
