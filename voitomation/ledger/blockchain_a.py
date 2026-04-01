"""
Blockchain A — Identity & Permissions store.

Inc 1: YAML file (read-only at runtime — no writes, ever).
Inc 2: Hyperledger Fabric permissioned ledger.

Schema (permissions.yaml):
  users:
    chris:
      display_name: "Christopher Hartline"
      roles: [operator, admin]
      permissions:
        - resource: "*"
          actions: [read, query, list]        # Tier 1 always allowed
        - resource: "gcp:projects/*/services/*"
          actions: [deploy:staging]            # Tier 2
        - resource: "gcp:projects/*/services/*"
          actions: [deploy:production]         # Tier 3 — requires confirmation
          requires_confirmation: true
        - resource: "gcp:*"
          actions: [iam:modify, delete]        # Tier 4 — QRNG challenge
          requires_confirmation: true
          tier: 4
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from voitomation.config import PERMISSIONS_FILE


class PermissionStore:
    """
    Read-only permission store (Blockchain A stub).

    Never written to at runtime. Only the enrollment authority
    can update the underlying YAML / Fabric ledger.
    """

    def __init__(self, path: Path = PERMISSIONS_FILE):
        self._path = path
        self._data: dict[str, Any] = self._load()

    def _load(self) -> dict[str, Any]:
        if not self._path.exists():
            return {"users": {}}
        with open(self._path) as f:
            return yaml.safe_load(f) or {"users": {}}

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        return self._data.get("users", {}).get(user_id)

    def get_roles(self, user_id: str) -> list[str]:
        user = self.get_user(user_id)
        return user.get("roles", []) if user else []

    def get_permissions(self, user_id: str) -> list[dict]:
        user = self.get_user(user_id)
        return user.get("permissions", []) if user else []

    def is_authorized(self, user_id: str, action: str, resource: str) -> bool:
        """
        Simple authorization check.
        Returns True if the user has any permission matching action + resource.
        The governance gate performs the full policy evaluation via OPA.
        """
        for perm in self.get_permissions(user_id):
            res_pattern = perm.get("resource", "")
            actions = perm.get("actions", [])
            if self._matches(res_pattern, resource) and action in actions:
                return True
        return False

    def get_tier(self, user_id: str, action: str, resource: str) -> int:
        """Return the confirmation tier required for this action (1-4)."""
        for perm in self.get_permissions(user_id):
            res_pattern = perm.get("resource", "")
            actions = perm.get("actions", [])
            if self._matches(res_pattern, resource) and action in actions:
                return perm.get("tier", 4 if perm.get("requires_confirmation") else 1)
        return 4  # deny-by-default: unknown action = highest tier

    @staticmethod
    def _matches(pattern: str, resource: str) -> bool:
        """Glob-style pattern matching (* = any segment)."""
        import fnmatch
        return fnmatch.fnmatch(resource, pattern)
