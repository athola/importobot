"""Evidence evaluation for format detection scores."""

from __future__ import annotations


class EvidenceEvaluator:
    """Evaluates format detection scores and maps them to evidence levels.

    Score Ranges and Meanings:
    - 0-3: INSUFFICIENT evidence (format unknown)
    - 4-6: MODERATE evidence (possible format match)
    - 7+: STRONG evidence (confident format match)
    """

    @staticmethod
    def evaluate_total_score(score: int) -> str:
        """Convert numeric score to evidence level description."""
        if score >= 7:
            return "STRONG"
        if score >= 4:
            return "MODERATE"
        return "INSUFFICIENT"

    @staticmethod
    def is_sufficient_for_detection(score: int) -> bool:
        """Check if score indicates sufficient evidence for format detection."""
        return score >= 4


__all__ = ["EvidenceEvaluator"]
