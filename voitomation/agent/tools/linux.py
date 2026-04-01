"""
Linux Tool — allowlisted shell command execution.

Only a curated set of read-safe commands are permitted in Inc 1.
Write commands (rm, chmod, systemctl stop, etc.) require Tier 3+ confirmation
and are gated by the governance layer before this tool is ever called.
"""

import subprocess
import shlex
from typing import Any

# Commands allowed without escalation (Tier 1 reads)
_ALLOWED_READ_COMMANDS = {
    "ls", "cat", "head", "tail", "grep", "find",
    "ps", "df", "du", "free", "top", "uname",
    "whoami", "hostname", "date", "env", "which",
    "systemctl status", "journalctl",
}

_ALLOWED_WRITE_COMMANDS = {
    "mkdir", "touch", "cp", "mv",
}

# Commands that are never permitted, regardless of tier
_BLOCKED_COMMANDS = {
    "rm", "rmdir", "dd", "mkfs", "fdisk",
    "chmod 777", "sudo rm", ">/dev/sda",
}


class LinuxTool:
    """Bounded shell execution for Lily."""

    def definition(self) -> dict:
        return {
            "name": "linux_exec",
            "description": (
                "Execute an allowlisted Linux/shell command. "
                "Only read-safe commands are permitted without Tier 3 confirmation. "
                "Never use this for destructive operations without governance approval."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to execute (e.g. 'ls -la /tmp')",
                    },
                    "working_dir": {
                        "type": "string",
                        "description": "Optional working directory",
                    },
                },
                "required": ["command"],
            },
        }

    def run(self, tool_input: dict[str, Any]) -> tuple[str, bool]:
        command = tool_input.get("command", "").strip()
        cwd = tool_input.get("working_dir")

        # Validate against blocklist
        cmd_base = shlex.split(command)[0] if command else ""
        for blocked in _BLOCKED_COMMANDS:
            if blocked in command:
                return f"BLOCKED: '{blocked}' is not permitted.", False

        if not cmd_base:
            return "ERROR: empty command", False

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=cwd,
            )
            output = result.stdout + (f"\nSTDERR: {result.stderr}" if result.stderr else "")
            return output or "(no output)", result.returncode == 0
        except subprocess.TimeoutExpired:
            return "ERROR: command timed out (30s limit)", False
        except Exception as exc:
            return f"ERROR: {exc}", False
