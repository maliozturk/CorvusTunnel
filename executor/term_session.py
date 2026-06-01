"""
CorvusTunnel Terminal Session — WebSocket-backed interactive PTY.

Manages a single persistent winpty PTY process (agy.exe) with:
- Pub/Sub output broadcasting to multiple WebSocket subscribers
- 64KB replay buffer for reconnection catch-up
- 5-minute grace period after last subscriber disconnects
- Deep forensic logging of all input and output
- Dynamic terminal resizing via pty.set_size()
"""

from __future__ import annotations

import asyncio
import logging
import os
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)

AGY_BIN_DIR = r"C:\Users\alini\AppData\Local\agy\bin"
REPLAY_BUFFER_MAX = 65536  # 64KB
GRACE_PERIOD_S = 300  # 5 minutes
LOG_FLUSH_INTERVAL_S = 2.0  # Batch deep-log output every 2s


def _build_env_string() -> str:
    """Build null-delimited environment string for winpty.PTY.spawn().

    winpty expects env as a single string:  "KEY1=VAL1\\0KEY2=VAL2\\0"
    We clone os.environ and prepend the agy bin dir to PATH.
    """
    env = os.environ.copy()

    # Prepend agy bin dir to PATH so `agy` is available immediately
    current_path = env.get("PATH", "")
    if AGY_BIN_DIR.lower() not in current_path.lower():
        env["PATH"] = AGY_BIN_DIR + ";" + current_path

    # Serialize to null-delimited string
    return "\0".join(f"{k}={v}" for k, v in env.items()) + "\0"


