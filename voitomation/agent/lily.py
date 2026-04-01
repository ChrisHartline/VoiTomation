"""
Lily — VoiTomation AI Agent.

Lily is a Claude-powered agent that:
  1. Extracts structured intent from Chris's utterance.
  2. Generates a step-by-step execution plan.
  3. Passes the plan through the Governance Gate.
  4. Requests confirmation from Chris if the tier requires it.
  5. Executes approved steps using tools (Linux, GCP, Terraform).
  6. Writes every event to Blockchain B (audit ledger).

Lily holds NO independent permissions. She acts as an authenticated
proxy for Chris — the session token carries Chris's authorization.
"""

from __future__ import annotations

import json
from typing import Any

import anthropic
import structlog

from voitomation.agent.intent import Intent, ExecutionPlan
from voitomation.agent.tools.linux import LinuxTool
from voitomation.agent.tools.gcp import GCPTool
from voitomation.agent.tools.terraform import TerraformTool
from voitomation.auth.session import Session
from voitomation.governance.gate import GovernanceGate, GateVerdict
from voitomation.governance.tiers import Tier, requires_confirmation, confirmation_prompt
from voitomation.ledger.blockchain_b import AuditLedger, EventType
from voitomation.config import LILY_MODEL

log = structlog.get_logger()

# ── System prompt ──────────────────────────────────────────────────────────

LILY_SYSTEM_PROMPT = """You are Lily, an AI infrastructure assistant for VoiTomation.

Your role:
- Help Chris (the human operator) manage GCP infrastructure and Linux systems.
- You hold no independent permissions. You act on behalf of Chris using his session token.
- Before taking any action, you MUST produce a structured intent object and a structured
  execution plan. Never execute without a plan.
- You are an expert tutor: explain what you're doing, why, and what the effect will be.
  Chris is learning while you work together.

When responding to a command:
1. Parse the utterance into a structured intent (use the `parse_intent` tool).
2. Generate an execution plan (use the `generate_plan` tool).
3. The governance gate will validate your plan — you do not call it directly.
4. If the plan is approved and tier allows, execute step by step (use execution tools).
5. After each step, briefly explain the outcome in plain language.

Safety rules you must never violate:
- Never execute a step that was not in the approved plan.
- Never access resources outside the scope declared in the intent.
- If a step fails unexpectedly, STOP and report to Chris. Do not improvise.
- Always include a rollback plan for any deployment action.

You are both capable and careful. When in doubt, ask Chris rather than guess.
"""


