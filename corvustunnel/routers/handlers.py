# /*--------------------------------*- py -*-----------------------------*\
# |     __                                                               |
# |   <(o )___    CorvusTunnel                                           |
# |    ( ._> /    control AI agents from any device                      |
# |     `---'     self-hosted · E2E encrypted · MIT                      |
# *----------------------------------------------------------------------*/
# File:        corvustunnel/routers/handlers.py
# Description: Transport-independent request handlers shared by the REST
#              routes (LAN/direct mode) and the encrypted channel dispatcher.
# \*---------------------------------------------------------------------*/

import os
import re
import shutil
from pathlib import Path

ALLOWED_AGENTS = ("agy", "codex", "claude")
ALLOWED_FLAGS = {"--dangerously-skip-permissions"}


class AppError(Exception):
    def __init__(self, status, detail):
        super().__init__(detail)
        self.status = status
        self.detail = detail


def _roots():
    from corvustunnel.config.settings import get_settings

    return [Path(d).resolve() for d in get_settings().allowed_dir_list]


def _under_roots(target):
    for root in _roots():
        try:
            target.relative_to(root)
            return root
        except ValueError:
            continue
    return None


def validate_work_dir(work_dir):
    roots = _roots()
    if not roots:
        return False
    target = Path(work_dir).resolve()
    return any(target == root or target.is_relative_to(root) for root in roots)


def filter_flags(flags):
    if not flags:
        return None
    if isinstance(flags, str):
        flags = [f.strip() for f in flags.split(",") if f.strip()]
    kept = [f for f in flags if f in ALLOWED_FLAGS]
    return kept or None


def check_agents():
    from corvustunnel.config.settings import get_settings

    settings = get_settings()
    cwd = os.getcwd()
    default_dir = cwd

    roots = [Path(d).resolve() for d in settings.allowed_dir_list]
    cwd_path = Path(cwd).resolve()
    cwd_allowed = any(cwd_path == root or cwd_path.is_relative_to(root) for root in roots)
    if not cwd_allowed and settings.allowed_dir_list:
        default_dir = settings.allowed_dir_list[0]

    return {
        "agents": [
            {"name": name, "available": shutil.which(name) is not None, "path": shutil.which(name)}
            for name in ALLOWED_AGENTS
        ],
        "default_work_dir": str(Path(default_dir).resolve()),
    }


def browse(path):
    roots = _roots()
    if not roots:
        raise AppError(400, "No allowed directories configured — set ALLOWED_DIRS")

    if not path:
        dirs = [
            {"name": r.name, "path": str(r)} for r in roots if r.exists() and r.is_dir()
        ]
        return {"current": "Projects", "parent": None, "directories": dirs}

    target = Path(path).resolve()
    active_root = _under_roots(target)
    if active_root is None:
        raise AppError(403, "Path not in allowed directories")
    if not target.exists() or not target.is_dir():
        raise AppError(404, "Directory not found")

    dirs = []
    try:
        for entry in sorted(target.iterdir()):
            if entry.is_dir() and not entry.name.startswith((".", "__")):
                dirs.append({"name": entry.name, "path": str(entry)})
    except PermissionError as exc:
        raise AppError(403, "Permission denied") from exc

    parent = "" if target == active_root else str(target.parent.resolve())
    return {"current": str(target), "parent": parent, "directories": dirs}


def mkdir(parent, name):
    parent = (parent or "").strip()
    name = (name or "").strip()
    if not parent or not name:
        raise AppError(400, "parent and name are required")
    if not re.match(r"^[a-zA-Z0-9_\-. ]+$", name) or ".." in name:
        raise AppError(400, "Invalid folder name")

    parent_path = Path(parent).resolve()
    if _under_roots(parent_path) is None:
        raise AppError(403, "Parent directory not in allowed directories")

    new_dir = parent_path / name
    if new_dir.exists():
        raise AppError(409, "Directory already exists")
    try:
        new_dir.mkdir(parents=False, exist_ok=False)
    except Exception as exc:
        raise AppError(500, "Failed to create directory") from exc

    return {"created": True, "path": str(new_dir)}


def history_list(agent=None, limit=50, offset=0):
    from corvustunnel.history.service import get_history_service

    return get_history_service().list_sessions(agent=agent, limit=limit, offset=offset)


def history_get(session_id, limit=200, offset=0):
    from corvustunnel.history.service import get_history_service

    result = get_history_service().get_session_messages(session_id, limit=limit, offset=offset)
    if "error" in result:
        raise AppError(404, result["error"])
    return result
