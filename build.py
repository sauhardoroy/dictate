"""Reproducible Windows build entrypoint: ``.venv\\Scripts\\python build.py``."""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP_NAME = "Dictate"


def run(command: list[str]) -> None:
    print("+", " ".join(command))
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Dictate with PyInstaller")
    parser.add_argument("--clean", action="store_true", help="remove prior build and dist directories first")
    parser.add_argument("--smoke", action="store_true", help="launch the built app in smoke mode after packaging")
    args = parser.parse_args()

    if args.clean:
        for directory in (ROOT / "build", ROOT / "dist"):
            if directory.exists():
                shutil.rmtree(directory)

    run([sys.executable, "-m", "PyInstaller", "--noconfirm", "Dictate.spec"])
    executable = ROOT / "dist" / APP_NAME / f"{APP_NAME}.exe"
    if not executable.exists():
        raise RuntimeError(f"Build finished without {executable}")
    print(f"Built: {executable}")

    if args.smoke:
        run([str(executable), "--smoke", "--console"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
