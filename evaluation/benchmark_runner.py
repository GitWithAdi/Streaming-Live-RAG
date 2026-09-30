"""
Automated Replay Benchmark Suite for Streaming Live RAG.
Evaluates the engine against the 6 quantitative acceptance gates (G1 - G6)
defined in Samsung PRISM Theme 04.
"""

import os
import sys
import json
import time
from typing import Dict, Any, List, Tuple

# Fix: Ensure UTF-8 output on Windows terminals for symbols like §
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from streaming_rag.pipeline import StreamingLiveRAGEngine
from streaming_rag.schemas import TranscriptChunk, StructuredOutputRecord
from streaming_rag.synthesizer.grounding import GroundingVerifier


class BenchmarkRunner:
    """Automated benchmark replay harness for evaluating Gates G1 to G6."""

    def __init__(self, suite_path: str = "data/benchmarks/benchmark_suite.json"):
        self.suite_path = suite_path
        if not os.path.exists(suite_path):
            raise FileNotFoundError(f"Benchmark suite file not found: {suite_path}")

        with open(suite_path, "r", encoding="utf-8") as f:
            self.suite_data = json.load(f)

        self.results: Dict[str, Any] = {}
        self.gate_scores: Dict[str, Dict[str, Any]] = {}

    def run_all(self, verbose: bool = True) -> Dict[str, Any]:
        """Runs all benchmark test cases and evaluates Gates G1-G6."""
        start_time = time.time()
        test_cases = self.suite_data.get("test_cases", [])

        total_eligible_early_queries = 0
        early_retrieval_successes = 0

        total_compound_queries = 0
        multi_intent_successes = 0

        total_citations = 0
        supported_citations = 0
        hallucinated_doc_ids = 0

        refinement_continuity_checks = 0
        refinement_continuity_passes = 0

        total_turns = 0
        valid_telemetry_traces = 0

        execution_errors = 0

        if verbose:
            print("================================================================================")
            print("            STREAMING LIVE RAG: AUTOMATED BENCHMARK REPLAY SUITE                ")
            print("================================================================================")

        for tc in test_cases:
            tc_id = tc["id"]
            tc_name = tc["name"]
            corpus_path = tc["corpus_path"]
            tc_type = tc["type"]

            if verbose:
                print(f"\n[Running Test Case]: {tc_id} - {tc_name}")

            try:
                engine = StreamingLiveRAGEngine(corpus_path, use_fast_fallback=False)
                session_id = f"bench_{tc_id}"

                if tc_type in ("streaming_multi_intent", "noise_filtering"):
                    chunks = [
                        TranscriptChunk(
                            timestamp_s=c["timestamp_s"],
                            text=c["text"],
                            is_final=c.get("is_final", False)
                        )
                        for c in tc["stream_chunks"]
                    ]

                    record = engine.process_stream(chunks, session_id=session_id)
                    total_turns += 1

                    # Telemetry check (G6)
                    if record.retrieval_events is not None and record.citations is not None and record.total_latency_ms is not None:
                        valid_telemetry_traces += 1

                    # Gate G2: Early Retrieval
                    if tc_type != "noise_filtering":
                        total_eligible_early_queries += 1
                        # Check if at least one retrieval event happened before utterance end
                        final_chunk_ts = chunks[-1].timestamp_s
                        early_events = [e for e in record.retrieval_events if e.timestamp_s < final_chunk_ts]
                        if early_events:
                            early_retrieval_successes += 1
                            if verbose:
                                print(f"  [G2 Early Retrieval]: PASS (Triggered at {early_events[0].timestamp_s}s < Final {final_chunk_ts}s)")
                        else:
                            if verbose:
                                print(f"  [G2 Early Retrieval]: FAIL (No retrieval prior to {final_chunk_ts}s)")

                    # Gate G3: Multi-Intent Identification
                    if tc_type == "streaming_multi_intent" and tc.get("expected_sub_intents_count", 0) >= 2:
                        total_compound_queries += 1
                        if len(record.sub_queries) >= 2:
                            multi_intent_successes += 1
                            if verbose:
                                print(f"  [G3 Multi-Intent]: PASS (Isolated {len(record.sub_queries)} sub-intents: {record.sub_queries})")
                        else:
                            if verbose:
                                print(f"  [G3 Multi-Intent]: FAIL (Found {len(record.sub_queries)} sub-intents)")

                    # Gate G4: Grounding Verification
                    if record.citations:
                        ratio, ver, hal = GroundingVerifier.verify_citations(record.citations, engine.corpus_chunks)
                        total_citations += len(record.citations)
                        supported_citations += len(ver)
                        hallucinated_doc_ids += len(hal)
                        if verbose:
                            print(f"  [G4 Grounding]: Verified {len(ver)}/{len(record.citations)} citations (Support: {ratio*100:.1f}%, Hallucinations: {len(hal)})")

                elif tc_type in ("multi_turn_refinement", "query_suppression"):
                    # Execute sequential turns in the same session
                    for turn in tc["turns"]:
                        t_id = turn["turn_id"]
                        t_chunks = [
                            TranscriptChunk(
                                timestamp_s=c["timestamp_s"],
                                text=c["text"],
                                is_final=c.get("is_final", False)
                            )
                            for c in turn["stream_chunks"]
                        ]
                        record = engine.process_stream(t_chunks, session_id=session_id)
                        total_turns += 1

                        if record.retrieval_events is not None and record.citations is not None:
                            valid_telemetry_traces += 1

                        # Query suppression check
                        if turn.get("expected_action") == "no_retrieval":
                            if len(record.retrieval_events) == 0:
                                if verbose:
                                    print(f"  [Turn {t_id} Suppression]: PASS (0 retrieval events executed, format transformed)")
                            else:
                                if verbose:
                                    print(f"  [Turn {t_id} Suppression]: FAIL ({len(record.retrieval_events)} retrieval events triggered)")

                        # Gate G5: Session Refinement Continuity
                        if turn.get("is_late_constraint"):
                            refinement_continuity_checks += 1
                            if record.answer_version == turn.get("expected_version", 2):
                                # Check that prior citations were preserved
                                expected_cites = turn.get("expected_citations", [])
                                if all(c in record.citations for c in expected_cites):
                                    refinement_continuity_passes += 1
                                    if verbose:
                                        print(f"  [G5 Session Refinement]: PASS (Version {record.answer_version}, State continuous, Citations: {record.citations})")
                                else:
                                    if verbose:
                                        print(f"  [G5 Session Refinement]: PARTIAL (Version {record.answer_version}, Missing some expected citations)")
                            else:
                                if verbose:
                                    print(f"  [G5 Session Refinement]: FAIL (Version was {record.answer_version})")

                        # Gate G4 check for turn
                        if record.citations:
                            ratio, ver, hal = GroundingVerifier.verify_citations(record.citations, engine.corpus_chunks)
                            total_citations += len(record.citations)
                            supported_citations += len(ver)
                            hallucinated_doc_ids += len(hal)

            except Exception as ex:
                execution_errors += 1
                if verbose:
                    print(f"  [Execution Error in {tc_id}]: {ex}")

        # Compute Gate Metrics
        g1_pass = (execution_errors == 0)

        g2_ratio = (early_retrieval_successes / total_eligible_early_queries) if total_eligible_early_queries > 0 else 1.0
        g2_pass = g2_ratio >= 0.80

        g3_ratio = (multi_intent_successes / total_compound_queries) if total_compound_queries > 0 else 1.0
        g3_pass = g3_ratio >= 0.70

        g4_ratio = (supported_citations / total_citations) if total_citations > 0 else 1.0
        g4_pass = (g4_ratio >= 0.85) and (hallucinated_doc_ids == 0)

        g5_ratio = (refinement_continuity_passes / refinement_continuity_checks) if refinement_continuity_checks > 0 else 1.0
        g5_pass = (g5_ratio == 1.0)

        g6_ratio = (valid_telemetry_traces / total_turns) if total_turns > 0 else 1.0
        g6_pass = (g6_ratio == 1.0)

        total_benchmark_time = round(time.time() - start_time, 2)

        summary = {
            "total_runtime_s": total_benchmark_time,
            "total_test_cases": len(test_cases),
            "total_turns": total_turns,
            "gates": {
                "G1_Reproducibility": {
                    "criterion": "Reproducibility (Single-command execution, 0 manual intervention)",
                    "target": "Pass/Fail",
                    "measured": "PASS" if g1_pass else "FAIL",
                    "passed": g1_pass
                },
                "G2_Early_Retrieval": {
                    "criterion": "Early Retrieval (commences prior to final transcript)",
                    "target": ">= 80% of eligible queries",
                    "measured": f"{g2_ratio * 100:.1f}% ({early_retrieval_successes}/{total_eligible_early_queries})",
                    "passed": g2_pass
                },
                "G3_Multi_Intent_Identification": {
                    "criterion": "Multi-Intent Identification (isolates >= 2 distinct sub-intents)",
                    "target": ">= 70% of compound queries",
                    "measured": f"{g3_ratio * 100:.1f}% ({multi_intent_successes}/{total_compound_queries})",
                    "passed": g3_pass
                },
                "G4_Factual_Grounding": {
                    "criterion": "Factual Grounding (citation support ratio, 0 hallucinated Doc IDs)",
                    "target": ">= 85% citation support, 0 fabricated",
                    "measured": f"{g4_ratio * 100:.1f}% support ({supported_citations}/{total_citations}), {hallucinated_doc_ids} hallucinations",
                    "passed": g4_pass
                },
                "G5_Session_Refinement": {
                    "criterion": "Session Refinement (mutates state without full reset)",
                    "target": "Verified state continuity (100%)",
                    "measured": f"{g5_ratio * 100:.1f}% ({refinement_continuity_passes}/{refinement_continuity_checks})",
                    "passed": g5_pass
                },
                "G6_Telemetry_Observability": {
                    "criterion": "Telemetry & Observability (structured trace coverage)",
                    "target": "100% trace coverage",
                    "measured": f"{g6_ratio * 100:.1f}% ({valid_telemetry_traces}/{total_turns})",
                    "passed": g6_pass
                }
            }
        }

        if verbose:
            print("\n================================================================================")
            print("                 TECHNICAL EVALUATION GATES SCORECARD                           ")
            print("================================================================================")
            print(f"{'Gate':<6} | {'Criterion':<32} | {'Target':<22} | {'Measured':<20} | {'Status':<6}")
            print("-" * 96)
            for gate_key, details in summary["gates"].items():
                gate_code = gate_key.split("_")[0]
                crit = details["criterion"][:30]
                tgt = details["target"][:20]
                meas = details["measured"][:18]
                stat = "PASS" if details["passed"] else "FAIL"
                print(f"{gate_code:<6} | {crit:<32} | {tgt:<22} | {meas:<20} | {stat:<6}")
            print("================================================================================")
            print(f"Total Benchmark Execution Time: {total_benchmark_time} seconds across {total_turns} turns.\n")

        return summary


if __name__ == "__main__":
    runner = BenchmarkRunner()
    summary = runner.run_all(verbose=True)
    all_passed = all(g["passed"] for g in summary["gates"].values())
    sys.exit(0 if all_passed else 1)
