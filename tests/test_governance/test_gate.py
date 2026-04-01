"""Tests for the Governance Gate."""

import pytest

from voitomation.governance.gate import GovernanceGate, GateVerdict
from voitomation.ledger.blockchain_a import PermissionStore


@pytest.fixture
def gate(tmp_path):
    # Write a minimal permissions YAML for tests
    perm_file = tmp_path / "permissions.yaml"
    perm_file.write_text("""
users:
  chris:
    roles: [operator]
    permissions:
      - resource: "*"
        actions: [list, query, read]
        tier: 1
      - resource: "gcp:projects/*/services/*"
        actions: ["deploy:staging"]
        tier: 2
""")
    store = PermissionStore(path=perm_file)
    return GovernanceGate(store)


def test_authorized_read_passes(gate):
    intent = {"action": "list", "scope": ["gcp:projects/my-proj/services/app"]}
    plan   = {"steps": [{"step": 1, "tool": "gcp_query", "action": "list services"}]}
    result = gate.evaluate("chris", intent, plan)
    assert result.verdict == GateVerdict.PASS


def test_unauthorized_user_blocked(gate):
    intent = {"action": "deploy:staging", "scope": ["gcp:projects/*/services/*"]}
    plan   = {"steps": [], "rollback": []}
    result = gate.evaluate("unknown_user", intent, plan)
    assert result.verdict == GateVerdict.BLOCK


def test_scope_violation_blocked(gate):
    intent = {"action": "deploy:staging", "environment": "staging",
              "scope": ["gcp:projects/*/services/*"]}
    # Plan references production despite staging intent
    plan = {
        "steps": [{"step": 1, "tool": "terraform_apply",
                   "action": "deploy app to production"}],
        "rollback": [{"step": 1, "tool": "terraform_apply", "action": "rollback"}],
    }
    result = gate.evaluate("chris", intent, plan)
    assert result.verdict == GateVerdict.BLOCK


def test_missing_rollback_modify(gate):
    intent = {"action": "deploy:staging", "environment": "staging",
              "scope": ["gcp:projects/*/services/*"]}
    plan = {
        "steps": [{"step": 1, "tool": "terraform_apply", "action": "deploy to staging"}],
        # no rollback key
    }
    result = gate.evaluate("chris", intent, plan)
    assert result.verdict == GateVerdict.MODIFY
