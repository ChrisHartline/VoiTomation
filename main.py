"""
VoiTomation — CLI entry point (Inc 1).

Usage:
    python main.py

In Inc 1, voice input is simulated with text. The full pipeline
(voice auth → intent → plan → governance → execution → audit) runs end-to-end.
"""

import sys
import structlog

from voitomation.auth.voice import VoiceAuthService
from voitomation.ledger.blockchain_a import PermissionStore
from voitomation.ledger.blockchain_b import AuditLedger
from voitomation.governance.gate import GovernanceGate
from voitomation.agent.lily import Lily

log = structlog.get_logger()


def main():
    print("=" * 60)
    print("  VoiTomation — Voice + Automation (Inc 1)")
    print("  Type 'exit' to quit. Type 'verify' to check audit chain.")
    print("=" * 60)

    # Bootstrap components
    auth_service  = VoiceAuthService()
    permissions   = PermissionStore()
    ledger        = AuditLedger()
    gate          = GovernanceGate(permissions)

    # Authenticate Chris
    session = auth_service.authenticate("chris")
    if not session or not session.is_valid:
        print("Authentication failed. Exiting.")
        sys.exit(1)

    lily = Lily(session=session, ledger=ledger, gate=gate)

    print(f"\nSession active for: {session.user_id}")
    print("Lily is ready. What would you like to do?\n")

    while True:
        try:
            utterance = input("Chris → Lily: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSession ended.")
            break

        if not utterance:
            continue

        if utterance.lower() == "exit":
            print("Session ended.")
            break

        if utterance.lower() == "verify":
            intact = ledger.verify_chain()
            print(f"Audit chain integrity: {'✅ INTACT' if intact else '❌ TAMPERED'}")
            for entry in ledger.tail(5):
                print(f"  [{entry.id}] {entry.event_type:20s} {entry.entry_hash[:16]}...")
            continue

        # Run through the full pipeline
        print()
        result = lily.handle(utterance)
        print(f"\nLily: {result['response']}")
        print(f"[Audit hash: {result['outcome_hash'][:20]}... | Chain: {'✅' if result['audit_chain'] else '❌'}]")
        print()


if __name__ == "__main__":
    main()
