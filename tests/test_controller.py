"""
Unit tests for Retrieval Controller, Intent Stability, and Query Suppression.
"""

import pytest
from streaming_rag.controller.stability_classifier import RetrievalController
from streaming_rag.controller.suppression_detector import PresentationSuppressionDetector
from streaming_rag.schemas import ControllerDecision


def test_early_noise_and_dangling_preposition():
    controller = RetrievalController()
    dec = controller.evaluate_chunk(
        accumulated_text="I need to plan a customer workshop in...",
        current_chunk_text="I need to plan a customer workshop in...",
        timestamp_s=0.0,
        is_final=False
    )
    assert dec.action == "wait"
    assert "instability" in dec.reason or "insufficient" in dec.reason


def test_provisional_retrieval_trigger():
    controller = RetrievalController()
    dec = controller.evaluate_chunk(
        accumulated_text="I need to plan a customer workshop in Pune for 30 people, and I need...",
        current_chunk_text="...Pune for 30 people, and I need...",
        timestamp_s=0.8,
        is_final=False,
        prior_retrieval_done=False
    )
    assert dec.action == "retrieve"
    assert dec.reason == "provisional_entities_stabilized"
    assert "pune" in [e.lower() for e in dec.extracted_entities]


def test_multi_intent_compound_trigger():
    controller = RetrievalController()
    dec = controller.evaluate_chunk(
        accumulated_text="I need to plan a customer workshop in Pune for 30 people, and I need the cancellation policy and the catering options.",
        current_chunk_text="...the cancellation policy and the catering options.",
        timestamp_s=1.6,
        is_final=False
    )
    assert dec.action == "retrieve"
    assert dec.is_compound is True


def test_presentation_query_suppression():
    detector = PresentationSuppressionDetector()
    is_supp, reason, conf = detector.evaluate("Please repeat your last answer in two bullets.", has_prior_context=True)
    assert is_supp is True
    assert reason == "presentation_restructure"
    assert conf >= 0.75

    # Should not suppress if no prior context exists
    is_supp_no_ctx, _, _ = detector.evaluate("Please repeat your last answer in two bullets.", has_prior_context=False)
    assert is_supp_no_ctx is False
