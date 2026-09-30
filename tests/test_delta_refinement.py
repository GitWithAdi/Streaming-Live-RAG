"""
Unit tests for Session-Aware Answer Delta Refinement (Example 2).
"""

from streaming_rag.pipeline import StreamingLiveRAGEngine
from streaming_rag.schemas import TranscriptChunk


def test_delta_refinement_state_continuity():
    engine = StreamingLiveRAGEngine("data/corpus/travel_reimbursement_corpus.json", use_fast_fallback=False)
    session_id = "test_delta_session"

    # Turn 1: Initial request
    r1 = engine.process_stream([
        TranscriptChunk(timestamp_s=0.0, text="Summarize the travel reimbursement rule for an employee trip.", is_final=True)
    ], session_id=session_id)

    assert r1.answer_version == 1
    assert "Doc_05 §1" in r1.citations

    # Turn 2: Late constraint
    r2 = engine.process_stream([
        TranscriptChunk(timestamp_s=0.0, text="The trip was international and the booking was made after travel.", is_final=True)
    ], session_id=session_id)

    # State continuity checks:
    # 1. Answer version incremented
    assert r2.answer_version == 2
    # 2. Prior citation preserved
    assert "Doc_05 §1" in r2.citations
    # 3. Delta citations added
    assert "Doc_05 §3" in r2.citations
    assert "Doc_07 §2" in r2.citations
    # 4. Retrieval trigger was delta_refinement
    assert any(e.trigger == "delta_refinement" for e in r2.retrieval_events)
