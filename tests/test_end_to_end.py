"""
End-to-end integration test validating Example 1, 2, and 3 workflows.
"""

from streaming_rag.pipeline import StreamingLiveRAGEngine
from streaming_rag.schemas import TranscriptChunk


def test_example_1_full_stream():
    engine = StreamingLiveRAGEngine("data/corpus/venue_booking_corpus.json", use_fast_fallback=False)
    stream = [
        TranscriptChunk(timestamp_s=0.0, text="I need to plan a customer workshop in..."),
        TranscriptChunk(timestamp_s=0.8, text="...Pune for 30 people, and I need..."),
        TranscriptChunk(timestamp_s=1.6, text="...the cancellation policy and the catering options."),
        TranscriptChunk(timestamp_s=2.1, text="", is_final=True)
    ]

    record = engine.process_stream(stream, session_id="e2e_ex1")

    # Verify provisional event at 0.8s
    prov_events = [e for e in record.retrieval_events if e.trigger == "provisional"]
    assert len(prov_events) >= 1
    assert prov_events[0].timestamp_s == 0.8

    # Verify multi-intent events at 1.6s
    multi_events = [e for e in record.retrieval_events if e.trigger == "multi_intent"]
    assert len(multi_events) >= 2

    # Verify 3 sub-queries
    assert len(record.sub_queries) == 3

    # Verify citations
    for expected_cite in ["Doc_12 §2", "Doc_31 §4", "Doc_09 §1"]:
        assert expected_cite in record.citations


def test_example_3_query_suppression():
    engine = StreamingLiveRAGEngine("data/corpus/travel_reimbursement_corpus.json", use_fast_fallback=False)
    session_id = "e2e_ex3"

    # Turn 1
    _ = engine.process_stream([
        TranscriptChunk(timestamp_s=0.0, text="Summarize the travel reimbursement rule for an employee trip.", is_final=True)
    ], session_id=session_id)

    # Turn 2: Presentation suppression
    record = engine.process_stream([
        TranscriptChunk(timestamp_s=0.0, text="Please repeat your last answer in two bullets.", is_final=True)
    ], session_id=session_id)

    # Must execute zero retrieval events
    assert len(record.retrieval_events) == 0
    # Must preserve citations
    assert "Doc_05 §1" in record.citations
    # Must be formatted in bullets
    assert "•" in record.answer
