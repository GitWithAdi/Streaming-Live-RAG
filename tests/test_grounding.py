"""
Unit tests for Grounding Verification and Uncertainty Flagging (Gate G4).
"""

from streaming_rag.synthesizer.grounding import GroundingVerifier
from streaming_rag.schemas import DocumentChunk


def test_grounding_verification_valid():
    valid_chunks = [
        DocumentChunk(doc_id="Doc_12", section="§2", title="Pune", text="Venue A capacity 30"),
        DocumentChunk(doc_id="Doc_31", section="§4", title="Cancel", text="80% refund")
    ]

    citations = ["Doc_12 §2", "Doc_31 §4"]
    support_ratio, verified, hallucinated = GroundingVerifier.verify_citations(citations, valid_chunks)

    assert support_ratio == 1.0
    assert len(hallucinated) == 0
    assert len(verified) == 2


def test_grounding_verification_hallucinated():
    valid_chunks = [
        DocumentChunk(doc_id="Doc_12", section="§2", title="Pune", text="Venue A capacity 30")
    ]

    # Includes fabricated citation
    citations = ["Doc_12 §2", "Doc_999 §9"]
    support_ratio, verified, hallucinated = GroundingVerifier.verify_citations(citations, valid_chunks)

    assert support_ratio == 0.5
    assert "Doc_999 §9" in hallucinated


def test_explicit_uncertainty_flagging():
    chunks = [
        DocumentChunk(doc_id="Doc_12", section="§2", title="Pune", text="Venue A classroom seating")
    ]

    # User asked for accommodation which is missing from retrieved chunks
    uncertainty = GroundingVerifier.detect_uncertainty(
        sub_queries=["venue capacity in Pune", "overnight accommodation policies for Venue A"],
        retrieved_chunks=chunks,
        accumulated_utterance="overnight accommodation policies for Venue A"
    )

    assert uncertainty is not None
    assert "accommodation" in uncertainty.lower()
