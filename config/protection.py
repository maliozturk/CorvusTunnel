"""
CorvusTunnel File Protection — OS-level write guard for critical files.

When the server boots, all CorvusTunnel source files and .env are set
to READ-ONLY at the OS level.  This is the last line of defense: even
if a remote command, AI agent, or injected prompt attempts to modify
.env, the operating system itself will deny the write.

Files are unlocked on clean shutdown so the developer can edit normally.

    from config.protection import lock_critical_files, unlock_critical_files

    count = lock_critical_files()   # call once at boot
    # ... server runs ...
    unlock_critical_files()         # called via atexit automatically
"""

from __future__ import annotations

import atexit
import logging
import os
import stat
from pathlib import Path

logger = logging.getLogger(__name__)

# ── CorvusTunnel project root (resolved at import time) ──────────────
CORVUS_ROOT = Path(__file__).resolve().parent.parent

# ── Individual files that are ALWAYS locked ──────────────────────────
_SECURE_DIR = Path.home() / ".corvustunnel"

LOCKED_FILES: list[Path] = [
    _SECURE_DIR / ".env",        # primary config (secure location)
    CORVUS_ROOT / ".env",        # legacy/leftover — lock it too
    CORVUS_ROOT / ".env.example",
    CORVUS_ROOT / "main.py",
    CORVUS_ROOT / "public_app.py",
    CORVUS_ROOT / "internal_app.py",
    CORVUS_ROOT / "requirements.txt",
]

# ── Directories whose .py files are locked ───────────────────────────
LOCKED_DIRS: list[Path] = [
    CORVUS_ROOT / "config",
    CORVUS_ROOT / "auth",
    CORVUS_ROOT / "audit",
    CORVUS_ROOT / "routers",
    CORVUS_ROOT / "executor",
    CORVUS_ROOT / "jobqueue",
    CORVUS_ROOT / "models",
]

_locked: list[Path] = []


def lock_critical_files() -> int:
    """Set critical files to read-only.  Returns count of locked files.

    Also registers ``unlock_critical_files`` via :func:`atexit.register`
    so files are restored on clean shutdown.
    """
    global _locked
    _locked = []

    def _lock(p: Path) -> bool:
        try:
            os.chmod(p, stat.S_IREAD)
            _locked.append(p)
            return True
        except OSError:
            return False

    for f in LOCKED_FILES:
        if f.exists():
            _lock(f)

    for d in LOCKED_DIRS:
        if d.exists():
            for py in d.rglob("*.py"):
                _lock(py)

    logger.info(
        "File protection ON — %d files locked read-only "
        "(including .env, all source code)",
        len(_locked),
    )

    atexit.register(unlock_critical_files)
    return len(_locked)


def unlock_critical_files() -> None:
    """Restore write permissions.  Called automatically on clean shutdown."""
    restored = 0
    for f in _locked:
        if f.exists():
            try:
                os.chmod(f, stat.S_IREAD | stat.S_IWRITE)
                restored += 1
            except OSError:
                pass
    if restored:
        logger.info("File protection OFF — %d files unlocked", restored)


def is_path_in_corvus(path_str: str) -> bool:
    """Return True if *path_str* resolves inside the CorvusTunnel tree."""
    try:
        Path(path_str).resolve().relative_to(CORVUS_ROOT)
        return True
    except (ValueError, OSError):
        return False
