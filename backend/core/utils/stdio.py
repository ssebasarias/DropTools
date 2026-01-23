from __future__ import annotations

import os
import sys


def configure_utf8_stdio() -> None:
    """
    Windows consoles often default to cp1252 which crashes on emojis (UnicodeEncodeError).
    We force UTF-8 and replace invalid characters instead of crashing.
    Safe to call multiple times.
    """
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    os.environ.setdefault("PYTHONUTF8", "1")

    for stream in (sys.stdout, sys.stderr):
        try:
            # Python 3.7+: TextIOWrapper.reconfigure
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

