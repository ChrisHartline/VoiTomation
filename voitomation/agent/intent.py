"""
Intent extraction helpers.

The structured intent object is the contract between:
  - What Chris said  (natural language utterance)
  - What Lily plans  (execution plan)
  - What the gate validates (governance rules)

Format:
{
    "action":       str,          # deploy | query | create | delete | list | ...
    "target":       str,          # resource name / app / service
    "environment":  str,          # staging | production | dev | ...
    "scope":        list[str],    # GCP resource paths or wildcard
    "constraints":  list[str],    # no-iam-changes | no-production | ...
    "tier":         int,          # 1-4 (auto-classified)
    "raw_utterance": str          # original text from Chris
}
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from voitomation.governance.tiers import Tier, classify


@dataclass
class Intent:
    action:       str
    target:       str
    environment:  str
    scope:        list[str]
    constraints:  list[str]
    tier:         Tier
    raw_utterance: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "action":       self.action,
            "target":       self.target,
            "environment":  self.environment,
            "scope":        self.scope,
            "constraints":  self.constraints,
            "tier":         int(self.tier),
            "raw_utterance": self.raw_utterance,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Intent":
        return cls(
            action=d["action"],
            target=d["target"],
            environment=d.get("environment", ""),
            scope=d.get("scope", []),
            constraints=d.get("constraints", []),
            tier=Tier(d.get("tier", 3)),
            raw_utterance=d.get("raw_utterance", ""),
        )


@dataclass
class ExecutionPlan:
    steps: list[dict[str, Any]]
    rollback: list[dict[str, Any]] = field(default_factory=list)
    estimated_cost: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "steps": self.steps,
            "rollback": self.rollback,
            "estimated_cost": self.estimated_cost,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ExecutionPlan":
        return cls(
            steps=d.get("steps", []),
            rollback=d.get("rollback", []),
            estimated_cost=d.get("estimated_cost", ""),
        )
