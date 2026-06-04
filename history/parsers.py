"""
Chat History Parsers for Antigravity, Claude Code, and Codex.

Each parser scans its agent's data directory and produces a unified
schema (ChatSession / ChatMessage) so the rest of the app doesn't
need to know about per-agent JSONL quirks.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
#  Unified Data Model
# ══════════════════════════════════════════════════════════════════════

@dataclass
class ChatMessage:
    """A single message in a chat session."""
    role: str               # "user" | "assistant" | "system" | "tool"
    content: str            # text content (may contain markdown)
    timestamp: str | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class ChatSession:
    """Summary of a chat session (for the list view)."""
    id: str                      # unique session ID
    agent: str                   # "antigravity" | "claude" | "codex"
    project: str | None = None   # project/workspace path
    title: str | None = None     # auto-generated from first user msg
    started_at: str | None = None  # ISO timestamp
    message_count: int = 0
    preview: str = ""            # first ~200 chars of first user msg
    file_path: str = ""          # path to the JSONL file (for loading)


# ══════════════════════════════════════════════════════════════════════
#  Parser Protocol
# ══════════════════════════════════════════════════════════════════════

class HistoryParser(Protocol):
    """Interface for agent-specific parsers."""

    def discover_sessions(self) -> list[ChatSession]:
        """Scan for all available sessions."""
        ...

    def load_messages(self, session: ChatSession) -> list[ChatMessage]:
        """Load all messages for a given session."""
        ...


# ══════════════════════════════════════════════════════════════════════
#  Helpers
# ══════════════════════════════════════════════════════════════════════

def _safe_read_jsonl(path: str | Path, max_lines: int = 50_000) -> list[dict]:
    """Read a JSONL file, skipping malformed lines."""
    results = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f):
                if i >= max_lines:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    results.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except (OSError, PermissionError) as e:
        logger.warning("Failed to read %s: %s", path, e)
    return results


def _truncate(text: str, length: int = 200) -> str:
    """Truncate text to `length` characters with ellipsis."""
    if len(text) <= length:
        return text
    return text[:length].rstrip() + "…"


def _extract_text_content(content) -> str:
    """Extract plain text from various content formats.

    Handles:
      - str: returned as-is
      - list of dicts with 'text' key: joined
      - dict with 'text' key: returned
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text", "")
                if text:
                    parts.append(text)
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(parts)
    if isinstance(content, dict):
        return content.get("text", str(content))
    return str(content) if content else ""


# ══════════════════════════════════════════════════════════════════════
#  Antigravity Parser
# ══════════════════════════════════════════════════════════════════════

