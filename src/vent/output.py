import shutil
import subprocess
import sys


def copy_to_clipboard(text: str) -> None:
    result = subprocess.run(["wl-copy"], input=text.encode(), check=False)
    if result.returncode != 0:
        print("vent: wl-copy failed", file=sys.stderr)


def type_text(text: str) -> None:
    result = subprocess.run(["wtype", "--", text], check=False)
    if result.returncode != 0:
        print("vent: wtype failed", file=sys.stderr)


def output_text(text: str) -> None:
    """Copy to clipboard first (reliable), then type via wtype."""
    if not shutil.which("wl-copy"):
        print("vent: wl-copy not found", file=sys.stderr)
    else:
        copy_to_clipboard(text)
    if not shutil.which("wtype"):
        print("vent: wtype not found", file=sys.stderr)
    else:
        type_text(text)
