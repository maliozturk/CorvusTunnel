# /*--------------------------------*- py -*-----------------------------*\
# |     __                                                               |
# |   <(o )___    CorvusTunnel                                           |
# |    ( ._> /    control AI agents from any device                      |
# |     `---'     self-hosted · E2E encrypted · MIT                      |
# *----------------------------------------------------------------------*/
# File:        corvustunnel/routers/channel.py
# Description: The single authenticated end-to-end channel (WS /api/channel).
#              After a signed handshake every control op (claim, browse,
#              history, terminal) is multiplexed inside encrypted frames, so
#              the relay only ever forwards opaque ciphertext.
# \*---------------------------------------------------------------------*/

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from corvustunnel.crypto import channel as ch
from corvustunnel.routers import handlers

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

_MAX_CLAIM_FAILURES = 5


@router.websocket("/channel")
async def channel_ws(websocket: WebSocket):
    from corvustunnel.audit.deep_logger import get_deep_logger
    from corvustunnel.auth.bearer import get_token_manager
    from corvustunnel.executor.term_session import get_terminal_session

    deep = get_deep_logger()
    await websocket.accept()

    try:
        client_hello = json.loads(await websocket.receive_text())
        server_hello, channel = ch.server_handshake(ch.get_server_identity(), client_hello)
        await websocket.send_text(json.dumps(server_hello))
    except (ch.HandshakeError, json.JSONDecodeError, KeyError, WebSocketDisconnect) as exc:
        logger.info("Channel handshake rejected: %s", exc)
        await websocket.close(code=4001, reason="Handshake failed")
        return

    send_lock = asyncio.Lock()
    state = {"claimed": False, "fails": 0}
    term_task = None
    term_queue = None

    async def send(obj):
        async with send_lock:
            await websocket.send_bytes(channel.encrypt(json.dumps(obj).encode()))

    async def reply(rid, data):
        await send({"id": rid, "ok": True, "data": data})

    async def reply_err(rid, status, detail):
        await send({"id": rid, "ok": False, "status": status, "error": detail})

    async def stream_terminal(queue):
        try:
            while True:
                msg = await queue.get()
                await send({"ev": msg.get("type"), **{k: v for k, v in msg.items() if k != "type"}})
                if msg.get("type") == "exited":
                    return
        except asyncio.CancelledError:
            return
        except Exception:
            return

    deep.log("channel_connected", category="channel")

    try:
        while True:
            try:
                raw = await websocket.receive_bytes()
            except WebSocketDisconnect:
                break

            try:
                msg = json.loads(channel.decrypt(raw))
            except (ch.HandshakeError, json.JSONDecodeError, ValueError):
                logger.warning("Channel frame rejected (auth/replay)")
                break

            op = msg.get("op", "")
            rid = msg.get("id")

            if op == "claim":
                token = msg.get("token", "")
                session_token = get_token_manager().claim_boot_token(token, client_ip=None)
                if session_token is None:
                    state["fails"] += 1
                    deep.log("channel_claim_rejected", category="auth")
                    await reply_err(rid, 401, "Invalid or already consumed token")
                    if state["fails"] >= _MAX_CLAIM_FAILURES:
                        break
                    continue
                state["claimed"] = True
                deep.log("channel_claim_success", category="auth")
                await reply(rid, {"session_token": session_token})
                continue

            if op == "resume":
                if get_token_manager().verify(msg.get("session_token", "")):
                    state["claimed"] = True
                    await reply(rid, {"resumed": True})
                    continue
                state["fails"] += 1
                await reply_err(rid, 401, "Invalid session token")
                if state["fails"] >= _MAX_CLAIM_FAILURES:
                    break
                continue

            if not state["claimed"]:
                await reply_err(rid, 401, "Channel not authenticated")
                continue

            if op == "ping":
                await send({"ev": "pong"})
                continue

            try:
                if op == "check_agents":
                    await reply(rid, handlers.check_agents())
                elif op == "browse":
                    await reply(rid, handlers.browse(msg.get("path")))
                elif op == "mkdir":
                    await reply(rid, handlers.mkdir(msg.get("parent"), msg.get("name")))
                elif op == "history_list":
                    await reply(
                        rid,
                        handlers.history_list(
                            agent=msg.get("agent"),
                            limit=int(msg.get("limit", 50)),
                            offset=int(msg.get("offset", 0)),
                        ),
                    )
                elif op == "history_get":
                    await reply(
                        rid,
                        handlers.history_get(
                            msg.get("session_id", ""),
                            limit=int(msg.get("limit", 200)),
                            offset=int(msg.get("offset", 0)),
                        ),
                    )
                elif op == "term_start":
                    work_dir = msg.get("work_dir", "")
                    agent = msg.get("agent", "agy")
                    if agent not in handlers.ALLOWED_AGENTS:
                        await reply_err(rid, 400, f"Unknown agent: {agent}")
                        continue
                    if not handlers.validate_work_dir(work_dir):
                        await reply_err(rid, 403, "work_dir not allowed")
                        continue
                    import shutil

                    if not shutil.which(agent):
                        await reply_err(rid, 400, f"{agent} not found on PATH")
                        continue
                    session = get_terminal_session()
                    if session.is_alive and (
                        session.work_dir != work_dir or session.command != agent
                    ):
                        session.stop()
                    if not session.is_alive:
                        session.start(
                            work_dir,
                            command=agent,
                            flags=handlers.filter_flags(msg.get("flags")),
                        )
                    term_queue, replay_text = session.subscribe()
                    if term_task is not None:
                        term_task.cancel()
                    term_task = asyncio.create_task(stream_terminal(term_queue))
                    await reply(rid, {"started": True})
                    if replay_text:
                        await send({"ev": "replay", "data": replay_text})
                elif op == "term_input":
                    session = get_terminal_session()
                    data = msg.get("data", "")
                    if data and session.is_alive:
                        session.send_input(data)
                elif op == "term_resize":
                    session = get_terminal_session()
                    if session.is_alive:
                        session.resize(int(msg.get("cols", 120)), int(msg.get("rows", 30)))
                else:
                    await reply_err(rid, 400, f"Unknown op: {op}")
            except handlers.AppError as exc:
                await reply_err(rid, exc.status, exc.detail)
            except Exception as exc:
                logger.error("Channel op %s failed: %s", op, exc, exc_info=True)
                await reply_err(rid, 500, "Internal error")

    finally:
        if term_task is not None:
            term_task.cancel()
        if term_queue is not None:
            get_terminal_session().unsubscribe(term_queue)
        deep.log("channel_disconnected", category="channel")