class AntigravityParser:
    """Parse Antigravity (Gemini) chat history.

    Directory structure:
        ~/.gemini/antigravity-ide/brain/{conv-id}/
            .system_generated/logs/transcript.jsonl

    JSONL schema:
        {"step_index": 0, "source": "USER_EXPLICIT", "type": "USER_INPUT",
         "content": "...", "created_at": "2026-06-04T18:12:27Z"}
    """

    # Map source/type to role
    _ROLE_MAP = {
        "USER_EXPLICIT": "user",
        "USER_IMPLICIT": "user",
        "MODEL": "assistant",
        "SYSTEM": "system",
    }

    _SKIP_TYPES = {
        "CONVERSATION_HISTORY",
        "KNOWLEDGE_ARTIFACTS",
    }

    def __init__(self, base_dir: str | None = None):
        if base_dir:
            self.base_dir = Path(base_dir)
        else:
            home = Path.home()
            self.base_dir = home / ".gemini" / "antigravity-ide" / "brain"

    def discover_sessions(self) -> list[ChatSession]:
        """Scan for all Antigravity conversation directories."""
        sessions = []
        if not self.base_dir.exists():
            return sessions

        for entry in self.base_dir.iterdir():
            if not entry.is_dir() or entry.name == "tempmediaStorage":
                continue

            transcript = entry / ".system_generated" / "logs" / "transcript.jsonl"
            if not transcript.exists():
                continue

            session = self._build_session_summary(entry.name, transcript)
            if session:
                sessions.append(session)

        return sessions

    def _build_session_summary(
        self, conv_id: str, transcript_path: Path
    ) -> ChatSession | None:
        """Build a session summary by reading the first few lines."""
        lines = _safe_read_jsonl(transcript_path, max_lines=30)
        if not lines:
            return None

        # Find first user message for preview/title
        first_user_msg = ""
        started_at = None
        msg_count = 0

        for line in lines:
            ts = line.get("created_at")
            if started_at is None and ts:
                started_at = ts

            source = line.get("source", "")
            line_type = line.get("type", "")

            if line_type in self._SKIP_TYPES:
                continue

            if source in self._ROLE_MAP:
                msg_count += 1
                if source in ("USER_EXPLICIT", "USER_IMPLICIT") and not first_user_msg:
                    content = line.get("content", "")
                    # Strip XML tags from user requests
                    content = re.sub(r"<[^>]+>", "", content).strip()
                    # Take first meaningful line
                    for cl in content.split("\n"):
                        cl = cl.strip()
                        if cl and len(cl) > 5:
                            first_user_msg = cl
                            break

        # Count total messages (read whole file for accurate count)
        try:
            with open(transcript_path, "r", encoding="utf-8", errors="replace") as f:
                total_lines = sum(
                    1 for ln in f
                    if ln.strip() and '"source"' in ln
                    and '"CONVERSATION_HISTORY"' not in ln
                    and '"KNOWLEDGE_ARTIFACTS"' not in ln
                )
        except OSError:
            total_lines = msg_count

        return ChatSession(
            id=f"antigravity:{conv_id}",
            agent="antigravity",
            project=None,  # Antigravity doesn't embed project path reliably
            title=_truncate(first_user_msg, 100) if first_user_msg else f"Session {conv_id[:8]}",
            started_at=started_at,
            message_count=total_lines,
            preview=_truncate(first_user_msg) if first_user_msg else "",
            file_path=str(transcript_path),
        )

    def load_messages(self, session: ChatSession) -> list[ChatMessage]:
        """Load all messages from a transcript."""
        lines = _safe_read_jsonl(session.file_path)
        messages = []

        for line in lines:
            source = line.get("source", "")
            line_type = line.get("type", "")

            if line_type in self._SKIP_TYPES:
                continue

            role = self._ROLE_MAP.get(source)
            if not role:
                continue

            content = line.get("content", "")
            if not content:
                continue

            # Clean up user messages (strip XML wrapper tags)
            if role == "user":
                # Extract content from <USER_REQUEST> tags if present
                match = re.search(
                    r"<USER_REQUEST>\s*(.*?)\s*</USER_REQUEST>",
                    content,
                    re.DOTALL,
                )
                if match:
                    content = match.group(1).strip()

            messages.append(ChatMessage(
                role=role,
                content=content,
                timestamp=line.get("created_at"),
                metadata={
                    "step_index": line.get("step_index"),
                    "type": line_type,
                },
            ))

        return messages


# ══════════════════════════════════════════════════════════════════════
#  Claude Code Parser
# ══════════════════════════════════════════════════════════════════════

