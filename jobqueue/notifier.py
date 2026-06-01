"""
CorvusTunnel Desktop Notifications — Windows (PowerShell / BurntToast).

Sends a Windows toast notification when a new job needs approval.
"""

from __future__ import annotations

import subprocess
import sys
import logging

logger = logging.getLogger(__name__)


def notify_new_job(job_id: str, target: str, prompt: str) -> None:
    """
    Send a desktop notification for a new pending job.
    
    On Windows, uses PowerShell to show a toast notification.
    Falls back to printing to console if notification fails.
    """
    title = f"CorvusTunnel — Onay Bekliyor [{job_id}]"
    # Truncate prompt for notification display
    body = f"[{target}] {prompt[:120]}{'...' if len(prompt) > 120 else ''}"
    body += f"\n\nOnayla: curl -X POST http://localhost:8001/approve/{job_id}"

    if sys.platform == "win32":
        _notify_windows(title, body)
    elif sys.platform == "darwin":
        _notify_macos(title, body)
    else:
        _notify_linux(title, body)


def _notify_windows(title: str, body: str) -> None:
    """Windows toast notification via PowerShell."""
    # Escape special characters for PowerShell
    title_escaped = title.replace("'", "''")
    body_escaped = body.replace("'", "''").replace("\n", "`n")

    # Try BurntToast first, fall back to basic .NET notification
    ps_script = f"""
    try {{
        Import-Module BurntToast -ErrorAction Stop
        New-BurntToastNotification -Text '{title_escaped}', '{body_escaped}' -AppLogo $null
    }} catch {{
        # Fallback: basic Windows notification
        [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
        [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
        $template = @"
<toast>
    <visual>
        <binding template="ToastGeneric">
            <text>{title_escaped}</text>
            <text>{body_escaped}</text>
        </binding>
    </visual>
</toast>
"@
        $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
        $xml.LoadXml($template)
        $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
        $notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('CorvusTunnel')
        $notifier.Show($toast)
    }}
    """

    try:
        subprocess.Popen(
            ["powershell", "-NoProfile", "-Command", ps_script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except Exception as e:
        logger.warning(f"Desktop notification failed: {e}")
        _fallback_console(title, body)


def _notify_macos(title: str, body: str) -> None:
    """macOS notification via osascript."""
    body_oneline = body.replace("\n", " | ")
    try:
        subprocess.Popen(
            [
                "osascript", "-e",
                f'display notification "{body_oneline}" with title "{title}"',
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as e:
        logger.warning(f"Desktop notification failed: {e}")
        _fallback_console(title, body)


def _notify_linux(title: str, body: str) -> None:
    """Linux notification via notify-send."""
    try:
        subprocess.Popen(
            ["notify-send", title, body, "--urgency=critical"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as e:
        logger.warning(f"Desktop notification failed: {e}")
        _fallback_console(title, body)


def _fallback_console(title: str, body: str) -> None:
    """Fallback: print to console with formatting."""
    print(f"\n{'='*60}")
    print(f"🔔 {title}")
    print(f"{'─'*60}")
    print(body)
    print(f"{'='*60}\n")
