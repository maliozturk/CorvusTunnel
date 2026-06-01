"""
CorvusTunnel Public API Router.

Exposed through Cloudflare Tunnel on port 8000.
All endpoints (except /health) require Bearer token authentication.
"""

from __future__ import annotations

import asyncio
import json
import time
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

from auth.dependencies import require_public_auth
from audit.logger import get_audit_logger
from config.allowlist import is_target_allowed, sanitize_prompt
from models.requests import PromptRequest
from models.responses import JobResponse, JobListResponse, HealthResponse
from jobqueue.manager import get_job_manager
from jobqueue.notifier import notify_new_job

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

# ── Startup time for uptime calculation ──────────────────────────────
_start_time = time.time()


# ── Health (no auth) ─────────────────────────────────────────────────
@router.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint (no authentication required)."""
    return HealthResponse(
        status="ok",
        version="0.1.0",
        uptime_seconds=round(time.time() - _start_time, 1),
    )


# ── Browse directories (folder picker) ───────────────────────────────
@router.get("/browse", dependencies=[Depends(require_public_auth)])
async def browse_directory(request: Request, path: str = Query(default=None)):
    """List subdirectories for the folder picker UI.

    Security: only directories listed in ALLOWED_DIRS (and their
    children) are visible.  No path outside the whitelist is reachable.
    """
    from pathlib import Path as P
    from config.settings import get_settings

    from audit.deep_logger import get_deep_logger
    deep = get_deep_logger()
    client_ip = request.client.host if request.client else "unknown"

    settings = get_settings()
    roots = [P(d).resolve() for d in settings.allowed_dir_list]

    if not roots:
        raise HTTPException(
            400, "No allowed directories configured — set ALLOWED_DIRS in .env"
        )

    # No path → return the whitelisted root directories
    if path is None:
        dirs = []
        for r in roots:
            if r.exists() and r.is_dir():
                dirs.append({"name": r.name, "path": str(r)})
        deep.browse(client_ip, path=None, result_count=len(dirs))
        return {"current": "Projects", "parent": None, "directories": dirs}

    target = P(path).resolve()

    # Security: must fall under one of the allowed roots
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
                and not entry.name.startswith('.')
                and not entry.name.startswith('__')
            ):
                dirs.append({"name": entry.name, "path": str(entry)})
    except PermissionError:
        raise HTTPException(403, "Permission denied")

    # Parent: at allowed root → "" (signals "go to root list"), else → real parent
    parent = "" if target == active_root else str(target.parent.resolve())

    deep.browse(client_ip, path, result_count=len(dirs))
    return {"current": str(target), "parent": parent, "directories": dirs}


# ── Check agy availability ───────────────────────────────────────
@router.get("/check-agy", dependencies=[Depends(require_public_auth)])
async def check_agy():
    """Check if agy.exe is available on this system."""
    import os
    agy_path = os.path.join(r"C:\Users\alini\AppData\Local\agy\bin", "agy.exe")
    available = os.path.isfile(agy_path)
    return {"available": available, "path": agy_path if available else None}


# ── Create new directory ─────────────────────────────────────────
@router.post("/browse/mkdir", dependencies=[Depends(require_public_auth)])
async def create_directory(request: Request):
    """Create a new subdirectory within an allowed directory."""
    from pathlib import Path as P
    from config.settings import get_settings
    from audit.deep_logger import get_deep_logger
    import re

    body = await request.json()
    parent = body.get("parent", "")
    name = body.get("name", "").strip()

    if not parent or not name:
        raise HTTPException(400, "parent and name are required")

    # Security: reject dangerous names
    if not re.match(r'^[a-zA-Z0-9_\-. ]+$', name):
        raise HTTPException(
            400,
            "Invalid folder name \u2014 only letters, numbers, dashes, "
            "underscores, dots, and spaces allowed",
        )

    if '..' in name:
        raise HTTPException(400, "Invalid folder name")

    settings = get_settings()
    roots = [P(d).resolve() for d in settings.allowed_dir_list]
    parent_path = P(parent).resolve()

    # Validate parent is inside ALLOWED_DIRS
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
    except Exception as e:
        raise HTTPException(500, f"Failed to create directory: {e}")

    deep = get_deep_logger()
    deep.log(
        "directory_created", category="browse",
        parent=str(parent_path), name=name, path=str(new_dir),
    )

    return {"created": True, "path": str(new_dir)}


# ── Submit prompt ────────────────────────────────────────────────────
@router.post(
    "/prompt",
    response_model=JobResponse,
    dependencies=[Depends(require_public_auth)],
)
async def submit_prompt(req: PromptRequest, request: Request):
    """
    Submit a new prompt to an executor.
    
    If require_approval is True (default), the job enters 'pending' state
    and waits for manual approval via the internal API.
    """
    audit = get_audit_logger()
    client_ip = request.client.host if request.client else "unknown"

    # Validate target
    if not is_target_allowed(req.target):
        audit.log(
            action="blocked",
            target=req.target,
            prompt=req.prompt,
            client_ip=client_ip,
            detail=f"Target '{req.target}' not in allowlist",
        )
        raise HTTPException(400, f"Target '{req.target}' is not allowed")

    # Sanitize prompt
    prompt = sanitize_prompt(req.prompt)

    # Submit to queue
    manager = get_job_manager()
    job = await manager.submit(
        target=req.target,
        prompt=prompt,
        require_approval=req.require_approval,
        work_dir=req.work_dir,
    )

    audit.log(
        action="submit",
        job_id=job.job_id,
        target=req.target,
        prompt=prompt,
        client_ip=client_ip,
    )

    # Deep log: full plaintext prompt and metadata
    from audit.deep_logger import get_deep_logger
    get_deep_logger().prompt_submitted(
        job_id=job.job_id,
        prompt=prompt,
        target=req.target,
        client_ip=client_ip,
        work_dir=req.work_dir,
        require_approval=req.require_approval,
        is_shell=prompt.startswith("$"),
    )

    # Send desktop notification for pending jobs
    if req.require_approval:
        try:
            notify_new_job(job.job_id, req.target, prompt)
        except Exception as e:
            logger.warning(f"Notification failed: {e}")

    logger.info(
        f"Job {job.job_id} submitted: target={req.target}, "
        f"status={job.status}, approval={'required' if req.require_approval else 'auto'}"
    )

    return job.to_response()


# ── Job status ───────────────────────────────────────────────────────
@router.get(
    "/status/{job_id}",
    response_model=JobResponse,
    dependencies=[Depends(require_public_auth)],
)
async def get_status(job_id: str):
    """Get the current status of a job."""
    manager = get_job_manager()
    job = await manager.get_job(job_id)

    if job is None:
        raise HTTPException(404, f"Job '{job_id}' not found")

    return job.to_response()


# ── Job list ─────────────────────────────────────────────────────────
@router.get(
    "/jobs",
    response_model=JobListResponse,
    dependencies=[Depends(require_public_auth)],
)
async def list_jobs(limit: int = Query(default=50, ge=1, le=200)):
    """List all jobs, most recent first."""
    manager = get_job_manager()
    jobs = await manager.get_all_jobs(limit=limit)

    return JobListResponse(
        jobs=[j.to_response() for j in jobs],
        total=len(jobs),
    )


# ── SSE Stream ───────────────────────────────────────────────────────
@router.get("/stream/{job_id}")
async def stream_job(
    job_id: str,
    token: str = Query(..., description="Bearer token for SSE auth"),
):
    """
    Server-Sent Events stream for real-time job output.
    
    SSE doesn't support custom headers, so the token is passed
    as a query parameter. This is acceptable because:
    1. The connection is over HTTPS (via Cloudflare)
    2. The token is not logged in access logs (POST body would be)
    """
    from auth.bearer import verify_bearer_token

    if not verify_bearer_token(f"Bearer {token}"):
        raise HTTPException(401, "Invalid token")

    manager = get_job_manager()
    job = await manager.get_job(job_id)

    if job is None:
        raise HTTPException(404, f"Job '{job_id}' not found")

    async def event_generator() -> AsyncGenerator[str, None]:
        """Generate SSE events from the job's output queue."""
        # Send current status
        yield _sse_format("status", job.status, job_id)

        # Send any existing output
        if job.output_text:
            yield _sse_format("output", job.output_text, job_id)

        # If job is already done, send done event and close
        if job.status in ("done", "failed", "timeout", "rejected"):
            result_str = json.dumps(job.result) if job.result else ""
            yield _sse_format("done", result_str, job_id)
            return

        # Subscribe to live updates
        queue = job.subscribe_sse()
        try:
            while True:
                try:
                    event_type, content = await asyncio.wait_for(
                        queue.get(), timeout=30.0
                    )
                    yield _sse_format(event_type, content, job_id)

                    if event_type == "done":
                        # Send final result
                        if job.result:
                            yield _sse_format(
                                "result",
                                json.dumps(job.result),
                                job_id,
                            )
                        break
                except asyncio.TimeoutError:
                    # Send keepalive comment
                    yield ": keepalive\n\n"
        finally:
            job.unsubscribe_sse(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _sse_format(event_type: str, content: str, job_id: str) -> str:
    """Format data as an SSE event."""
    data = json.dumps({
        "type": event_type,
        "content": content,
        "job_id": job_id,
    })
    return f"data: {data}\n\n"


# ══════════════════════════════════════════════════════════════════════
#  WebSocket Terminal
# ══════════════════════════════════════════════════════════════════════


def _validate_work_dir(work_dir: str) -> bool:
    """Check that work_dir falls under one of the ALLOWED_DIRS roots."""
    from pathlib import Path
    from config.settings import get_settings

    settings = get_settings()
    roots = [Path(d).resolve() for d in settings.allowed_dir_list]
    if not roots:
        return False
    target = Path(work_dir).resolve()
    return any(
        target == root or target.is_relative_to(root)
        for root in roots
    )


@router.websocket("/terminal/ws")
async def terminal_ws(
    websocket: WebSocket,
    token: str = Query(""),
    work_dir: str = Query(""),
    flags: str = Query(""),
):
    """WebSocket endpoint for interactive terminal sessions.

    Provides a full-duplex connection between the browser and
    a winpty PTY running agy.exe on the server.

    Auth is via query-param token (WebSocket upgrade can't set headers).
    All I/O is forensically logged.

    Client messages:
        {"type": "input",  "data": "..."}          → raw keystrokes
        {"type": "resize", "cols": N, "rows": N}   → resize PTY
        {"type": "ping"}                            → keep-alive

    Server messages:
        {"type": "output", "data": "..."}           → PTY output
        {"type": "replay", "data": "..."}           → replay buffer on connect
        {"type": "exited", "code": N}               → process exited
        {"type": "pong"}                            → keep-alive reply
        {"type": "error",  "message": "..."}        → error
    """
    from auth.bearer import verify_bearer_token
    from executor.term_session import get_terminal_session
    from audit.deep_logger import get_deep_logger

    deep = get_deep_logger()

    # ── Auth ──────────────────────────────────────────────────────
    if not verify_bearer_token(f"Bearer {token}"):
        deep.log(
            "terminal_ws_auth_fail", category="terminal",
            reason="Invalid token",
        )
        await websocket.close(code=4001, reason="Unauthorized")
        return

    # ── Validate work_dir ─────────────────────────────────────────
    if not work_dir:
        await websocket.close(code=4003, reason="work_dir is required")
        return

    if not _validate_work_dir(work_dir):
        deep.log(
            "terminal_ws_blocked", category="terminal",
            work_dir=work_dir, reason="Not in ALLOWED_DIRS",
        )
        await websocket.close(code=4003, reason="work_dir not allowed")
        return

    # ── Accept ────────────────────────────────────────────────────
    await websocket.accept()
    logger.info("Terminal WebSocket connected (work_dir=%s)", work_dir)
    deep.log(
        "terminal_ws_connected", category="terminal",
        work_dir=work_dir,
    )

    # ── Session ───────────────────────────────────────────────────
    session = get_terminal_session()

    # If session is alive but for a different work_dir, restart it
    if session.is_alive and session.work_dir != work_dir:
        logger.info(
            "Switching terminal work_dir: %s → %s",
            session.work_dir, work_dir,
        )
        session.stop()

    # Start session if not alive
    if not session.is_alive:
        # Parse flags from comma-separated string
        flag_list = [f.strip() for f in flags.split(",") if f.strip()] if flags else None
        # Security: only allow known safe flags
        ALLOWED_FLAGS = {"--dangerously-skip-permissions"}
        if flag_list:
            flag_list = [f for f in flag_list if f in ALLOWED_FLAGS]
        session.start(work_dir, flags=flag_list if flag_list else None)

    # Subscribe to output
    queue, replay_text = session.subscribe()

    try:
        # Send replay buffer for reconnect catch-up
        if replay_text:
            await websocket.send_json({"type": "replay", "data": replay_text})

        # ── Concurrent read/write loops ───────────────────────────

        async def ws_to_pty():
            """Read messages from WebSocket, forward to PTY."""
            while True:
                try:
                    raw = await websocket.receive_text()
                except WebSocketDisconnect:
                    return

                try:
                    msg = json.loads(raw)
                except (json.JSONDecodeError, TypeError):
                    continue

                msg_type = msg.get("type", "")

                if msg_type == "input":
                    data = msg.get("data", "")
                    if data and session.is_alive:
                        session.send_input(data)

                elif msg_type == "resize":
                    cols = msg.get("cols", 120)
                    rows = msg.get("rows", 30)
                    if session.is_alive:
                        session.resize(int(cols), int(rows))

                elif msg_type == "ping":
                    await websocket.send_json({"type": "pong"})

        async def pty_to_ws():
            """Read output from PTY queue, forward to WebSocket."""
            while True:
                try:
                    msg = await queue.get()
                except asyncio.CancelledError:
                    return

                try:
                    await websocket.send_json(msg)
                except Exception:
                    return

                # If process exited, we're done
                if msg.get("type") == "exited":
                    return

        # Run both loops; when either finishes, cancel the other
        done, pending = await asyncio.wait(
            [asyncio.create_task(ws_to_pty()),
             asyncio.create_task(pty_to_ws())],
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
            "terminal_ws_error", error=str(e), work_dir=work_dir,
        )
    finally:
        session.unsubscribe(queue)
        deep.log(
            "terminal_ws_disconnected", category="terminal",
            work_dir=work_dir,
        )
        logger.info("Terminal WebSocket disconnected")

