"""
Chat History Service — unified discovery and retrieval.

Aggregates sessions from all parsers, caches the index in memory,
and provides a clean API for the router layer.
"""

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

# Cache TTL in seconds (re-scan filesystem every 60s at most)
_CACHE_TTL = 60


class HistoryService:
    """High-level service for browsing chat histories."""

    def __init__(self, custom_dirs: str | None = None):
        """
        Args:
            custom_dirs: Comma-separated override paths in the format
                         "antigravity=/path,claude=/path,codex=/path".
                         If empty/None, auto-discovers from home dir.
        """
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

        # In-memory cache
        self._session_cache: list[ChatSession] = []
        self._cache_time: float = 0

    # ── Session Discovery ────────────────────────────────────────────

    def _refresh_cache(self) -> None:
        """Re-scan all parsers and rebuild the session index."""
        all_sessions: list[ChatSession] = []

        for agent_name, parser in self._parsers.items():
            try:
                sessions = parser.discover_sessions()
                all_sessions.extend(sessions)
                logger.info(
                    "Discovered %d %s sessions", len(sessions), agent_name
                )
            except Exception as e:
                logger.error("Error scanning %s sessions: %s", agent_name, e)

        # Sort by start time, newest first
        all_sessions.sort(
            key=lambda s: s.started_at or "",
            reverse=True,
        )

        self._session_cache = all_sessions
        self._cache_time = time.monotonic()

    def _ensure_cache(self) -> None:
        """Refresh cache if stale."""
        if time.monotonic() - self._cache_time > _CACHE_TTL:
            self._refresh_cache()

    # ── Public API ───────────────────────────────────────────────────

    def list_sessions(
        self,
        agent: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        """Return paginated session list.

        Args:
            agent: Filter by agent name (antigravity, claude, codex).
            limit: Max sessions to return.
            offset: Pagination offset.

        Returns:
            {"sessions": [...], "total": N, "limit": N, "offset": N}
        """
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
        """Load messages for a specific session.

        Args:
            session_id: Session ID in the format "agent:id".
            limit: Max messages to return.
            offset: Pagination offset.

        Returns:
            {"session": {...}, "messages": [...], "total": N}
        """
        self._ensure_cache()

        # Find session
        session = None
        for s in self._session_cache:
            if s.id == session_id:
                session = s
                break

        if session is None:
            return {"error": "Session not found", "session_id": session_id}

        # Determine which parser to use
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
        """Return quick stats about available sessions."""
        self._ensure_cache()

        stats: dict[str, int] = {}
        for s in self._session_cache:
            stats[s.agent] = stats.get(s.agent, 0) + 1

        # Date range
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
        """Force a cache refresh and return stats."""
        self._cache_time = 0
        self._ensure_cache()
        return self.get_stats()


# ── Singleton ────────────────────────────────────────────────────────

_service_instance: HistoryService | None = None


def get_history_service() -> HistoryService:
    """Return a singleton HistoryService instance."""
    global _service_instance
    if _service_instance is None:
        # Try to load custom dirs from settings
        try:
            from corvustunnel.config.settings import get_settings
            settings = get_settings()
            custom_dirs = getattr(settings, "chat_history_dirs", "") or ""
        except Exception:
            custom_dirs = ""

        _service_instance = HistoryService(custom_dirs=custom_dirs or None)
    return _service_instance
