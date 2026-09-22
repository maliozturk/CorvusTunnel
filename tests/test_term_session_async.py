# /*--------------------------------*- py -*-----------------------------*\
# |     __                                                               |
# |   <(o )___    CorvusTunnel                                           |
# |    ( ._> /    control AI agents from any device                      |
# |     `---'     self-hosted · E2E encrypted · MIT                      |
# *----------------------------------------------------------------------*/
# File:        tests/test_term_session_async.py
# Description: Terminal lifecycle must not run on the event-loop thread:
#              stop() sleeps 0.3s and start() spawns a PTY, so both are
#              offloaded and other channel connections keep being served.
# \*---------------------------------------------------------------------*/

import asyncio
import time

import pytest_asyncio

from corvustunnel.executor.term_session import TerminalSession

HEARTBEAT_S = 0.02


class _FakeProcess:
    """Stands in for pexpect/winpty so stop() takes its real 0.3s path."""

    exitstatus = 0

    def __init__(self):
        self.alive = True
        self.terminated = False

    def isalive(self):
        return self.alive

    def sendline(self, line):
        pass

    def terminate(self, force=False):
        self.alive = False
        self.terminated = True


def _live_session():
    session = TerminalSession()
    session._process = _FakeProcess()
    session._alive = True
    session._started_at = time.time()
    session._loop = asyncio.get_running_loop()
    return session


@pytest_asyncio.fixture
async def heartbeat():
    """Counts how often the event loop got to run."""
    ticks = []

    async def _beat():
        while True:
            ticks.append(time.perf_counter())
            await asyncio.sleep(HEARTBEAT_S)

    task = asyncio.create_task(_beat())
    yield ticks
    task.cancel()


async def test_stop_async_keeps_event_loop_responsive(env_full, heartbeat):
    session = _live_session()

    await asyncio.sleep(HEARTBEAT_S * 2)
    before = len(heartbeat)
    await session.stop_async()

    assert not session.is_alive
    assert session._process is None
    # stop() sleeps 0.3s; a blocked loop would tick zero times meanwhile.
    assert len(heartbeat) - before >= 2


async def test_start_async_captures_the_calling_loop(env_full, monkeypatch):
    session = TerminalSession()
    monkeypatch.setattr(
        "corvustunnel.executor.term_session._WindowsProcess",
        lambda *a, **kw: _FakeProcess(),
        raising=False,
    )
    monkeypatch.setattr(session, "_read_loop", lambda: None)

    await session.start_async("/tmp", command="fake-agent", flags=["--x"])

    # start() runs off-thread, where get_event_loop() would have failed:
    # _broadcast/unsubscribe still need the serving loop.
    assert session._loop is asyncio.get_running_loop()
    assert session.is_alive
    assert session.command == "fake-agent"

    await session.stop_async()


async def test_grace_expiry_does_not_block_the_loop(env_full, heartbeat):
    session = _live_session()
    queue, _ = session.subscribe()
    session.unsubscribe(queue)
    assert session._grace_timer is not None

    before = len(heartbeat)
    session._grace_expired()  # fires on the loop thread
    await asyncio.sleep(0.6)

    assert not session.is_alive
    assert len(heartbeat) - before >= 2