class ClaudeParser:
    """Parse Claude Code chat history.

    Directory structure:
        ~/.claude/projects/{project-slug}/
            {session-id}.jsonl      — per-session messages

        ~/.claude/history.jsonl     — user input timeline (optional)

    JSONL schema (session files):
        {"type": "user", "message": {"role": "user", "content": "hi"},
         "timestamp": "...", "sessionId": "...", "cwd": "..."}
        {"type": "assistant", "message": {"role": "assistant",
         "content": [{"type": "text", "text": "..."}]},
         "timestamp": "...", "sessionId": "..."}
    """

    # Message types that carry actual conversation content
    _CONTENT_TYPES = {"user", "assistant"}

    # Skip meta/internal message types
    _SKIP_TYPES = {"mode", "permission-mode", "file-history-snapshot"}

    def __init__(self, base_dir: str | None = None):
        if base_dir:
            self.base_dir = Path(base_dir)
        else:
            self.base_dir = Path.home() / ".claude"

    def discover_sessions(self) -> list[ChatSession]:
        """Scan for all Claude Code sessions across projects."""
        sessions = []
        projects_dir = self.base_dir / "projects"
        if not projects_dir.exists():
            return sessions

        for project_dir in projects_dir.iterdir():
            if not project_dir.is_dir():
                continue

            # Decode project path from slug (C--Users-alini-foo → C:\Users\alini\foo)
            project_path = self._decode_project_slug(project_dir.name)

            for jsonl_file in project_dir.glob("*.jsonl"):
                session = self._build_session_summary(
                    jsonl_file, project_path, project_dir.name
                )
                if session:
                    sessions.append(session)

        return sessions

    @staticmethod
    def _decode_project_slug(slug: str) -> str:
        """Convert Claude's project slug back to a path.

        e.g. 'C--Users-alini-phdworks-CorvusTunnel' → 'C:\\Users\\alini\\phdworks\\CorvusTunnel'
        """
        # First char is drive letter, then -- is :\, then - is \
        if len(slug) >= 3 and slug[1:3] == "--":
            path = slug[0] + ":\\" + slug[3:].replace("-", "\\")
            return path
        return slug.replace("-", "/")

    def _build_session_summary(
        self, jsonl_path: Path, project_path: str, project_slug: str
    ) -> ChatSession | None:
        """Build a session summary from first few messages."""
        session_id = jsonl_path.stem
        lines = _safe_read_jsonl(jsonl_path, max_lines=30)
        if not lines:
            return None

        first_user_msg = ""
        started_at = None
        msg_count = 0

        for line in lines:
            msg_type = line.get("type", "")

            if msg_type in self._SKIP_TYPES:
                continue

            ts = line.get("timestamp")
            if started_at is None and ts:
                started_at = ts

            if msg_type in self._CONTENT_TYPES:
                msg_count += 1
                message = line.get("message", {})
                content = message.get("content", "")

                if msg_type == "user" and not first_user_msg:
                    text = _extract_text_content(content)
                    # Skip meta messages
                    if text and not text.startswith("<local-command"):
                        # Strip XML tags
                        text = re.sub(r"<[^>]+>", "", text).strip()
                        for cl in text.split("\n"):
                            cl = cl.strip()
                            if cl and len(cl) > 3:
                                first_user_msg = cl
                                break

        # Count total content messages
        try:
            with open(jsonl_path, "r", encoding="utf-8", errors="replace") as f:
                total = sum(
                    1 for ln in f
                    if ln.strip()
                    and ('"type":"user"' in ln.replace(" ", "")
                         or '"type":"assistant"' in ln.replace(" ", ""))
                )
        except OSError:
            total = msg_count

        if total == 0:
            return None

        # Extract short project name
        project_name = project_path.rsplit("\\", 1)[-1] if "\\" in project_path else project_path.rsplit("/", 1)[-1]

        return ChatSession(
            id=f"claude:{session_id}",
            agent="claude",
            project=project_path,
            title=_truncate(first_user_msg, 100) if first_user_msg else f"Claude session in {project_name}",
            started_at=started_at,
            message_count=total,
            preview=_truncate(first_user_msg) if first_user_msg else "",
            file_path=str(jsonl_path),
        )

    def load_messages(self, session: ChatSession) -> list[ChatMessage]:
        """Load all messages from a Claude session file."""
        lines = _safe_read_jsonl(session.file_path)
        messages = []

        for line in lines:
            msg_type = line.get("type", "")
            if msg_type not in self._CONTENT_TYPES:
                continue

            message = line.get("message", {})
            role = message.get("role", msg_type)
            content_raw = message.get("content", "")
            content = _extract_text_content(content_raw)

            if not content:
                continue

            # Skip meta/command messages
            is_meta = line.get("isMeta", False)
            if is_meta:
                continue
            if content.startswith("<local-command") or content.startswith("<command-name"):
                continue

            messages.append(ChatMessage(
                role=role,
                content=content,
                timestamp=line.get("timestamp"),
                metadata={
                    k: v for k, v in {
                        "model": message.get("model"),
                        "sessionId": line.get("sessionId"),
                        "stop_reason": message.get("stop_reason"),
                    }.items() if v is not None
                },
            ))

        return messages


# ══════════════════════════════════════════════════════════════════════
#  Codex Parser
# ══════════════════════════════════════════════════════════════════════

