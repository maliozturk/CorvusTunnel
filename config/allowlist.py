"""
CorvusTunnel Allowlist — Command validation and security filters.
"""

from __future__ import annotations

import shlex
import re
from pathlib import PurePosixPath, PureWindowsPath

# ── Allowed executor targets ─────────────────────────────────────────
ALLOWED_TARGETS: set[str] = {"antigravity"}

# ── Shell command allowlist (for future shell executor) ──────────────
SHELL_ALLOWLIST: set[str] = {
    "git", "ls", "dir", "cat", "type", "echo", "pwd",
    "npm", "python", "node", "pip",
}

# ── Blocked shell operators (chain / redirect / subshell) ────────────
BLOCKED_OPERATORS: set[str] = {
    "&&", "||", ";", "|", "`", "$(", ">", "<", ">>", "<<",
}

# ── Blocked path patterns (sensitive directories / files) ────────────
BLOCKED_PATH_PATTERNS: list[str] = [
    ".ssh", ".env", "credentials", "secrets", ".aws",
    ".gnupg", ".gitconfig", "id_rsa", "id_ed25519",
    "authorized_keys", "known_hosts", ".npmrc", ".pypirc",
]


def is_target_allowed(target: str) -> bool:
    """Check if the given executor target is in the allowlist."""
    return target in ALLOWED_TARGETS


def is_shell_allowed(command: str) -> bool:
    """
    Validate a shell command against the allowlist.
    
    Rules:
    - First token (binary name) must be in SHELL_ALLOWLIST
    - No chaining operators allowed
    - No blocked path patterns in arguments
    """
    # Check for blocked operators
    for op in BLOCKED_OPERATORS:
        if op in command:
            return False

    # Parse command tokens
    try:
        parts = shlex.split(command)
    except ValueError:
        return False

    if not parts:
        return False

    # First token must be an allowed binary
    binary = parts[0].lower()
    # Strip path prefix if present (e.g., /usr/bin/git -> git)
    binary = binary.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    if binary not in SHELL_ALLOWLIST:
        return False

    # Check arguments for blocked path patterns
    for arg in parts[1:]:
        arg_lower = arg.lower()
        for pattern in BLOCKED_PATH_PATTERNS:
            if pattern in arg_lower:
                return False

    # Block path traversal
    for arg in parts[1:]:
        if ".." in arg:
            return False

    return True


def sanitize_prompt(prompt: str, max_length: int = 4000) -> str:
    """Sanitize a prompt string: trim, limit length."""
    prompt = prompt.strip()
    if len(prompt) > max_length:
        prompt = prompt[:max_length]
    return prompt
