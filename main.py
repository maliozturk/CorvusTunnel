"""
CorvusTunnel -- Dual-Server Launcher.

Starts two uvicorn servers in parallel:
  - Public API on 0.0.0.0:8000 (accessible via Cloudflare Tunnel)
  - Internal API on 127.0.0.1:8001 (localhost only, for approval)

Usage:
    python main.py
    
    # Or with custom ports:
    PUBLIC_PORT=9000 INTERNAL_PORT=9001 python main.py
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys

import uvicorn

# -- Setup logging ---------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("corvustunnel")


def _setup_executor() -> None:
    """Register the Antigravity executor with the job manager."""
    from jobqueue.manager import get_job_manager
    from executor.antigravity import AntigravityExecutor
    from config.settings import get_settings

    settings = get_settings()
    executor = AntigravityExecutor()
    manager = get_job_manager()

    async def execute_callback(job):
        return await executor.execute(
            job=job,
            work_dir=settings.work_dir,
            timeout=settings.max_exec_timeout,
            max_output=settings.max_output_size,
        )

    manager.set_executor(execute_callback)
    logger.info(f"Executor registered: {executor.name}")


def _setup_protection() -> None:
    """Lock critical files read-only and initialize deep logging."""
    from config.protection import lock_critical_files
    from audit.deep_logger import get_deep_logger

    count = lock_critical_files()
    deep = get_deep_logger()
    deep.log(
        "protection_enabled",
        category="system",
        locked_files=count,
        detail=".env and all source files are read-only until shutdown",
    )


def _print_banner(public_port: int, internal_port: int) -> None:
    """Print a startup banner with configuration summary."""
    banner = f"""
+==============================================================+
|                                                              |
|   CORVUS TUNNEL                                              |
|   Remote Agent Control System v0.1.0                         |
|                                                              |
+==============================================================+
|                                                              |
|   [PUBLIC]   http://0.0.0.0:{public_port:<5}                          |
|   [INTERNAL] http://127.0.0.1:{internal_port:<5}                         |
|   [API DOCS] http://localhost:{public_port}/docs                     |
|   [ADMIN]    http://localhost:{internal_port}/docs                     |
|                                                              |
|   Start Cloudflare Tunnel separately:                        |
|   cloudflared tunnel --url http://localhost:{public_port}              |
|                                                              |
+==============================================================+
"""
    print(banner)


async def _run_servers() -> None:
    """Run both public and internal servers concurrently."""
    from config.settings import get_settings

    settings = get_settings()
    public_port = settings.public_port
    internal_port = settings.internal_port

    # Lock critical files (read-only) before anything else
    _setup_protection()

    # Setup executor
    _setup_executor()

    # Print banner
    _print_banner(public_port, internal_port)

    logger.info(f"Work directory: {settings.work_dir}")
    logger.info(f"Audit log directory: {settings.audit_log_dir}")

    # Configure uvicorn servers
    public_config = uvicorn.Config(
        "public_app:app",
        host="0.0.0.0",
        port=public_port,
        log_level="info",
        access_log=True,
    )
    internal_config = uvicorn.Config(
        "internal_app:app",
        host="127.0.0.1",
        port=internal_port,
        log_level="info",
        access_log=True,
    )

    public_server = uvicorn.Server(public_config)
    internal_server = uvicorn.Server(internal_config)

    # Run both servers concurrently
    logger.info("Starting dual servers...")

    try:
        await asyncio.gather(
            public_server.serve(),
            internal_server.serve(),
        )
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutdown signal received")
    finally:
        logger.info("CorvusTunnel stopped")


def main() -> None:
    """Entry point."""
    # Validate environment before starting
    try:
        from config.settings import get_settings
        settings = get_settings()
    except Exception as e:
        print(f"\n[ERROR] Configuration error: {e}")
        print(f"\n[TIP] Make sure to set required environment variables.")
        print(f"   Copy .env.example to .env and fill in the values:")
        print(f"   - AGENT_TOKEN (required, min 32 chars)")
        print(f"\n   Or set AGENT_TOKEN as an environment variable.")
        sys.exit(1)

    try:
        asyncio.run(_run_servers())
    except KeyboardInterrupt:
        print("\nCorvusTunnel stopped.")


if __name__ == "__main__":
    main()
