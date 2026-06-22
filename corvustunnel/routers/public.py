# /*--------------------------------*- py -*-----------------------------*\
# | ___                 _____                  _                          |
# || _ \___ _ ___ ___ _|_   _|  _ _ _  _ _  ___| |                         |
# ||   / _ \ '_\ V / || || || || | ' \| ' \/ -_) |                         |
# ||_|_\___/_|  \_/ \_,_||_| \_,_|_||_|_||_\___|_|                         |
# |  CorvusTunnel  -  control AI agents from your phone  -  MIT            |
# *----------------------------------------------------------------------*/
# File:        corvustunnel/routers/public.py
# Description: Public REST and WebSocket API: auth, E2E key exchange,
#              browse, history, and the interactive terminal stream.
# \*---------------------------------------------------------------------*/

from __future__ import annotations

import asyncio
import json
import logging
import shutil
import time
from collections import defaultdict

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from pydantic import BaseModel

from corvustunnel.audit.logger import get_audit_logger
from corvustunnel.auth.dependencies import require_public_auth
from corvustunnel.middleware.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

_start_time = time.time()

_ws_connections: dict[str, int] = defaultdict(int)
_ws_lock = asyncio.Lock()
MAX_WS_PER_IP = 3


class HealthResponse(BaseModel):
    status: str
    version: str
    uptime_seconds: float


@router.get("/health", response_model=HealthResponse)
@limiter.limit("30/minute")
async def health(request: Request):
    from corvustunnel.version import __version__

    return HealthResponse(
        status="ok",
        version=__version__,
        uptime_seconds=round(time.time() - _start_time, 1),
    )


@router.post("/e2e/exchange")
@limiter.limit("10/minute")
async def e2e_key_exchange(request: Request):
    from corvustunnel.crypto.e2e import get_e2e_crypto

    crypto = get_e2e_crypto()
    if not crypto.available:
        raise HTTPException(
            501, "E2E encryption not available — install PyNaCl: pip install PyNaCl"
        )

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "Invalid request body")

    client_key = body.get("client_public_key", "")
    session_id = body.get("session_id", "")

    if not client_key or not session_id:
        raise HTTPException(400, "client_public_key and session_id are required")

    try:
        server_key = crypto.exchange(session_id, client_key)
    except ValueError as e:
        raise HTTPException(400, str(e))

    get_audit_logger().log(
        "e2e_key_exchange",
        client_ip=_get_client_ip(request),
        session_id=session_id,
    )

    return {
        "server_public_key": server_key,
        "e2e_enabled": True,
    }


@router.post("/claim")
@limiter.limit("5/minute")
async def claim_token(request: Request):
    from corvustunnel.audit.deep_logger import get_deep_logger
    from corvustunnel.auth.bearer import get_token_manager
    from corvustunnel.middleware.ip_ban import get_ban_tracker

    deep = get_deep_logger()
    ban_tracker = get_ban_tracker()
    client_ip = _get_client_ip(request)

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "Invalid request body")

    boot_token = body.get("token", "")
    if not boot_token:
        raise HTTPException(400, "token is required")

    manager = get_token_manager()
    session_token = manager.claim_boot_token(boot_token, client_ip=client_ip)

    if session_token is None:
        ban_tracker.record_failure(client_ip)
        deep.log(
            "claim_rejected",
            category="auth",
            client_ip=client_ip,
            reason="Invalid or already consumed boot token",
        )
        raise HTTPException(401, "Invalid or already consumed token")

    deep.log(
        "claim_success",
        category="auth",
        client_ip=client_ip,
    )

    return {"session_token": session_token}


