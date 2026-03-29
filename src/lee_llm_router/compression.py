"""Optional prompt compression hook.

Phase 0: pass-through stub. The interface is preserved so Phase 1/2 can
replace the body without touching any callers.
"""

from __future__ import annotations


def compress(messages: list[dict]) -> list[dict]:
    """Return messages unchanged. Replace with real compression in Phase 1/2."""
    return messages
