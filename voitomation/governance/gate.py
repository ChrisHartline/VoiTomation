"""
Governance Gate — validates execution plans before any tool runs.

The gate is architecturally INDEPENDENT from Lily (the planning agent).
It uses deterministic OPA/Rego rules, not an LLM — so Lily's hallucinations
or prompt injection cannot bypass it.

Inc 1: inline Python rules (OPA integration stubbed).
Inc 2: full OPA/Rego evaluation via REST API.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any

import structlog

from voitomation.ledger.blockchain_a import PermissionStore

log = structlog.get_logger()


class GateVerdict(str, Enum):
    PASS    = "pass"
    MODIFY  = "modify"   # plan needs adjustment
    BLOCK   = "block"


@dataclass
class GateResult:
    verdict: GateVerdict
    reasons: list[str]       # why this verdict was reached
    modified_plan: dict | None = None


class GovernanceGate:
    """
    Validates an execution plan against:
      1. IAM / permission policy (from Blockchain A)
      2. Scope constraints (plan must not exceed declared intent scope)
      3. SOP compliance (required steps present)
      4. Resource existence (not yet implemented — needs live GCP API)

    The gate returns a GateResult. If verdict == BLOCK, Lily must not execute.
    If MODIFY, Lily revises the plan and re-submits.
    """

    def __init__(self, permission_store: PermissionStore):
        self._perms = permission_store

    def evaluate(
        self,
        user_id: str,
        intent: dict[str, Any],
        plan: dict[str, Any],
    ) -> GateResult:
        """
        Evaluate a plan against all governance rules.

        Args:
            user_id: authenticated user (e.g. "chris")
            intent:  structured intent object from Lily
            plan:    structured execution plan from Lily

        Returns:
            GateResult with PASS, MODIFY, or BLOCK verdict.
        """
        reasons: list[str] = []

        # ── Rule 1: IAM / permission check ──────────────────────────────
        action   = intent.get("action", "")
        resource = intent.get("scope", ["*"])[0] if intent.get("scope") else "*"

        if not self._perms.is_authorized(user_id, action, resource):
            log.warning("governance.iam_block", user=user_id, action=action, resource=resource)
            return GateResult(
                verdict=GateVerdict.BLOCK,
                reasons=[f"User '{user_id}' is not authorized for action '{action}' on '{resource}'"],
            )

        # ── Rule 2: Scope constraint — plan must not exceed intent scope ─
        scope_issues = self._check_scope(intent, plan)
        if scope_issues:
            reasons.extend(scope_issues)
            return GateResult(verdict=GateVerdict.BLOCK, reasons=reasons)

        # ── Rule 3: SOP compliance (basic checks) ────────────────────────
        sop_issues = self._check_sop(intent, plan)
        if sop_issues:
            reasons.extend(sop_issues)
            # SOP failures are MODIFY (Lily can revise), not BLOCK
            return GateResult(verdict=GateVerdict.MODIFY, reasons=reasons)

        log.info("governance.pass", user=user_id, action=action)
        return GateResult(verdict=GateVerdict.PASS, reasons=["All governance checks passed"])

    def _check_scope(self, intent: dict, plan: dict) -> list[str]:
        """
        Verify the plan does not reference resources outside the declared scope.
        Inc 1: simple keyword-based check.
        """
        issues: list[str] = []
        declared_env = intent.get("environment", "")
        steps = plan.get("steps", [])

        if declared_env == "staging":
            for step in steps:
                action_text = (step.get("action") or "").lower()
                if "production" in action_text or "prod" in action_text:
                    issues.append(
                        f"Step {step.get('step')}: plan references 'production' "
                        f"but intent declared environment=staging"
                    )

        return issues

    def _check_sop(self, intent: dict, plan: dict) -> list[str]:
        """
        Verify required SOP steps are present.
        Inc 1: deployments must include a rollback plan.
        """
        issues: list[str] = []
        if intent.get("action") in ("deploy", "apply"):
            if not plan.get("rollback"):
                issues.append("Deployment plan missing required rollback steps (SOP violation)")
        return issues
