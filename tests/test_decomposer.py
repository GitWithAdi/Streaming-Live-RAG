"""
Unit tests for Multi-Intent Decomposition and Context Propagation.
"""

from streaming_rag.decomposer.multi_intent import MultiIntentDecomposer


def test_multi_intent_decomposition():
    decomposer = MultiIntentDecomposer()
    text = "I need to plan a customer workshop in Pune for 30 people, and I need the cancellation policy and the catering options."
    sub_queries = decomposer.decompose(text)

    # Must isolate at least 2, ideally 3 distinct orthogonal queries
    assert len(sub_queries) >= 3

    # Check for contextual anchor preservation: Pune and workshop preserved
    assert any("pune" in sq.lower() for sq in sub_queries)
    assert any("cancellation" in sq.lower() for sq in sub_queries)
    assert any("catering" in sq.lower() for sq in sub_queries)


def test_anti_fragmentation_on_simple_query():
    decomposer = MultiIntentDecomposer()
    text = "What is the venue capacity for 30 attendees in Pune?"
    sub_queries = decomposer.decompose(text)

    # Should not over-fragment a single intent into duplicate queries
    assert len(sub_queries) == 1
