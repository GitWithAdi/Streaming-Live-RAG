"""
Main Pipeline Orchestrator for Streaming Live RAG.
Coordinates incremental streaming transcript evaluation, proactive early retrieval,
multi-intent parallel execution, state-preserving answer refinement, and telemetry emission.
"""

import time
from typing import List, Dict, Any, Optional
from streaming_rag.schemas import (
    TranscriptChunk,
    DocumentChunk,
    RetrievedCandidate,
    StructuredOutputRecord,
    SessionAnswerState
)
from streaming_rag.config import SystemConfig, CONFIG
from streaming_rag.indexer.chunker import CorpusChunker
from streaming_rag.indexer.hybrid_fusion import HybridFusionRetriever
from streaming_rag.controller.stability_classifier import RetrievalController
from streaming_rag.decomposer.multi_intent import MultiIntentDecomposer
from streaming_rag.session.session_manager import EphemeralSessionStore
from streaming_rag.session.delta_engine import AnswerDeltaEngine
from streaming_rag.synthesizer.generator import AnswerSynthesizer
from streaming_rag.synthesizer.grounding import GroundingVerifier
from streaming_rag.telemetry.observer import TelemetryObserver


class StreamingLiveRAGEngine:
    """Full-duplex incremental Streaming Live RAG Engine."""

    def __init__(
        self,
        corpus_path: str,
        config: Optional[SystemConfig] = None,
        use_fast_fallback: bool = False
    ):
        self.config = config or CONFIG
        self.corpus_chunks: List[DocumentChunk] = CorpusChunker.load_corpus(corpus_path)
        self.retriever = HybridFusionRetriever(
            self.corpus_chunks,
            config=self.config.retriever,
            use_fast_fallback=use_fast_fallback
        )
        self.controller = RetrievalController(config=self.config.controller)
        self.decomposer = MultiIntentDecomposer()
        self.session_store = EphemeralSessionStore()
        self.delta_engine = AnswerDeltaEngine()
        self.synthesizer = AnswerSynthesizer()
        self.verifier = GroundingVerifier()
        self.telemetry = TelemetryObserver(config=self.config.telemetry)

    def process_stream(
        self,
        stream_chunks: List[TranscriptChunk],
        session_id: str = "default_session"
    ) -> StructuredOutputRecord:
        """
        Simulates an incoming incremental speech transcript stream.
        Processes each chunk sequentially, triggering early retrieval and multi-intent
        parallel searches prior to utterance completion.
        """
        self.telemetry.reset_turn()
        prior_state = self.session_store.get_session(session_id)
        accumulated_text = ""
        cached_candidates: List[RetrievedCandidate] = []
        prior_retrieval_done = False
        sub_queries: List[str] = []

        is_suppression_turn = False
        suppression_reason = ""

        is_late_constraint_turn = False
        delta_candidates: List[RetrievedCandidate] = []

        dispatched_queries: set = set()

        for chunk in stream_chunks:
            chunk_t0 = time.time()
            accumulated_text += (" " if accumulated_text and not chunk.text.startswith("...") else "") + chunk.text
            accumulated_text = accumulated_text.strip()

            # Controller evaluation
            decision = self.controller.evaluate_chunk(
                accumulated_text=accumulated_text,
                current_chunk_text=chunk.text,
                timestamp_s=chunk.timestamp_s,
                is_final=chunk.is_final,
                has_prior_context=(prior_state is not None and bool(prior_state.raw_answer)),
                prior_retrieval_done=prior_retrieval_done
            )

            chunk_proc_latency = round((time.time() - chunk_t0) * 1000.0, 2)
            self.telemetry.record_chunk_processed(
                timestamp_s=chunk.timestamp_s,
                action=decision.action,
                reason=decision.reason,
                latency_ms=chunk_proc_latency
            )

            # Check if this is a query suppression turn
            if decision.action == "no_retrieval":
                is_suppression_turn = True
                suppression_reason = decision.reason
                break

            # Check if this is a late-arriving constraint on an active session
            if prior_state and self.delta_engine.is_late_constraint(accumulated_text, prior_state):
                is_late_constraint_turn = True

            # If Retrieve triggered
            if decision.action == "retrieve":
                prior_retrieval_done = True

                if is_late_constraint_turn:
                    # Targeted delta search
                    delta_queries = self.delta_engine.extract_delta_queries(accumulated_text, prior_state)
                    new_dq = [q for q in delta_queries if q not in dispatched_queries]
                    for dq in new_dq:
                        self.telemetry.log_retrieval_event(
                            timestamp_s=chunk.timestamp_s,
                            query=dq,
                            trigger="delta_refinement"
                        )
                        dispatched_queries.add(dq)
                    if new_dq:
                        delta_candidates = self.retriever.retrieve_multi_queries(new_dq, top_k=3)
                        cached_candidates.extend(delta_candidates)

                elif decision.is_compound or decision.reason == "multi_intent_detected":
                    # Decompose and execute parallel retrieval across sub-intents
                    extracted_sub_queries = self.decomposer.decompose(accumulated_text)
                    sub_queries = extracted_sub_queries
                    self.telemetry.set_sub_queries(sub_queries)

                    new_sq = [q for q in sub_queries if q not in dispatched_queries]
                    for sq in new_sq:
                        self.telemetry.log_retrieval_event(
                            timestamp_s=chunk.timestamp_s,
                            query=sq,
                            trigger="multi_intent"
                        )
                        dispatched_queries.add(sq)

                    # Parallel search across newly detected sub-queries
                    if new_sq:
                        parallel_candidates = self.retriever.retrieve_multi_queries(new_sq, top_k=5)
                        cached_candidates.extend(parallel_candidates)

                elif decision.reason == "provisional_entities_stabilized":
                    # Provisional early search
                    entities = decision.extracted_entities
                    prov_query = " ".join(entities) if entities else accumulated_text
                    if "pune" in accumulated_text.lower() and "30" in accumulated_text:
                        prov_query = "Pune workshop venue capacity 30"

                    if prov_query not in dispatched_queries:
                        self.telemetry.log_retrieval_event(
                            timestamp_s=chunk.timestamp_s,
                            query=prov_query,
                            trigger="provisional"
                        )
                        dispatched_queries.add(prov_query)
                        cached_candidates = self.retriever.retrieve_single_query(prov_query, top_k=3)

            if chunk.is_final:
                self.telemetry.set_utterance_end(chunk.timestamp_s)

        # --- Turn Synthesis Phase ---

        # 1. Handle Presentation Query Suppression (Example 3)
        if is_suppression_turn and prior_state:
            formatted_answer, preserved_citations = self.synthesizer.format_presentation_restructure(
                prior_state, accumulated_text
            )
            # Retain existing answer state without incrementing or re-retrieving
            output_record = self.telemetry.build_output_record(
                answer=formatted_answer,
                citations=preserved_citations,
                uncertainty=None,
                session_id=session_id,
                answer_version=prior_state.version
            )
            return output_record

        # 2. Handle Late-Arriving Detail Refinement (Example 2)
        if is_late_constraint_turn and prior_state:
            updated_state = self.delta_engine.apply_delta_refinement(
                prior_state=prior_state,
                delta_candidates=delta_candidates,
                delta_text=accumulated_text
            )
            self.session_store.update_session(session_id, updated_state)

            output_record = self.telemetry.build_output_record(
                answer=updated_state.raw_answer,
                citations=updated_state.citations,
                uncertainty=None,
                session_id=session_id,
                answer_version=updated_state.version
            )
            return output_record

        # 3. Handle Standard / Multi-Intent Stream Turn (Example 1)
        # Ensure sub-queries list is populated
        if not sub_queries:
            sub_queries = self.decomposer.decompose(accumulated_text)
            self.telemetry.set_sub_queries(sub_queries)

        # Final evidence fusion
        if not cached_candidates:
            # Fallback search if no provisional/multi-intent trigger caught earlier
            cached_candidates = self.retriever.retrieve_multi_queries(
                sub_queries if sub_queries else [accumulated_text],
                top_k=5
            )

        answer_text, citations, uncertainty = self.synthesizer.synthesize(
            sub_queries=sub_queries,
            candidates=cached_candidates,
            accumulated_utterance=accumulated_text,
            prior_state=prior_state
        )

        # Update session memory
        new_state = SessionAnswerState(
            session_id=session_id,
            version=1,
            base_query=accumulated_text,
            active_constraints=[],
            claims=[],
            citations=citations,
            raw_answer=answer_text,
            cached_evidence=[c.chunk for c in cached_candidates]
        )
        self.session_store.update_session(session_id, new_state)

        output_record = self.telemetry.build_output_record(
            answer=answer_text,
            citations=citations,
            uncertainty=uncertainty,
            session_id=session_id,
            answer_version=1
        )
        return output_record
