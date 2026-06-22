# /*--------------------------------*- py -*-----------------------------*\
# | ___                 _____                  _                          |
# || _ \___ _ ___ ___ _|_   _|  _ _ _  _ _  ___| |                         |
# ||   / _ \ '_\ V / || || || || | ' \| ' \/ -_) |                         |
# ||_|_\___/_|  \_/ \_,_||_| \_,_|_||_|_||_\___|_|                         |
# |  CorvusTunnel  -  control AI agents from your phone  -  MIT            |
# *----------------------------------------------------------------------*/
# File:        corvustunnel/history/parsers.py
# Description: Parsers that read each agent's on-disk session format.
# \*---------------------------------------------------------------------*/

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

logger = logging.getLogger(__name__)


@dataclass
class ChatMessage:
    role: str
    content: str
    timestamp: str | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class ChatSession:
    id: str
    agent: str
    project: str | None = None
    title: str | None = None
    started_at: str | None = None
    message_count: int = 0
    preview: str = ""
    file_path: str = ""


class HistoryParser(Protocol):
    def discover_sessions(self) -> list[ChatSession]: ...

    def load_messages(self, session: ChatSession) -> list[ChatMessage]: ...


def _safe_read_jsonl(path: str | Path, max_lines: int = 50_000) -> list[dict]:
    results = []
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
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
    if len(text) <= length:
        return text
    return text[:length].rstrip() + "…"


def _extract_text_content(content) -> str:
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


class AntigravityParser:
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

    def _build_session_summary(self, conv_id: str, transcript_path: Path) -> ChatSession | None:
        lines = _safe_read_jsonl(transcript_path, max_lines=30)
        if not lines:
            return None

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
                    content = re.sub(r"<[^>]+>", "", content).strip()
                    for cl in content.split("\n"):
                        cl = cl.strip()
                        if cl and len(cl) > 5:
                            first_user_msg = cl
                            break

        try:
            with open(transcript_path, encoding="utf-8", errors="replace") as f:
                total_lines = sum(
                    1
                    for ln in f
                    if ln.strip()
                    and '"source"' in ln
                    and '"CONVERSATION_HISTORY"' not in ln
                    and '"KNOWLEDGE_ARTIFACTS"' not in ln
                )
        except OSError:
            total_lines = msg_count

        return ChatSession(
            id=f"antigravity:{conv_id}",
            agent="antigravity",
            project=None,
            title=_truncate(first_user_msg, 100) if first_user_msg else f"Session {conv_id[:8]}",
            started_at=started_at,
            message_count=total_lines,
            preview=_truncate(first_user_msg) if first_user_msg else "",
            file_path=str(transcript_path),
        )

    def load_messages(self, session: ChatSession) -> list[ChatMessage]:
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

            if role == "user":
                match = re.search(
                    r"<USER_REQUEST>\s*(.*?)\s*</USER_REQUEST>",
                    content,
                    re.DOTALL,
                )
                if match:
                    content = match.group(1).strip()

            messages.append(
                ChatMessage(
                    role=role,
                    content=content,
                    timestamp=line.get("created_at"),
                    metadata={
                        "step_index": line.get("step_index"),
                        "type": line_type,
                    },
                )
            )

        return messages


