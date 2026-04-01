"""
Action tier classification.

Tiers determine what confirmation is required before execution:

  Tier 1 — Read/query:           auto-proceed, no confirmation
  Tier 2 — Non-destructive write: Lily presents plan; implicit proceed
  Tier 3 — Risky/costly:         explicit voice confirmation required
  Tier 4 — Destructive/irreversible: QRNG challenge + time delay (Inc 3)
"""

from enum import IntEnum
import re


class Tier(IntEnum):
    READ            = 1
    WRITE           = 2
    RISKY           = 3
    DESTRUCTIVE     = 4


# Keywords that signal risky or destructive intent in a plan action string.
_TIER4_PATTERNS = [
    r"\bdelete\b", r"\bdrop\b", r"\bdestroy\b", r"\bremove\b",
    r"\biam\b", r"\bpermission\b", r"\boverride\b", r"\bforce\b",
]

_TIER3_PATTERNS = [
    r"\bproduction\b", r"\bprod\b", r"\btransaction\b", r"\bpay\b",
    r"\bbilling\b", r"\bscale.*up\b", r"\bexpensive\b", r"\bcost\b",
]

_TIER2_PATTERNS = [
    r"\bdeploy\b", r"\bapply\b", r"\bcreate\b", r"\bupdate\b",
    r"\bprovision\b", r"\bstaging\b", r"\bwrite\b",
]


def classify(action_description: str) -> Tier:
    """
    Classify a free-text action description into a tier.
    Conservative: defaults to Tier 3 if ambiguous.
    """
    text = action_description.lower()

    for pattern in _TIER4_PATTERNS:
        if re.search(pattern, text):
            return Tier.DESTRUCTIVE

    for pattern in _TIER3_PATTERNS:
        if re.search(pattern, text):
            return Tier.RISKY

    for pattern in _TIER2_PATTERNS:
        if re.search(pattern, text):
            return Tier.WRITE

    # Pure read/query actions
    if re.search(r"\b(list|get|read|query|show|describe|status|log)\b", text):
        return Tier.READ

    return Tier.RISKY  # unknown → err on the side of caution


def requires_confirmation(tier: Tier) -> bool:
    return tier >= Tier.RISKY


def confirmation_prompt(tier: Tier, plan_summary: str) -> str:
    if tier == Tier.DESTRUCTIVE:
        return (
            f"⚠️  DESTRUCTIVE ACTION REQUIRED\n\n"
            f"{plan_summary}\n\n"
            f"Type 'CONFIRM DELETE' to proceed, or anything else to abort: "
        )
    return (
        f"Lily's plan:\n{plan_summary}\n\n"
        f"Type 'confirm' to proceed, or anything else to abort: "
    )