class CodexParser:
    """Parse Codex (OpenAI) chat history.

    Directory structure:
        ~/.codex/sessions/{year}/{month}/{day}/
            rollout-{timestamp}-{id}.jsonl

    JSONL schema:
        {"timestamp": "...", "type": "response_item",
         "payload": {"type": "message", "role": "user",
                     "content": [{"type": "input_text", "text": "..."}]}}
    """

    def __init__(self, base_dir: str | None = None):
        if base_dir:
            self.base_dir = Path(base_dir)
        else:
            self.base_dir = Path.home() / ".codex"

    def discover_sessions(self) -> list[ChatSession]:
        """Scan for all Codex rollout sessions."""
        sessions = []
        sessions_dir = self.base_dir / "sessions"
        if not sessions_dir.exists():
            return sessions

        # Walk year/month/day directories
        for jsonl_file in sessions_dir.rglob("rollout-*.jsonl"):
            session = self._build_session_summary(jsonl_file)
            if session:
                sessions.append(session)

        return sessions

    def _build_session_summary(self, jsonl_path: Path) -> ChatSession | None:
        """Build a session summary from a rollout file."""
        # Extract session ID and timestamp from filename
        # Format: rollout-2026-05-19T21-30-32-{uuid}.jsonl
        name = jsonl_path.stem  # rollout-2026-05-19T21-30-32-019e4180-...
        parts = name.split("-", 7)  # rollout, year, month, dayThh, mm, ss, uuid...

        lines = _safe_read_jsonl(jsonl_path, max_lines=50)
        if not lines:
            return None

        first_user_msg = ""
        started_at = None
        project_path = None
        msg_count = 0

        for line in lines:
            ts = line.get("timestamp")
            if started_at is None and ts:
                started_at = ts

            line_type = line.get("type", "")

            # Extract project from turn_context
            if line_type == "turn_context":
                payload = line.get("payload", {})
                cwd = payload.get("cwd")
                if cwd and not project_path:
                    project_path = cwd

            if line_type == "response_item":
                payload = line.get("payload", {})
                payload_type = payload.get("type", "")
                role = payload.get("role", "")

                if payload_type == "message" and role in ("user", "assistant"):
                    msg_count += 1
                    content_list = payload.get("content", [])
                    text = _extract_text_content(content_list)

                    if role == "user" and not first_user_msg:
                        # Skip system/environment context messages
                        if text and not text.startswith("<environment_context"):
                            # Strip XML tags
                            clean = re.sub(r"<[^>]+>", "", text).strip()
                            for cl in clean.split("\n"):
                                cl = cl.strip()
                                if cl and len(cl) > 5:
                                    first_user_msg = cl
                                    break

        # Count total messages in file
        try:
            with open(jsonl_path, "r", encoding="utf-8", errors="replace") as f:
                total = sum(
                    1 for ln in f
                    if ln.strip() and '"response_item"' in ln
                    and '"message"' in ln
                )
        except OSError:
            total = msg_count

        if total == 0:
            return None

        # Build a readable session ID from the filename
        session_id = name.replace("rollout-", "")

        # Extract project name
        project_name = ""
        if project_path:
            project_name = project_path.rsplit("\\", 1)[-1] if "\\" in project_path else project_path.rsplit("/", 1)[-1]

        return ChatSession(
            id=f"codex:{session_id}",
            agent="codex",
            project=project_path,
            title=_truncate(first_user_msg, 100) if first_user_msg else (
                f"Codex session in {project_name}" if project_name else f"Codex {session_id[:20]}"
            ),
            started_at=started_at,
            message_count=total,
            preview=_truncate(first_user_msg) if first_user_msg else "",
            file_path=str(jsonl_path),
        )

    def load_messages(self, session: ChatSession) -> list[ChatMessage]:
        """Load all messages from a Codex rollout file."""
        lines = _safe_read_jsonl(session.file_path)
        messages = []

        for line in lines:
            line_type = line.get("type", "")
            if line_type != "response_item":
                continue

            payload = line.get("payload", {})
            if payload.get("type") != "message":
                continue

            role = payload.get("role", "")
            if role not in ("user", "assistant"):
                continue

            content_list = payload.get("content", [])
            content = _extract_text_content(content_list)

            if not content:
                continue

            # Skip environment/system context messages
            if role == "user" and content.strip().startswith("<environment_context"):
                continue
            # Skip giant system prompts
            if role == "user" and "<skills_instructions>" in content:
                continue
            if role == "user" and "<plugins_instructions>" in content:
                continue

            messages.append(ChatMessage(
                role=role,
                content=content,
                timestamp=line.get("timestamp"),
                metadata={
                    "model": payload.get("model"),
                },
            ))

        return messages