@router.get("/browse", dependencies=[Depends(require_public_auth)])
@limiter.limit("60/minute")
async def browse_directory(request: Request, path: str = Query(default=None)):
    from pathlib import Path as P

    from corvustunnel.audit.deep_logger import get_deep_logger
    from corvustunnel.config.settings import get_settings

    deep = get_deep_logger()
    client_ip = _get_client_ip(request)

    settings = get_settings()
    roots = [P(d).resolve() for d in settings.allowed_dir_list]

    if not roots:
        raise HTTPException(400, "No allowed directories configured — set ALLOWED_DIRS")

    if path is None:
        dirs = []
        for r in roots:
            if r.exists() and r.is_dir():
                dirs.append({"name": r.name, "path": str(r)})
        deep.browse(client_ip, path=None, result_count=len(dirs))
        return {"current": "Projects", "parent": None, "directories": dirs}

    target = P(path).resolve()

    active_root = None
    for root in roots:
        try:
            target.relative_to(root)
            active_root = root
            break
        except ValueError:
            continue

    if active_root is None:
        deep.browse_blocked(client_ip, path, "Path not in allowed directories")
        raise HTTPException(403, "Path not in allowed directories")

    if not target.exists() or not target.is_dir():
        raise HTTPException(404, "Directory not found")

    dirs = []
    try:
        for entry in sorted(target.iterdir()):
            if (
                entry.is_dir()
                and not entry.name.startswith(".")
                and not entry.name.startswith("__")
            ):
                dirs.append({"name": entry.name, "path": str(entry)})
    except PermissionError:
        raise HTTPException(403, "Permission denied")

    parent = "" if target == active_root else str(target.parent.resolve())

    deep.browse(client_ip, path, result_count=len(dirs))
    return {"current": str(target), "parent": parent, "directories": dirs}


@router.get("/check-agents", dependencies=[Depends(require_public_auth)])
@limiter.limit("20/minute")
async def check_agents(request: Request):
    import os
    from pathlib import Path

    from corvustunnel.config.settings import get_settings

    agy_path = shutil.which("agy")
    codex_path = shutil.which("codex")
    claude_path = shutil.which("claude")

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
            {"name": "agy", "available": agy_path is not None, "path": agy_path},
            {"name": "codex", "available": codex_path is not None, "path": codex_path},
            {"name": "claude", "available": claude_path is not None, "path": claude_path},
        ],
        "default_work_dir": str(Path(default_dir).resolve()),
    }


@router.post("/browse/mkdir", dependencies=[Depends(require_public_auth)])
@limiter.limit("10/minute")
async def create_directory(request: Request):
    import re
    from pathlib import Path as P

    from corvustunnel.audit.deep_logger import get_deep_logger
    from corvustunnel.config.settings import get_settings

    body = await request.json()
    parent = body.get("parent", "")
    name = body.get("name", "").strip()

    if not parent or not name:
        raise HTTPException(400, "parent and name are required")

    if not re.match(r"^[a-zA-Z0-9_\-. ]+$", name):
        raise HTTPException(
            400,
            "Invalid folder name — only letters, numbers, dashes, "
            "underscores, dots, and spaces allowed",
        )

    if ".." in name:
        raise HTTPException(400, "Invalid folder name")

    settings = get_settings()
    roots = [P(d).resolve() for d in settings.allowed_dir_list]
    parent_path = P(parent).resolve()

    allowed = False
    for root in roots:
        try:
            parent_path.relative_to(root)
            allowed = True
            break
        except ValueError:
            continue

    if not allowed:
        raise HTTPException(403, "Parent directory not in allowed directories")

    new_dir = parent_path / name
    if new_dir.exists():
        raise HTTPException(409, "Directory already exists")

    try:
        new_dir.mkdir(parents=False, exist_ok=False)
    except Exception:
        raise HTTPException(500, "Failed to create directory")

    deep = get_deep_logger()
    deep.log(
        "directory_created",
        category="browse",
        parent=str(parent_path),
        name=name,
        path=str(new_dir),
    )

    return {"created": True, "path": str(new_dir)}


