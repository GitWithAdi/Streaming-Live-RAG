"""
Query suppression detector for presentation-only, restructuring, and formatting turns.
Prevents unneeded corpus queries when user simply requests presentation changes to existing context.
"""

import re
from typing import Tuple

PRESENTATION_PATTERNS = [
    r"\b(repeat|rephrase|rewrite|format|restructure|convert|summarize)\b.*?\b(bullet|bullets|point|points|table|short|concise)\b",
    r"\b(in|into)\s+(two|three|four|\d+)\s+bullets?\b",
    r"\b(make\s+it\s+(shorter|briefer|more\s+concise|longer|simpler))\b",
    r"\b(repeat\s+your\s+last\s+(answer|response))\b",
    r"\b(put\s+that\s+in\s+a\s+(table|list|bullet\s+points))\b",
    r"\b(summarize\s+(the\s+)?above)\b",
    r"\b(translate\s+(that|the\s+above|your\s+answer)\s+to)\b",
]


class PresentationSuppressionDetector:
    """Detects whether a user turn is a presentation transformation that does not require retrieval."""

    @staticmethod
    def evaluate(text: str, has_prior_context: bool = False) -> Tuple[bool, str, float]:
        """
        Returns (is_suppressed, reason, confidence).
        is_suppressed = True means NO retrieval required.
        """
        if not has_prior_context:
            return False, "no_prior_context_to_reformat", 0.0

        cleaned = text.strip().lower()
        for pattern in PRESENTATION_PATTERNS:
            if re.search(pattern, cleaned):
                return True, "presentation_restructure", 0.95

        # Check for concise formatting commands
        if cleaned.startswith("in bullets") or cleaned.startswith("bullet points please"):
            return True, "presentation_restructure", 0.90

        return False, "retrieval_eligible", 0.0
