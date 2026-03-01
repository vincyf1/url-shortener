"""Clipboard helper with graceful fallback."""

import subprocess
import shutil
import sys


def copy_to_clipboard(text: str) -> tuple[bool, str]:
    """Try to copy text to the system clipboard.

    Returns (success, message).
    """
    # Try pyperclip first
    try:
        import pyperclip  # type: ignore[import-untyped]

        pyperclip.copy(text)
        return True, "Copied to clipboard!"
    except Exception:
        pass

    # Fallback: platform-specific commands
    if sys.platform == "darwin":
        cmd = "pbcopy"
    elif shutil.which("xclip"):
        cmd = "xclip -selection clipboard"
    elif shutil.which("xsel"):
        cmd = "xsel --clipboard --input"
    elif shutil.which("wl-copy"):
        cmd = "wl-copy"
    else:
        return False, f"Copy manually: {text}"

    try:
        proc = subprocess.Popen(
            cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        proc.communicate(text.encode(), timeout=3)
        if proc.returncode == 0:
            return True, "Copied to clipboard!"
        return False, f"Copy manually: {text}"
    except Exception:
        return False, f"Copy manually: {text}"
