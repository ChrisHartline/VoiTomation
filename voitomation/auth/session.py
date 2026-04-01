"""
Session — represents an authenticated user session.

Inc 1: simple dataclass with stub auth confidence.
Inc 2: short-lived JWT minted from voice auth event.
Inc 3: JWT derived from quantum-enhanced biometric verification.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from voitomation.governance.tiers import Tier


@dataclass
class Session:
    user_id:         str
    auth_confidence: float      # 0.0–1.0 (voice biometric confidence score)
    tier_granted:    Tier       # max tier this session is authorized for
    created_at:      float = field(default_factory=time.time)
    expires_at:      float = field(default_factory=lambda: time.time() + 3600)
    token:           str = ""   # Inc 2: JWT; Inc 1: stub

    @property
    def is_valid(self) -> bool:
        return time.time() < self.expires_at and self.auth_confidence >= 0.7

    @classmethod
    def stub(cls, user_id: str = "chris") -> "Session":
        """
        Create a stub session for Inc 1 development.
        Replace with real voice auth in Inc 2.
        """
        return cls(
            user_id=user_id,
            auth_confidence=0.99,  # stub: assume perfect confidence
            tier_granted=Tier.RISKY,  # default: allow up to Tier 3
        )