@router.get("/history/sessions", dependencies=[Depends(require_public_auth)])
@limiter.limit("30/minute")
async def list_history_sessions(
    request: Request,
    agent: str | None = Query(
        default=None, description="Filter by agent: antigravity, claude, codex"
    ),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    from corvustunnel.history.service import get_history_service

    service = get_history_service()
    return service.list_sessions(agent=agent, limit=limit, offset=offset)


@router.get("/history/sessions/{session_id:path}", dependencies=[Depends(require_public_auth)])
@limiter.limit("30/minute")
async def get_history_session(
    request: Request,
    session_id: str,
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    from corvustunnel.history.service import get_history_service

    service = get_history_service()
    result = service.get_session_messages(session_id, limit=limit, offset=offset)
    if "error" in result:
        raise HTTPException(404, result["error"])
    return result


@router.get("/history/stats", dependencies=[Depends(require_public_auth)])
@limiter.limit("30/minute")
async def history_stats(request: Request):
    from corvustunnel.history.service import get_history_service

    service = get_history_service()
    return service.get_stats()


@router.post("/ws-ticket", dependencies=[Depends(require_public_auth)])
@limiter.limit("10/minute")
async def create_ws_ticket(request: Request):
    from corvustunnel.auth.bearer import get_token_manager

    client_ip = _get_client_ip(request)
    manager = get_token_manager()
    ticket = manager.create_ws_ticket(client_ip)

    return {"ticket": ticket}


def _validate_work_dir(work_dir: str) -> bool:
    from pathlib import Path

    from corvustunnel.config.settings import get_settings

    settings = get_settings()
    roots = [Path(d).resolve() for d in settings.allowed_dir_list]
    if not roots:
        return False
    target = Path(work_dir).resolve()
    return any(target == root or target.is_relative_to(root) for root in roots)


def _get_client_ip(request) -> str:
    from corvustunnel.middleware.client_ip import get_trusted_client_ip

    return get_trusted_client_ip(request)


@router.get("/terminal/status", dependencies=[Depends(require_public_auth)])
@limiter.limit("30/minute")
async def terminal_status(request: Request):
    from corvustunnel.executor.term_session import get_terminal_session

    session = get_terminal_session()
    return {
        "alive": session.is_alive,
        "work_dir": session.work_dir if session.is_alive else None,
    }


@router.websocket("/terminal/ws")
async def terminal_ws(
    websocket: WebSocket,
    ticket: str = Query(""),
    work_dir: str = Query(""),
    flags: str = Query(""),
    agent: str = Query("agy"),
    session_id: str = Query(""),
):
    from corvustunnel.audit.deep_logger import get_deep_logger
    from corvustunnel.auth.bearer import get_token_manager
    from corvustunnel.crypto.e2e import get_e2e_crypto
    from corvustunnel.executor.term_session import get_terminal_session
    from corvustunnel.middleware.ip_ban import get_ban_tracker

    deep = get_deep_logger()
    ban_tracker = get_ban_tracker()
    crypto = get_e2e_crypto()

    from corvustunnel.middleware.client_ip import get_trusted_client_ip

    client_ip = get_trusted_client_ip(websocket)

    if ban_tracker.is_banned(client_ip):
        await websocket.close(code=4403, reason="Temporarily banned")
        return

    manager = get_token_manager()
    if not ticket or not manager.consume_ws_ticket(ticket, client_ip):
        ban_tracker.record_failure(client_ip)
        deep.log(
            "terminal_ws_auth_fail",
            category="terminal",
            reason="Invalid or expired ticket",
            client_ip=client_ip,
        )
        await websocket.close(code=4001, reason="Unauthorized")
        return

    async with _ws_lock:
        if _ws_connections[client_ip] >= MAX_WS_PER_IP:
            await websocket.close(code=4429, reason="Too many connections")
            return
        _ws_connections[client_ip] += 1

    try:
        if not work_dir:
            await websocket.close(code=4003, reason="work_dir is required")
            return

        if not _validate_work_dir(work_dir):
            deep.log(
                "terminal_ws_blocked",
                category="terminal",
                work_dir=work_dir,
                reason="Not in ALLOWED_DIRS",
            )
            await websocket.close(code=4003, reason="work_dir not allowed")
            return

        ALLOWED_AGENTS = {"agy", "codex", "claude"}
        if agent not in ALLOWED_AGENTS:
            await websocket.close(code=4003, reason=f"Unknown agent: {agent}")
            return
        if not shutil.which(agent):
            await websocket.close(code=4003, reason=f"{agent} not found on PATH")
            return

        await websocket.accept()

        e2e_on = bool(session_id) and crypto.has_session(session_id)

        async def send_msg(msg: dict) -> None:
            if e2e_on:
                await websocket.send_text(crypto.encrypt(session_id, json.dumps(msg)))
            else:
                await websocket.send_json(msg)

        def decode_msg(raw: str) -> dict | None:
            try:
                if e2e_on:
                    raw = crypto.decrypt(session_id, raw)
                return json.loads(raw)
            except (json.JSONDecodeError, TypeError, KeyError, ValueError):
                return None

        logger.info(
            "Terminal WebSocket connected (agent=%s, work_dir=%s, ip=%s, e2e=%s)",
            agent,
            work_dir,
            client_ip,
            e2e_on,
        )
        deep.log(
            "terminal_ws_connected",
            category="terminal",
            work_dir=work_dir,
            client_ip=client_ip,
            e2e=e2e_on,
        )

        session = get_terminal_session()

        if session.is_alive and (session.work_dir != work_dir or session.command != agent):
            logger.info(
                "Switching terminal: %s(%s) → %s(%s)",
                session.command,
                session.work_dir,
                agent,
                work_dir,
            )
            session.stop()

        if not session.is_alive:
            flag_list = [f.strip() for f in flags.split(",") if f.strip()] if flags else None
            ALLOWED_FLAGS = {"--dangerously-skip-permissions"}
            if flag_list:
                flag_list = [f for f in flag_list if f in ALLOWED_FLAGS]
            session.start(work_dir, command=agent, flags=flag_list if flag_list else None)

        queue, replay_text = session.subscribe()

        try:
            if replay_text:
                await send_msg({"type": "replay", "data": replay_text})

            _input_tokens = 100.0
            _input_max = 100.0
            _input_rate = 100.0
            _input_last = time.monotonic()
            _input_flood_count = 0
            _input_flood_window = time.monotonic()

            async def ws_to_pty():
                nonlocal \
                    _input_tokens, \
                    _input_last, \
                    _input_flood_count, \
                    _input_flood_window, \
                    _last_client_activity

                while True:
                    try:
                        raw = await websocket.receive_text()
                    except WebSocketDisconnect:
                        return

                    msg = decode_msg(raw)
                    if msg is None:
                        continue

                    msg_type = msg.get("type", "")
                    _last_client_activity = time.monotonic()

                    if msg_type == "input":
                        now = time.monotonic()
                        elapsed = now - _input_last
                        _input_tokens = min(_input_max, _input_tokens + elapsed * _input_rate)
                        _input_last = now

                        if _input_tokens < 1.0:
                            _input_flood_count += 1
                            if now - _input_flood_window > 5.0:
                                _input_flood_window = now
                                _input_flood_count = 1

                            if _input_flood_count > 500:
                                logger.warning("WS input flood from %s — disconnecting", client_ip)
                                await websocket.close(code=4429, reason="Input rate exceeded")
                                return
                            continue

                        _input_tokens -= 1.0
                        data = msg.get("data", "")
                        if data and session.is_alive:
                            session.send_input(data)

                    elif msg_type == "resize":
                        cols = msg.get("cols", 120)
                        rows = msg.get("rows", 30)
                        if session.is_alive:
                            session.resize(int(cols), int(rows))

                    elif msg_type == "ping":
                        await send_msg({"type": "pong"})

            async def pty_to_ws():
                while True:
                    try:
                        msg = await queue.get()
                    except asyncio.CancelledError:
                        return

                    for attempt in range(3):
                        try:
                            await send_msg(msg)
                            break
                        except WebSocketDisconnect:
                            return
                        except Exception:
                            if attempt < 2:
                                await asyncio.sleep(0.3 * (attempt + 1))
                            else:
                                return

                    if msg.get("type") == "exited":
                        return

            async def server_heartbeat():
                nonlocal _last_client_activity
                while True:
                    await asyncio.sleep(25)
                    try:
                        await send_msg({"type": "pong"})
                    except Exception:
                        return
                    if time.monotonic() - _last_client_activity > 60:
                        logger.info("Client silent for >60s, closing WS (ip=%s)", client_ip)
                        try:
                            await websocket.close(code=4408, reason="Heartbeat timeout")
                        except Exception:
                            pass
                        return

            _last_client_activity = time.monotonic()

            done, pending = await asyncio.wait(
                [
                    asyncio.create_task(ws_to_pty()),
                    asyncio.create_task(pty_to_ws()),
                    asyncio.create_task(server_heartbeat()),
                ],
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        except WebSocketDisconnect:
            pass
        except Exception as e:
            logger.error("Terminal WebSocket error: %s", e, exc_info=True)
            deep.error(
                "terminal_ws_error",
                error=str(e),
                work_dir=work_dir,
            )
        finally:
            session.unsubscribe(queue)
            if session_id:
                crypto.remove_session(session_id)
            deep.log(
                "terminal_ws_disconnected",
                category="terminal",
                work_dir=work_dir,
            )
            logger.info("Terminal WebSocket disconnected")

    finally:
        async with _ws_lock:
            _ws_connections[client_ip] = max(0, _ws_connections[client_ip] - 1)
            if _ws_connections[client_ip] == 0:
                del _ws_connections[client_ip]