class ClaudeParser:
    _CONTENT_TYPES = {"user", "assistant"}

    _SKIP_TYPES = {"mode", "permission-mode", "file-history-snapshot"}

    def __init__(self, base_dir: str | None = None):
        if base_dir:
            self.base_dir = Path(base_dir)
        else:
            self.base_dir = Path.home() / ".claude"

    def discover_sessions(self) -> list[ChatSession]:
        sessions = []
        projects_dir = self.base_dir / "projects"
        if not projects_dir.exists():
            return sessions

        for project_dir in projects_dir.iterdir():
            if not project_dir.is_dir():
                continue

            project_path = self._decode_project_slug(project_dir.name)

            for jsonl_file in project_dir.glob("*.jsonl"):
                session = self._build_session_summary(jsonl_file, project_path, project_dir.name)
                if session:
                    sessions.append(session)

        return sessions

    @staticmethod
    def _decode_project_slug(slug: str) -> str:
        if len(slug) >= 3 and slug[1:3] == "--":
            path = slug[0] + ":\\" + slug[3:].replace("-", "\\")
            return path
        return slug.replace("-", "/")

    def _build_session_summary(
        self, jsonl_path: Path, project_path: str, project_slug: str
    ) -> ChatSession | None:
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
                    if text and not text.startswith("<local-command"):
                        text = re.sub(r"<[^>]+>", "", text).strip()
                        for cl in text.split("\n"):
                            cl = cl.strip()
                            if cl and len(cl) > 3:
                                first_user_msg = cl
                                break

        try:
            with open(jsonl_path, encoding="utf-8", errors="replace") as f:
                total = sum(
                    1
                    for ln in f
                    if ln.strip()
                    and (
                        '"type":"user"' in ln.replace(" ", "")
                        or '"type":"assistant"' in ln.replace(" ", "")
                    )
                )
        except OSError:
            total = msg_count

        if total == 0:
            return None

        project_name = (
            project_path.rsplit("\\", 1)[-1]
            if "\\" in project_path
            else project_path.rsplit("/", 1)[-1]
        )

        return ChatSession(
            id=f"claude:{session_id}",
            agent="claude",
            project=project_path,
            title=_truncate(first_user_msg, 100)
            if first_user_msg
            else f"Claude session in {project_name}",
            started_at=started_at,
            message_count=total,
            preview=_truncate(first_user_msg) if first_user_msg else "",
            file_path=str(jsonl_path),
        )

    def load_messages(self, session: ChatSession) -> list[ChatMessage]:
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

            is_meta = line.get("isMeta", False)
            if is_meta:
                continue
            if content.startswith("<local-command") or content.startswith("<command-name"):
                continue

            messages.append(
                ChatMessage(
                    role=role,
                    content=content,
                    timestamp=line.get("timestamp"),
                    metadata={
                        k: v
                        for k, v in {
                            "model": message.get("model"),
                            "sessionId": line.get("sessionId"),
                            "stop_reason": message.get("stop_reason"),
                        }.items()
                        if v is not None
                    },
                )
            )

        return messages


class CodexParser:
    def __init__(self, base_dir: str | None = None):
        if base_dir:
            self.base_dir = Path(base_dir)
        else:
            self.base_dir = Path.home() / ".codex"

    def discover_sessions(self) -> list[ChatSession]:
        sessions = []
        sessions_dir = self.base_dir / "sessions"
        if not sessions_dir.exists():
            return sessions

        for jsonl_file in sessions_dir.rglob("rollout-*.jsonl"):
            session = self._build_session_summary(jsonl_file)
            if session:
                sessions.append(session)

        return sessions

    def _build_session_summary(self, jsonl_path: Path) -> ChatSession | None:
        name = jsonl_path.stem
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
                        if text and not text.startswith("<environment_context"):
                            clean = re.sub(r"<[^>]+>", "", text).strip()
                            for cl in clean.split("\n"):
                                cl = cl.strip()
                                if cl and len(cl) > 5:
                                    first_user_msg = cl
                                    break

        try:
            with open(jsonl_path, encoding="utf-8", errors="replace") as f:
                total = sum(
                    1 for ln in f if ln.strip() and '"response_item"' in ln and '"message"' in ln
                )
        except OSError:
            total = msg_count

        if total == 0:
            return None

        session_id = name.replace("rollout-", "")

        project_name = ""
        if project_path:
            project_name = (
                project_path.rsplit("\\", 1)[-1]
                if "\\" in project_path
                else project_path.rsplit("/", 1)[-1]
            )

        return ChatSession(
            id=f"codex:{session_id}",
            agent="codex",
            project=project_path,
            title=_truncate(first_user_msg, 100)
            if first_user_msg
            else (
                f"Codex session in {project_name}" if project_name else f"Codex {session_id[:20]}"
            ),
            started_at=started_at,
            message_count=total,
            preview=_truncate(first_user_msg) if first_user_msg else "",
            file_path=str(jsonl_path),
        )

    def load_messages(self, session: ChatSession) -> list[ChatMessage]:
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

            if role == "user" and content.strip().startswith("<environment_context"):
                continue
            if role == "user" and "<skills_instructions>" in content:
                continue
            if role == "user" and "<plugins_instructions>" in content:
                continue

            messages.append(
                ChatMessage(
                    role=role,
                    content=content,
                    timestamp=line.get("timestamp"),
                    metadata={
                        "model": payload.get("model"),
                    },
                )
            )

        return messages
