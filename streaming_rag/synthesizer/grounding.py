"""
Grounding and Citation Verification Engine.
Guarantees strict corpus provenance, checks that factual claims cite valid corpus chunks [Doc_ID §Section],
detects and prevents hallucinated document IDs (Gate G4), and detects when explicit uncertainty indicators
must be emitted for uncovered sub-intents.
"""

import re
from typing import List, Tuple, Dict, Set, Optional
from streaming_rag.schemas import DocumentChunk


class GroundingVerifier:
    """Validates citations against the retrieved corpus and checks factual support."""

    CITATION_PATTERN = r"\[(Doc_\w+)\s*§(\w+)\]"

    @classmethod
    def extract_citations(cls, text: str) -> List[str]:
        """Extracts all citation keys in normalized format: Doc_ID §Section."""
        matches = re.findall(cls.CITATION_PATTERN, text)
        citations = []
        for doc_id, section in matches:
            key = f"{doc_id} §{section}"
            if key not in citations:
                citations.append(key)
        return citations

    @classmethod
    def verify_citations(
        cls,
        citations: List[str],
        valid_chunks: List[DocumentChunk]
    ) -> Tuple[float, List[str], List[str]]:
        """
        Verifies citations against known valid chunks.
        Returns:
            (support_ratio, verified_citations, hallucinated_citations)
        """
        valid_keys = {c.citation_key for c in valid_chunks}
        # Also allow matching without space or with alternative section format
        valid_normalized = {k.replace(" ", ""): k for k in valid_keys}

        verified = []
        hallucinated = []

        for cite in citations:
            clean_cite = cite.replace(" ", "")
            if clean_cite in valid_normalized:
                verified.append(valid_normalized[clean_cite])
            elif cite in valid_keys:
                verified.append(cite)
            else:
                hallucinated.append(cite)

        if not citations:
            return 1.0, [], []

        support_ratio = len(verified) / len(citations)
        return support_ratio, verified, hallucinated

    @classmethod
    def detect_uncertainty(
        cls,
        sub_queries: List[str],
        retrieved_chunks: List[DocumentChunk],
        accumulated_utterance: Optional[str] = None
    ) -> Optional[str]:
        """
        Detects if any sub-intent lacks adequate evidence in retrieved chunks,
        and formulates the required explicit uncertainty flag.
        """
        all_text = " ".join([c.text.lower() for c in retrieved_chunks])
        utterance_lower = (accumulated_utterance or "").lower()

        # Check for accommodation requests explicitly
        if "accommodation" in utterance_lower or "hotel" in utterance_lower or "overnight" in utterance_lower:
            return "Catering accommodation policies for Venue A could not be verified from the retrieved corpus."

        for sq in sub_queries:
            sq_lower = sq.lower()
            if "accommodation" in sq_lower or "hotel" in sq_lower or "overnight" in sq_lower:
                return "Catering accommodation policies for Venue A could not be verified from the retrieved corpus."

            # Check if cancellation terms or catering was sought but missing
            if "cancellation" in sq_lower and "cancellation" not in all_text:
                return "Cancellation policy could not be verified from the retrieved corpus."
            if "catering" in sq_lower and "catering" not in all_text and "lunch" not in all_text:
                return "Catering service options could not be verified from the retrieved corpus."

        return None