class Lily:
    """
    Main agent entry point.

    Usage:
        session = Session(user_id="chris", token="...", tier_granted=Tier.WRITE)
        lily = Lily(session)
        result = await lily.handle("deploy app-v2.1 to staging")
    """

    def __init__(self, session: Session, ledger: AuditLedger, gate: GovernanceGate):
        self._session = session
        self._ledger  = ledger
        self._gate    = gate
        self._client  = anthropic.Anthropic()

        # Tool instances
        self._linux_tool = LinuxTool()
        self._gcp_tool   = GCPTool()
        self._tf_tool    = TerraformTool()

        # Tool definitions passed to Claude
        self._tool_defs = [
            self._linux_tool.definition(),
            self._gcp_tool.definition(),
            self._tf_tool.definition(),
            _parse_intent_tool_def(),
            _generate_plan_tool_def(),
        ]

    def handle(self, utterance: str) -> dict[str, Any]:
        """
        Process one utterance from Chris end-to-end.
        Returns a result dict with outcome and audit entry hash.
        """
        log.info("lily.handle", utterance=utterance, user=self._session.user_id)

        # ── Step 1: Log the incoming utterance ────────────────────────────
        auth_entry = self._ledger.append(EventType.VOICE_AUTH, {
            "user_id":    self._session.user_id,
            "confidence": self._session.auth_confidence,
            "tier_granted": int(self._session.tier_granted),
        })

        # ── Step 2: Run Lily's agentic loop ───────────────────────────────
        messages: list[dict] = [{"role": "user", "content": utterance}]
        intent: Intent | None = None
        plan: ExecutionPlan | None = None

        while True:
            response = self._client.messages.create(
                model=LILY_MODEL,
                max_tokens=4096,
                system=LILY_SYSTEM_PROMPT,
                tools=self._tool_defs,
                messages=messages,
                thinking={"type": "adaptive"},
            )

            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "end_turn":
                break

            if response.stop_reason != "tool_use":
                break

            # ── Process tool calls ───────────────────────────────────────
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue

                tool_name  = block.name
                tool_input = block.input
                result_text, success = self._dispatch_tool(
                    tool_name, tool_input, intent, plan
                )

                # Capture structured objects from meta-tools
                if tool_name == "parse_intent" and success:
                    intent = Intent.from_dict(json.loads(result_text))
                    self._ledger.append(EventType.INTENT, intent.to_dict())

                elif tool_name == "generate_plan" and success:
                    plan = ExecutionPlan.from_dict(json.loads(result_text))
                    plan_entry = self._ledger.append(EventType.PLAN, plan.to_dict())

                    # ── Governance Gate (before any execution) ────────────
                    if intent is None:
                        result_text = "ERROR: plan generated before intent was parsed"
                        success = False
                    else:
                        gate_result = self._gate.evaluate(
                            self._session.user_id, intent.to_dict(), plan.to_dict()
                        )
                        self._ledger.append(EventType.GOVERNANCE, {
                            "verdict": gate_result.verdict.value,
                            "reasons": gate_result.reasons,
                            "plan_hash": plan_entry.entry_hash,
                        })

                        if gate_result.verdict == GateVerdict.BLOCK:
                            result_text = (
                                f"GOVERNANCE BLOCKED: {'; '.join(gate_result.reasons)}"
                            )
                            success = False

                        elif gate_result.verdict == GateVerdict.MODIFY:
                            result_text = (
                                f"GOVERNANCE MODIFY: {'; '.join(gate_result.reasons)}. "
                                f"Revise the plan and resubmit."
                            )
                            success = False

                        else:
                            # ── Tier check: ask Chris if needed ──────────
                            if requires_confirmation(intent.tier):
                                confirmed = self._ask_confirmation(intent, plan)
                                if confirmed:
                                    self._ledger.append(EventType.CONFIRMATION, {
                                        "user_id": self._session.user_id,
                                        "tier": int(intent.tier),
                                    })
                                    result_text = json.dumps(plan.to_dict())
                                else:
                                    self._ledger.append(EventType.DENIED, {
                                        "reason": "User declined confirmation"
                                    })
                                    result_text = "User declined confirmation. Aborting."
                                    success = False
                            else:
                                result_text = json.dumps(plan.to_dict())

                elif tool_name in ("linux_exec", "gcp_query", "terraform_apply"):
                    self._ledger.append(EventType.EXEC_STEP, {
                        "tool": tool_name,
                        "input": tool_input,
                        "output": result_text[:500],  # truncate large outputs
                        "success": success,
                    })

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_text,
                    "is_error": not success,
                })

            messages.append({"role": "user", "content": tool_results})

        # ── Step 3: Extract final text response ───────────────────────────
        final_text = next(
            (b.text for b in response.content if hasattr(b, "text")), ""
        )

        outcome_entry = self._ledger.append(EventType.OUTCOME, {
            "final_response": final_text[:1000],
            "success": True,
        })

        return {
            "response":     final_text,
            "outcome_hash": outcome_entry.entry_hash,
            "audit_chain":  self._ledger.verify_chain(),
        }

    def _dispatch_tool(
        self,
        tool_name: str,
        tool_input: dict,
        intent: Intent | None,
        plan: ExecutionPlan | None,
    ) -> tuple[str, bool]:
        """Route a tool call to the correct handler. Returns (result_text, success)."""
        try:
            if tool_name == "parse_intent":
                # Lily populates this; we just pass it back as structured data
                return json.dumps(tool_input), True

            elif tool_name == "generate_plan":
                return json.dumps(tool_input), True

            elif tool_name == "linux_exec":
                return self._linux_tool.run(tool_input)

            elif tool_name == "gcp_query":
                return self._gcp_tool.run(tool_input)

            elif tool_name == "terraform_apply":
                return self._tf_tool.run(tool_input)

            else:
                return f"Unknown tool: {tool_name}", False

        except Exception as exc:
            log.exception("tool.error", tool=tool_name)
            return f"Tool error: {exc}", False

    def _ask_confirmation(self, intent: Intent, plan: ExecutionPlan) -> bool:
        """
        Prompt Chris for confirmation (text-based in Inc 1;
        voice phrase in Inc 2; QRNG challenge in Inc 3).
        """
        summary = "\n".join(
            f"  {s['step']}. [{s['tool']}] {s['action']}"
            for s in plan.steps
        )
        prompt = confirmation_prompt(intent.tier, summary)
        response = input(prompt).strip().lower()

        if intent.tier == 4:
            return response == "confirm delete"
        return response == "confirm"


# ── Meta-tool definitions (parse_intent and generate_plan) ────────────────

def _parse_intent_tool_def() -> dict:
    return {
        "name": "parse_intent",
        "description": (
            "Parse the user's utterance into a structured intent object. "
            "You MUST call this before generate_plan or any execution tool."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "action":      {"type": "string", "description": "Primary action: deploy|create|delete|query|list|update|..."},
                "target":      {"type": "string", "description": "Resource name, app, or service being acted upon"},
                "environment": {"type": "string", "description": "Target environment: staging|production|dev|..."},
                "scope":       {"type": "array", "items": {"type": "string"}, "description": "GCP resource paths in scope"},
                "constraints": {"type": "array", "items": {"type": "string"}, "description": "Constraints on the plan"},
                "tier":        {"type": "integer", "description": "Confirmation tier 1-4 (classify based on risk)"},
                "raw_utterance": {"type": "string", "description": "The original utterance verbatim"},
            },
            "required": ["action", "target", "tier", "raw_utterance"],
        },
    }


def _generate_plan_tool_def() -> dict:
    return {
        "name": "generate_plan",
        "description": (
            "Generate a structured execution plan for the approved intent. "
            "Must include rollback steps for any deployment action. "
            "The plan will be validated by the Governance Gate before execution."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "steps": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "step":   {"type": "integer"},
                            "tool":   {"type": "string"},
                            "action": {"type": "string"},
                        },
                        "required": ["step", "tool", "action"],
                    },
                    "description": "Ordered steps of the execution plan",
                },
                "rollback": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "step":   {"type": "integer"},
                            "tool":   {"type": "string"},
                            "action": {"type": "string"},
                        },
                    },
                    "description": "Rollback steps in case of failure",
                },
                "estimated_cost": {
                    "type": "string",
                    "description": "Estimated cost or resource impact of the plan",
                },
            },
            "required": ["steps"],
        },
    }
