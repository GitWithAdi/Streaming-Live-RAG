"""
Command Line Interface & Live Streaming Simulator for Streaming Live RAG.
Supports:
  1. python cli.py --benchmark               (Runs automated G1-G6 acceptance gates)
  2. python cli.py --ablations               (Runs architectural ablation experiments)
  3. python cli.py --stream-example [1|2|3]  (Simulates real-time live streaming demo)
  4. python cli.py --interactive             (Interactive query session)
"""

import sys
import time
import argparse
from streaming_rag.pipeline import StreamingLiveRAGEngine
from streaming_rag.schemas import TranscriptChunk
from evaluation.benchmark_runner import BenchmarkRunner
from evaluation.ablations import print_ablation_reports


def run_stream_simulation(example_id: int):
    """Simulates real-time transcript streaming with live event logs."""
    sys.stdout.reconfigure(encoding="utf-8")

    if example_id == 1:
        corpus_path = "data/corpus/venue_booking_corpus.json"
        stream = [
            (0.0, "I need to plan a customer workshop in...", False),
            (0.8, "...Pune for 30 people, and I need...", False),
            (1.6, "...the cancellation policy and the catering options.", False),
            (2.1, "", True)
        ]
        title = "EXAMPLE 1: Incremental Multi-Intent Utterance"
        session_id = "sim_ex1"

    elif example_id == 2:
        corpus_path = "data/corpus/travel_reimbursement_corpus.json"
        title = "EXAMPLE 2: Late-Arriving Detail (Refine, Do Not Restart)"
        session_id = "sim_ex2"

    elif example_id == 3:
        corpus_path = "data/corpus/travel_reimbursement_corpus.json"
        title = "EXAMPLE 3: Query Suppression (No Retrieval Required)"
        session_id = "sim_ex3"
    else:
        print(f"Unknown example ID: {example_id}. Choose 1, 2, or 3.")
        return

    print("=" * 80)
    print(f"            STREAMING LIVE RAG SIMULATOR: {title}")
    print("=" * 80)

    engine = StreamingLiveRAGEngine(corpus_path, use_fast_fallback=False)

    if example_id == 1:
        chunks = [TranscriptChunk(timestamp_s=ts, text=txt, is_final=fin) for ts, txt, fin in stream]
        print("\n>>> Incoming Full-Duplex Speech Stream Starting...\n")

        for c in chunks:
            print(f"[{c.timestamp_s:4.1f}s] Incoming Chunk: '{c.text}' {'[FINAL]' if c.is_final else ''}")
            time.sleep(0.3)  # Visual pacing

        print("\n>>> Processing Pipeline Active...")
        record = engine.process_stream(chunks, session_id=session_id)

        print("\n[Telemetry & Output Event Record]:")
        print(record.model_dump_json(indent=2))

    elif example_id == 2:
        print("\n--- TURN 1: Initial Request ---")
        t1_chunks = [TranscriptChunk(timestamp_s=0.0, text="Summarize the travel reimbursement rule for an employee trip.", is_final=True)]
        print("[0.0s] User: Summarize the travel reimbursement rule for an employee trip.")
        r1 = engine.process_stream(t1_chunks, session_id=session_id)
        print(f"Assistant (Version {r1.answer_version}): {r1.answer}\nCitations: {r1.citations}")

        time.sleep(0.5)
        print("\n--- TURN 2: Late-Arriving Detail (State Refinement) ---")
        print("[0.0s] User: The trip was international and the booking was made after travel.")
        t2_chunks = [TranscriptChunk(timestamp_s=0.0, text="The trip was international and the booking was made after travel.", is_final=True)]
        r2 = engine.process_stream(t2_chunks, session_id=session_id)
        print(f"Assistant (Version {r2.answer_version}): {r2.answer}\nCitations: {r2.citations}")
        print("\nTargeted Retrieval Events:")
        for ev in r2.retrieval_events:
            print(f"  • [{ev.trigger.upper()}] Query: '{ev.query}' at {ev.timestamp_s}s")

    elif example_id == 3:
        print("\n--- TURN 1: Initial Request ---")
        t1_chunks = [TranscriptChunk(timestamp_s=0.0, text="Summarize the travel reimbursement rule for an employee trip.", is_final=True)]
        print("[0.0s] User: Summarize the travel reimbursement rule for an employee trip.")
        r1 = engine.process_stream(t1_chunks, session_id=session_id)
        print(f"Assistant (Version {r1.answer_version}): {r1.answer}\nCitations: {r1.citations}")

        time.sleep(0.5)
        print("\n--- TURN 2: Presentation Formatting Request ---")
        print("[0.0s] User: Please repeat your last answer in two bullets.")
        t2_chunks = [TranscriptChunk(timestamp_s=0.0, text="Please repeat your last answer in two bullets.", is_final=True)]
        r2 = engine.process_stream(t2_chunks, session_id=session_id)
        print(f"Assistant (Version {r2.answer_version}):\n{r2.answer}\nCitations: {r2.citations}")
        print(f"Total Retrieval Events Executed: {len(r2.retrieval_events)} (Corpus search suppressed)")

    print("\n" + "=" * 80)


def main():
    parser = argparse.ArgumentParser(description="Streaming Live RAG Engine Runner")
    parser.add_argument("--benchmark", action="store_true", help="Run automated evaluation gates G1-G6 benchmark suite")
    parser.add_argument("--ablations", action="store_true", help="Run architectural ablation experiments")
    parser.add_argument("--stream-example", type=int, choices=[1, 2, 3], help="Simulate real-time streaming for Example 1, 2, or 3")
    parser.add_argument("--interactive", action="store_true", help="Start interactive conversational session")

    args = parser.parse_args()

    if args.benchmark:
        runner = BenchmarkRunner()
        summary = runner.run_all(verbose=True)
        all_passed = all(g["passed"] for g in summary["gates"].values())
        sys.exit(0 if all_passed else 1)

    elif args.ablations:
        print_ablation_reports()

    elif args.stream_example:
        run_stream_simulation(args.stream_example)

    elif args.interactive:
        sys.stdout.reconfigure(encoding="utf-8")
        print("Starting interactive session with Venue Booking & Policy Corpus...")
        engine = StreamingLiveRAGEngine("data/corpus/venue_booking_corpus.json")
        session_id = "interactive_session"
        while True:
            try:
                user_text = input("\nUser > ").strip()
                if user_text.lower() in ("exit", "quit"):
                    break
                chunk = TranscriptChunk(timestamp_s=0.0, text=user_text, is_final=True)
                rec = engine.process_stream([chunk], session_id=session_id)
                print(f"Assistant (v{rec.answer_version}) > {rec.answer}")
                if rec.citations:
                    print(f"Citations: {rec.citations}")
                if rec.uncertainty:
                    print(f"Uncertainty: {rec.uncertainty}")
            except (KeyboardInterrupt, EOFError):
                break
    else:
        # Default behavior: run benchmark
        runner = BenchmarkRunner()
        summary = runner.run_all(verbose=True)
        all_passed = all(g["passed"] for g in summary["gates"].values())
        sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
