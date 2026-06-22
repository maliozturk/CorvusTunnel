# /*--------------------------------*- py -*-----------------------------*\
# | ___                 _____                  _                          |
# || _ \___ _ ___ ___ _|_   _|  _ _ _  _ _  ___| |                         |
# ||   / _ \ '_\ V / || || || || | ' \| ' \/ -_) |                         |
# ||_|_\___/_|  \_/ \_,_||_| \_,_|_||_|_||_\___|_|                         |
# |  CorvusTunnel  -  control AI agents from your phone  -  MIT            |
# *----------------------------------------------------------------------*/
# File:        corvustunnel/history/service.py
# Description: Discovers and serves agent chat sessions across
#              Antigravity, Claude, and Codex.
# \*---------------------------------------------------------------------*/

from __future__ import annotations

import logging
import time
from dataclasses import asdict

from corvustunnel.history.parsers import (
    AntigravityParser,
    ChatSession,
    ClaudeParser,
    CodexParser,
)

logger = logging.getLogger(__name__)

_CACHE_TTL = 60


class HistoryService:
    def __init__(self, custom_dirs: str | None = None):
        ag_dir = cl_dir = cx_dir = None

        if custom_dirs:
            for part in custom_dirs.split(","):
                part = part.strip()
                if "=" in part:
                    key, val = part.split("=", 1)
                    key = key.strip().lower()
                    val = val.strip()
                    if key == "antigravity":
                        ag_dir = val
                    elif key == "claude":
                        cl_dir = val
                    elif key == "codex":
                        cx_dir = val

        self._parsers = {
            "antigravity": AntigravityParser(base_dir=ag_dir),
            "claude": ClaudeParser(base_dir=cl_dir),
            "codex": CodexParser(base_dir=cx_dir),
        }

        self._session_cache: list[ChatSession] = []
        self._cache_time: float = 0

    def _refresh_cache(self) -> None:
        all_sessions: list[ChatSession] = []

        for agent_name, parser in self._parsers.items():
            try:
                sessions = parser.discover_sessions()
                all_sessions.extend(sessions)
                logger.info("Discovered %d %s sessions", len(sessions), agent_name)
            except Exception as e:
                logger.error("Error scanning %s sessions: %s", agent_name, e)

        all_sessions.sort(
            key=lambda s: s.started_at or "",
            reverse=True,
        )

        self._session_cache = all_sessions
        self._cache_time = time.monotonic()

    def _ensure_cache(self) -> None:
        if time.monotonic() - self._cache_time > _CACHE_TTL:
            self._refresh_cache()

    def list_sessions(
        self,
        agent: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        self._ensure_cache()

        sessions = self._session_cache
        if agent:
            sessions = [s for s in sessions if s.agent == agent]

        total = len(sessions)
        page = sessions[offset : offset + limit]

        return {
            "sessions": [asdict(s) for s in page],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def get_session_messages(
        self,
        session_id: str,
        limit: int = 200,
        offset: int = 0,
    ) -> dict:
        self._ensure_cache()

        session = None
        for s in self._session_cache:
            if s.id == session_id:
                session = s
                break

        if session is None:
            return {"error": "Session not found", "session_id": session_id}

        agent_key = session.agent
        parser = self._parsers.get(agent_key)
        if parser is None:
            return {"error": f"Unknown agent: {agent_key}"}

        try:
            all_messages = parser.load_messages(session)
        except Exception as e:
            logger.error("Error loading messages for %s: %s", session_id, e)
            return {"error": f"Failed to load messages: {e}"}

        total = len(all_messages)
        page = all_messages[offset : offset + limit]

        return {
            "session": asdict(session),
            "messages": [asdict(m) for m in page],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def get_stats(self) -> dict:
        self._ensure_cache()

        stats: dict[str, int] = {}
        for s in self._session_cache:
            stats[s.agent] = stats.get(s.agent, 0) + 1

        dates = [s.started_at for s in self._session_cache if s.started_at]
        oldest = min(dates) if dates else None
        newest = max(dates) if dates else None

        return {
            "total_sessions": len(self._session_cache),
            "by_agent": stats,
            "date_range": {
                "oldest": oldest,
                "newest": newest,
            },
        }

    def force_refresh(self) -> dict:
        self._cache_time = 0
        self._ensure_cache()
        return self.get_stats()


_service_instance: HistoryService | None = None


def get_history_service() -> HistoryService:
    global _service_instance
    if _service_instance is None:
        try:
            from corvustunnel.config.settings import get_settings

            settings = get_settings()
            custom_dirs = getattr(settings, "chat_history_dirs", "") or ""
        except Exception:
            custom_dirs = ""

        _service_instance = HistoryService(custom_dirs=custom_dirs or None)
    return _service_instance
