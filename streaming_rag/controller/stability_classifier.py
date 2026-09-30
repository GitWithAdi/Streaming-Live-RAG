"""
Real-time Intent Stability Classifier and Retrieval Controller.
Evaluates incoming transcript chunks to balance early retrieval latency gains
against premature, noisy searches triggered by incomplete thoughts.
"""

import re
from typing import List, Dict, Any, Tuple, Optional
from streaming_rag.schemas import ControllerDecision
from streaming_rag.controller.suppression_detector import PresentationSuppressionDetector
from streaming_rag.config import RetrievalControllerConfig


TRAILING_DANGLERS = [
    r"\b(in|at|to|for|with|by|on|about|from|into|of)\s*\.{0,3}$",
    r"\b(and|or|but|because|if|when|that|which)\s*\.{0,3}$",
    r"\b(and\s+i\s+need|and\s+also|and\s+we\s+need)\s*\.{0,3}$",
    r"\b(i\s+need\s+to|i\s+want\s+to|can\s+you)\s*\.{0,3}$",
]

ENTITY_PATTERNS = {
    "location": r"\b(pune|mumbai|bangalore|delhi|hyderabad|chennai|international|domestic|overseas)\b",
    "capacity_number": r"\b(\d{1,4})\s*(people|attendees|delegates|persons|pax|seats)?\b",
    "event_type": r"\b(workshop|conference|seminar|meeting|trip|travel|flight|hotel|booking)\b",
    "policy_domain": r"\b(cancellation|refund|reimbursement|per[- ]diem|expense|catering|food|meal|av|equipment)\b",
    "exception_terms": r"\b(international|after\s+travel|late[- ]booking|retroactive|director\s+approval)\b",
}

COMPOUND_MARKERS = [
    r"\b(cancellation\s+policy|refund\s+terms?)\b",
    r"\b(catering\s+options?|meal\s+packages?|food\s+options?)\b",
    r"\b(venue\s+capacity|room\s+capacity|seating)\b",
    r"\b(and\s+the|as\s+well\s+as|along\s+with|in\s+addition\s+to)\b",
]


class RetrievalController:
    """Evaluates transcript stream in real-time to emit Wait | Retrieve | No-Retrieval decisions."""

    def __init__(self, config: Optional[RetrievalControllerConfig] = None):
        self.config = config or RetrievalControllerConfig()
        self.suppression_detector = PresentationSuppressionDetector()

    def extract_entities(self, text: str) -> List[str]:
        """Extracts recognizable semantic entities from text."""
        entities = []
        lower = text.lower()
        for cat, pattern in ENTITY_PATTERNS.items():
            matches = re.findall(pattern, lower)
            if matches:
                for m in matches:
                    if isinstance(m, tuple):
                        entity_str = " ".join([part for part in m if part]).strip()
                    else:
                        entity_str = str(m).strip()
                    if entity_str and entity_str not in entities:
                        entities.append(entity_str)
        return entities

    def is_dangling(self, text: str) -> bool:
        """Checks whether the text ends with an incomplete preposition or conjunction."""
        cleaned = text.strip().rstrip(".").strip()
        for pat in TRAILING_DANGLERS:
            if re.search(pat, cleaned, re.IGNORECASE):
                return True
        return False

    def detect_compound_intent(self, text: str) -> bool:
        """Determines if the text contains compound / multi-intent requests."""
        lower = text.lower()
        marker_hits = sum(1 for pat in COMPOUND_MARKERS if re.search(pat, lower))
        return marker_hits >= 2

    def evaluate_chunk(
        self,
        accumulated_text: str,
        current_chunk_text: str,
        timestamp_s: float,
        is_final: bool = False,
        has_prior_context: bool = False,
        prior_retrieval_done: bool = False
    ) -> ControllerDecision:
        """
        Main decision method for incoming streaming chunk.
        Decides:
        - no_retrieval (presentation formatting)
        - wait (semantic instability / incomplete thought)
        - retrieve (stable provisional entities or multi-intent)
        """
        raw_text = accumulated_text.strip()

        # 1. Presentation query suppression check
        if has_prior_context:
            is_suppressed, reason, conf = self.suppression_detector.evaluate(raw_text, has_prior_context=True)
            if is_suppressed:
                return ControllerDecision(
                    action="no_retrieval",
                    confidence=conf,
                    reason=reason,
                    is_compound=False,
                    sub_queries=[]
                )

        # Token count
        tokens = raw_text.split()
        if len(tokens) < self.config.min_tokens_for_intent and not is_final:
            return ControllerDecision(
                action="wait",
                confidence=0.9,
                reason="insufficient_tokens_early_stream",
                extracted_entities=[],
                is_compound=False
            )

        # Entity extraction
        entities = self.extract_entities(raw_text)
        is_compound = self.detect_compound_intent(raw_text)
        dangling = self.is_dangling(raw_text)

        # Check for multi-intent completion
        if is_compound:
            # Multi-intent triggers when compound facets are visible
            return ControllerDecision(
                action="retrieve",
                confidence=0.88,
                reason="multi_intent_detected",
                extracted_entities=entities,
                is_compound=True
            )

        # Check for provisional retrieval
        # If we have stable entities (e.g. Pune, 30 people, workshop)
        if len(entities) >= self.config.min_entities_for_provisional and not prior_retrieval_done:
            return ControllerDecision(
                action="retrieve",
                confidence=0.82,
                reason="provisional_entities_stabilized",
                extracted_entities=entities,
                is_compound=False
            )

        # If sentence is dangling and not final, wait
        if dangling and not is_final:
            return ControllerDecision(
                action="wait",
                confidence=0.85,
                reason="semantic_instability_trailing_conjunction",
                extracted_entities=entities,
                is_compound=False
            )

        # Final transcript chunk handling
        if is_final:
            if not prior_retrieval_done and len(tokens) >= 3:
                return ControllerDecision(
                    action="retrieve",
                    confidence=0.90,
                    reason="final_transcript_boundary",
                    extracted_entities=entities,
                    is_compound=is_compound
                )
            return ControllerDecision(
                action="wait",
                confidence=0.95,
                reason="utterance_end_ready_for_synthesis",
                extracted_entities=entities,
                is_compound=is_compound
            )

        return ControllerDecision(
            action="wait",
            confidence=0.70,
            reason="stabilizing_context",
            extracted_entities=entities,
            is_compound=False
        )