class TerminalSession:
    """Persistent interactive terminal session backed by winpty.

    Lifecycle:
        start(work_dir, cols, rows)  → spawn PTY, start reader thread
        send_input(data)             → pty.write(data), deep-log
        resize(cols, rows)           → pty.set_size(cols, rows)
        stop()                       → graceful shutdown

    Pub/Sub:
        subscribe()   → asyncio.Queue (+ replay buffer text)
        unsubscribe() → remove queue, schedule grace-period cleanup
    """

    def __init__(self) -> None:
        self._pty: Any = None
        self._alive: bool = False
        self._work_dir: str | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._reader_thread: threading.Thread | None = None
        self._started_at: float | None = None

        # Pub/Sub: list of subscriber queues
        self._subscribers: list[asyncio.Queue] = []
        self._sub_lock: threading.Lock = threading.Lock()

        # Replay buffer (front-trimmed when > 64KB)
        self._replay_buf: str = ""
        self._replay_lock: threading.Lock = threading.Lock()

        # Deep-log output batching
        self._log_buf: str = ""
        self._log_buf_lock: threading.Lock = threading.Lock()
        self._last_log_flush: float = 0.0
        self._input_count: int = 0

        # Grace period timer handle
        self._grace_timer: asyncio.TimerHandle | None = None

    # ── Properties ────────────────────────────────────────────────────

    @property
    def is_alive(self) -> bool:
        return self._alive and self._pty is not None

    @property
    def work_dir(self) -> str | None:
        return self._work_dir

    # ── Lifecycle ─────────────────────────────────────────────────────

    def start(self, work_dir: str, cols: int = 120, rows: int = 30, flags: list[str] | None = None) -> None:
        """Start a new terminal session in work_dir."""
        if self.is_alive:
            self.stop()

        import winpty

        self._work_dir = work_dir
        self._loop = asyncio.get_event_loop()
        self._alive = True
        self._started_at = time.time()
        self._replay_buf = ""
        self._log_buf = ""
        self._input_count = 0
        self._last_log_flush = time.time()

        # Cancel any pending grace timer
        if self._grace_timer:
            self._grace_timer.cancel()
            self._grace_timer = None

        # Build environment with agy on PATH
        env_str = _build_env_string()

        # Build agy command with optional flags
        agy_path = os.path.join(AGY_BIN_DIR, "agy.exe")
        cmd = agy_path
        if flags:
            cmd = cmd + " " + " ".join(flags)

        logger.info("Starting terminal session in %s (%dx%d) cmd=%s", work_dir, cols, rows, cmd)

        self._pty = winpty.PTY(cols, rows)
        self._pty.spawn(
            cmd,
            cwd=work_dir,
            env=env_str,
        )

        self._reader_thread = threading.Thread(
            target=self._read_loop, daemon=True, name="term-reader",
        )
        self._reader_thread.start()

        from audit.deep_logger import get_deep_logger
        get_deep_logger().log(
            "terminal_started", category="terminal",
            work_dir=work_dir, cols=cols, rows=rows,
            flags=flags or [],
        )

    def send_input(self, data: str) -> None:
        """Send raw input data to the PTY."""
        if not self.is_alive:
            raise RuntimeError("Terminal session is not running")

        self._pty.write(data)

        # Flush any pending output to deep log before logging input
        self._flush_log_buffer(force=True)

        self._input_count += 1

        from audit.deep_logger import get_deep_logger
        get_deep_logger().log(
            "terminal_input", category="terminal",
            seq=self._input_count,
            data=data,
            work_dir=self._work_dir,
        )

    def resize(self, cols: int, rows: int) -> None:
        """Resize the PTY."""
        if not self.is_alive:
            return
        try:
            self._pty.set_size(cols, rows)
            logger.debug("Terminal resized to %dx%d", cols, rows)
        except Exception as e:
            logger.warning("Failed to resize terminal: %s", e)

    def stop(self) -> None:
        """Stop the terminal session gracefully."""
        if not self._alive:
            return

        logger.info("Stopping terminal session")
        self._alive = False

        # Cancel grace timer
        if self._grace_timer:
            self._grace_timer.cancel()
            self._grace_timer = None

        # Try graceful exit
        if self._pty:
            try:
                self._pty.write("exit\r\n")
                time.sleep(0.3)
            except Exception:
                pass

        # Notify all subscribers
        self._broadcast({"type": "exited", "code": self._get_exit_status()})

        # Flush remaining log buffer
        self._flush_log_buffer(force=True)

        from audit.deep_logger import get_deep_logger
        get_deep_logger().log(
            "terminal_stopped", category="terminal",
            total_inputs=self._input_count,
            uptime_s=round(time.time() - self._started_at, 1)
            if self._started_at else 0,
            work_dir=self._work_dir,
        )

        self._pty = None

    # ── Pub/Sub ───────────────────────────────────────────────────────

    def subscribe(self) -> tuple[asyncio.Queue, str]:
        """Subscribe to terminal output.

        Returns:
            (queue, replay_text): A dedicated queue for this subscriber,
            and the current replay buffer for catch-up.
        """
        q: asyncio.Queue = asyncio.Queue(maxsize=4096)
        with self._sub_lock:
            self._subscribers.append(q)

        # Cancel any pending grace timer since we have a subscriber
        if self._grace_timer:
            self._grace_timer.cancel()
            self._grace_timer = None
            logger.info("Grace period cancelled — new subscriber connected")

        with self._replay_lock:
            replay = self._replay_buf

        logger.info(
            "Subscriber added (total: %d, replay: %d chars)",
            len(self._subscribers), len(replay),
        )
        return q, replay

    def unsubscribe(self, q: asyncio.Queue) -> None:
        """Remove a subscriber queue and schedule grace-period cleanup."""
        with self._sub_lock:
            if q in self._subscribers:
                self._subscribers.remove(q)

        count = len(self._subscribers)
        logger.info("Subscriber removed (remaining: %d)", count)

        # If no subscribers left, schedule grace period
        if count == 0 and self.is_alive and self._loop:
            logger.info(
                "No subscribers — scheduling %ds grace period",
                GRACE_PERIOD_S,
            )
            self._grace_timer = self._loop.call_later(
                GRACE_PERIOD_S, self._grace_expired,
            )

    def _grace_expired(self) -> None:
        """Called when the grace period expires with no subscribers."""
        if len(self._subscribers) == 0 and self.is_alive:
            logger.info("Grace period expired — stopping terminal session")
            self.stop()
        else:
            logger.info("Grace period expired but subscribers exist — keeping session")

    # ── Status ────────────────────────────────────────────────────────

    def status(self) -> dict[str, Any]:
        return {
            "alive": self.is_alive,
            "work_dir": self._work_dir,
            "uptime_s": round(time.time() - self._started_at, 1)
            if self._started_at else 0,
            "subscribers": len(self._subscribers),
        }

    # ── Internal: PTY read loop ───────────────────────────────────────

    def _read_loop(self) -> None:
        """Background thread: read PTY output continuously.

        - Pushes data to all subscriber queues (pub/sub)
        - Appends to replay buffer (front-trimmed at 64KB)
        - Batches output for deep logging (flush every 2s or on input)
        - Detects process death and broadcasts 'exited' event
        """
        while self._alive:
            # Check if process is still alive
            if self._pty and not self._pty.isalive():
                exit_code = self._get_exit_status()
                logger.info("PTY process exited (code=%s)", exit_code)
                self._broadcast({"type": "exited", "code": exit_code})

                from audit.deep_logger import get_deep_logger
                self._flush_log_buffer(force=True)
                get_deep_logger().log(
                    "terminal_process_exited", category="terminal",
                    exit_code=exit_code, work_dir=self._work_dir,
                )
                self._alive = False
                break

            # Read from PTY (non-blocking)
            try:
                data = self._pty.read(blocking=False)
            except Exception:
                time.sleep(0.03)
                continue

            if not data:
                # Periodically flush log buffer even when idle
                self._flush_log_buffer(force=False)
                time.sleep(0.03)
                continue

            # Append to replay buffer (front-trim if needed)
            with self._replay_lock:
                self._replay_buf += data
                if len(self._replay_buf) > REPLAY_BUFFER_MAX:
                    self._replay_buf = self._replay_buf[-REPLAY_BUFFER_MAX:]

            # Accumulate for deep-log batching
            with self._log_buf_lock:
                self._log_buf += data

            # Flush log buffer if enough time has passed
            self._flush_log_buffer(force=False)

            # Broadcast to all subscribers
            self._broadcast({"type": "output", "data": data})

    def _broadcast(self, msg: dict) -> None:
        """Push a message to all subscriber queues (thread-safe)."""
        if not self._loop:
            return
        with self._sub_lock:
            for q in list(self._subscribers):
                try:
                    self._loop.call_soon_threadsafe(q.put_nowait, msg)
                except asyncio.QueueFull:
                    logger.warning("Subscriber queue full — dropping message")
                except Exception:
                    pass

    def _flush_log_buffer(self, force: bool = False) -> None:
        """Flush batched output to deep log.

        Called periodically (every LOG_FLUSH_INTERVAL_S) or forced on input.
        """
        now = time.time()
        if not force and (now - self._last_log_flush) < LOG_FLUSH_INTERVAL_S:
            return

        with self._log_buf_lock:
            buf = self._log_buf
            self._log_buf = ""

        if not buf:
            return

        self._last_log_flush = now
        try:
            from audit.deep_logger import get_deep_logger
            get_deep_logger().log(
                "terminal_output", category="terminal",
                output_length=len(buf),
                data=buf,
                work_dir=self._work_dir,
            )
        except Exception as e:
            logger.warning("Failed to deep-log terminal output: %s", e)

    def _get_exit_status(self) -> int | None:
        """Get the exit status of the PTY process, or None if unavailable."""
        if self._pty:
            try:
                return self._pty.get_exitstatus()
            except Exception:
                return None
        return None


# ── Singleton ────────────────────────────────────────────────────────

_terminal_session: TerminalSession | None = None


def get_terminal_session() -> TerminalSession:
    """Return the singleton TerminalSession."""
    global _terminal_session
    if _terminal_session is None:
        _terminal_session = TerminalSession()
    return _terminal_session
