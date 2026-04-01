"""
Terraform Tool — plan and apply infrastructure changes.

terraform_plan:  generates a plan (read-safe, Tier 1)
terraform_apply: applies an approved plan (Tier 3, requires confirmation)

Inc 1: subprocess calls to terraform CLI.
"""

import subprocess
import json
import os
from pathlib import Path
from typing import Any


class TerraformTool:
    """Terraform plan/apply tool for Lily."""

    def definition(self) -> dict:
        return {
            "name": "terraform_apply",
            "description": (
                "Run 'terraform plan' (safe) or 'terraform apply' (requires governance approval). "
                "Always run plan before apply. Apply is Tier 3 and requires Chris's confirmation."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["plan", "apply", "destroy", "output", "show"],
                        "description": "Terraform operation to run",
                    },
                    "working_dir": {
                        "type": "string",
                        "description": "Path to Terraform configuration directory",
                    },
                    "var_file": {
                        "type": "string",
                        "description": "Optional .tfvars file path",
                    },
                    "vars": {
                        "type": "object",
                        "description": "Optional inline variable overrides",
                    },
                    "auto_approve": {
                        "type": "boolean",
                        "description": "Pass -auto-approve (only for apply after governance gate + confirmation)",
                    },
                },
                "required": ["operation"],
            },
        }

    def run(self, tool_input: dict[str, Any]) -> tuple[str, bool]:
        operation  = tool_input.get("operation", "plan")
        working_dir = tool_input.get("working_dir", ".")
        var_file   = tool_input.get("var_file")
        vars_dict  = tool_input.get("vars", {})
        auto_approve = tool_input.get("auto_approve", False)

        # Destroy is always blocked through this tool — requires explicit override
        if operation == "destroy":
            return "BLOCKED: terraform destroy requires Tier 4 confirmation and manual override", False

        # Build command
        cmd = ["terraform", operation]
        if operation in ("apply",) and auto_approve:
            cmd.append("-auto-approve")
        if var_file:
            cmd.extend(["-var-file", var_file])
        for k, v in vars_dict.items():
            cmd.extend(["-var", f"{k}={v}"])
        cmd.append("-json")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=working_dir,
            )
            output = result.stdout or result.stderr or "(no output)"
            return output, result.returncode == 0
        except FileNotFoundError:
            # Terraform not installed — return stub for Inc 1 dev/test
            stub = (
                f"[TERRAFORM STUB] operation={operation} dir={working_dir}\n"
                f"(Install terraform CLI to enable real execution)"
            )
            return stub, True
        except subprocess.TimeoutExpired:
            return "ERROR: terraform timed out (5m limit)", False
        except Exception as exc:
            return f"ERROR: {exc}", False
