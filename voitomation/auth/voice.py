"""
Voice Auth Service.

Inc 1: stub (text input, no biometrics).
Inc 2: SpeechBrain x-vector speaker verification + Google STT.
Inc 3: Quantum PQC kernel + HDC voiceprint + QRNG challenge.
"""

from __future__ import annotations

import time

from voitomation.auth.session import Session
from voitomation.governance.tiers import Tier
from voitomation.config import VOICE_AUTH_BACKEND


class VoiceAuthService:
    """
    Authenticates a speaker and returns a Session.

    All backends produce the same Session object — the rest of the
    system is backend-agnostic.
    """

    def authenticate(self, user_id: str) -> Session | None:
        """
        Attempt to authenticate the user.
        Returns a Session on success, None on failure.
        """
        backend = VOICE_AUTH_BACKEND

        if backend == "stub":
            return self._stub_auth(user_id)
        elif backend == "speechbrain":
            return self._speechbrain_auth(user_id)   # Inc 2
        elif backend == "quantum":
            return self._quantum_auth(user_id)        # Inc 3
        else:
            raise ValueError(f"Unknown voice auth backend: {backend}")

    def _stub_auth(self, user_id: str) -> Session:
        """
        Inc 1 stub: accept any user_id, confidence = 1.0.
        The stub prompts for text input to simulate the voice interaction.
        """
        print(f"\n[VOICE AUTH STUB] Authenticating '{user_id}'")
        print("In Inc 2, this will capture microphone input and verify your voiceprint.")
        print(f"Session granted for user: {user_id}\n")
        return Session.stub(user_id=user_id)

    def _speechbrain_auth(self, user_id: str) -> Session | None:
        """
        Inc 2: SpeechBrain x-vector speaker verification.
        TODO: implement in Inc 2.
        """
        raise NotImplementedError("SpeechBrain auth not implemented — target Inc 2")

    def _quantum_auth(self, user_id: str) -> Session | None:
        """
        Inc 3: Quantum PQC kernel + HDC + QRNG challenge.
        TODO: implement in Inc 3.
        """
        raise NotImplementedError("Quantum auth not implemented — target Inc 3")
