"""Clipboard helper with graceful fallback."""

import logging
import shutil
import subprocess
import sys

logger = logging.getLogger(__name__)


def copy_to_clipboard(text: str) -> tuple[bool, str]:
    """Try to copy text to the system clipboard.

    Returns (success, message).
    """
    try:
        import pyperclip  # type: ignore[import-untyped]

        pyperclip.copy(text)
        return True, "Copied to clipboard!"
    except Exception:
        logger.debug("pyperclip unavailable or failed", exc_info=True)

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
            cmd,
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        proc.communicate(text.encode(), timeout=3)
        if proc.returncode == 0:
            return True, "Copied to clipboard!"
        return False, f"Copy manually: {text}"
    except Exception:
        logger.debug("clipboard command failed", exc_info=True)
        return False, f"Copy manually: {text}"
