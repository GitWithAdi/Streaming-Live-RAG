# Streaming Live RAG Engine
**Real-Time Incremental Retrieval, Multi-Intent Decomposition, and State-Preserving Answer Refinement**  
*Samsung PRISM GenAI Hackathon 3rd Edition (Theme 04)*  

[![Acceptance Gates: All Passed](https://img.shields.io/badge/Acceptance%20Gates-G1--G6%20PASSED-brightgreen.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)]()
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)]()

---

## 1. Overview & Problem Statement

Conventional Retrieval-Augmented Generation (RAG) pipelines operate in a static, batch turn cycle: a user finishes speaking, submits a query, and waits while the system searches a knowledge base and synthesizes an answer. In real-time conversational voice systems, this forces artificial pauses of 2 to 4 seconds, fails on compound multi-intent speech, and restarts from scratch whenever mid-conversation constraints arrive.

**Streaming Live RAG** is an event-driven conversational engine that:
1. **Listens Incrementally**: Evaluates timestamped transcript fragments in real-time, predicting retrieval intent prior to utterance completion (**1,300 ms early retrieval lead time**).
2. **Decomposes Multi-Intent Queries**: Identifies and parallelizes retrieval for multiple discrete sub-questions embedded within compound speech while propagating contextual anchors.
3. **Refines Rather Than Restarts**: Ingests late-arriving constraints directly into active answer states without clearing session context or re-executing full-corpus retrieval (Answer Versioning $v1 \to v2$).
4. **Guarantees Corpus Grounding**: Strictly isolates retrieval to the supplied corpus, enforces `[Doc_ID §Section]` citations with zero hallucinated IDs, and emits explicit uncertainty indicators for missing facts.
5. **Suppresses Presentation Queries**: Intercepts formatting/restructuring requests (e.g. *"repeat in two bullets"*), transforming existing context with **zero unneeded corpus searches**.

---

## 2. Technical Evaluation Gates Scorecard

All six automated quantitative acceptance gates defined in Section 5 of the Samsung PRISM guide have been benchmarked and verified:

| Gate | Criterion | Target Threshold | Measured Score | Status |
| :---: | :--- | :--- | :--- | :---: |
| **G1** | **Reproducibility** | Pass/Fail | Clean single-command launch with 0 manual intervention | **PASS** |
| **G2** | **Early Retrieval** | $\ge 80\%$ of eligible queries | **100.0%** (Triggered at 0.8s < 2.1s final transcript) | **PASS** |
| **G3** | **Multi-Intent Identification** | $\ge 70\%$ of compound queries | **100.0%** (Isolates 3 orthogonal sub-queries) | **PASS** |
| **G4** | **Factual Grounding** | $\ge 85\%$ citation support | **100.0%** (15/15 citations verified, 0 hallucinations) | **PASS** |
| **G5** | **Session Refinement** | Verified state continuity | **100.0%** (State continuous, $v1 \to v2$, 0 full restarts) | **PASS** |
| **G6** | **Telemetry & Observability** | 100% trace coverage | **100.0%** (Complete structured logs across all turns) | **PASS** |

---

## 3. Architecture & Data Flow

```
Incoming Audio / Transcript Stream:
[Chunk 0.0s] ──► [Chunk 0.8s] ──► [Chunk 1.6s] ──► [Utterance End 2.1s]
                        │               │                    │
                        ▼               ▼                    ▼
             ┌─────────────────────────────────────────────────────────┐
             │            [1] RETRIEVAL CONTROLLER                     │
             │  • Dangling Preposition & Stability Detection           │
             │  • Entity Density & Semantic Boundary Analysis          │
             │  • Decision: [WAIT | RETRIEVE | NO-RETRIEVAL]           │
             └──────────────────────────┬──────────────────────────────┘
                                        │ (Retrieve Triggered)
                                        ▼
             ┌─────────────────────────────────────────────────────────┐
             │          [2] MULTI-INTENT DECOMPOSER                    │
             │  • Orthogonal Sub-Query Extraction                      │
             │  • Contextual Anchor Propagation (Location, Topic)      │
             │  • Anti-Fragmentation Filter                            │
             └──────────────────────────┬──────────────────────────────┘
                                        │
                                        ▼
             ┌─────────────────────────────────────────────────────────┐
             │       [3] CORPUS RETRIEVAL & EVIDENCE FUSION            │
             │  • Parallel Execution across Sub-Queries                │
             │  • Dense Vector Index (SentenceTransformers)            │
             │  • Sparse Lexical Index (BM25Okapi)                     │
             │  • Reciprocal Rank Fusion (RRF k=60) & Deduplication    │
             └──────────────────────────┬──────────────────────────────┘
                                        │
                                        ▼
             ┌─────────────────────────────────────────────────────────┐
             │     [4] SESSION-AWARE SYNTHESIS & DELTA ENGINE          │
             │  • Ephemeral Session Store (No cross-session profiling) │
             │  • Answer Delta Mutation (v1 ──► v2 Lineage)            │
             │  • Strict Grounding Verification ([Doc_ID §Section])    │
             │  • Explicit Uncertainty Flagging                        │
             └──────────────────────────┬──────────────────────────────┘
                                        │
                                        ▼
             ┌─────────────────────────────────────────────────────────┐
             │      [5] OBSERVABILITY TELEMETRY & STREAMED OUTPUT      │
             │  • Sub-second Latencies (TTFT, Lead Time, Processing)   │
             │  • Structured Event Records matching Page 4 JSON Schema │
             │  • Token Usage & Inference Cost Estimation              │
             └─────────────────────────────────────────────────────────┘
```

---

## 4. Quick Start & Reproducibility (Gate G1)

### Option A: Clean Single-Command CLI Runner (Local)
Ensure Python 3.10+ is installed:
```powershell
# Windows PowerShell
./run.ps1

# Linux / macOS
chmod +x run.sh && ./run.sh
```

Or execute the benchmark runner directly:
```bash
python -m evaluation.benchmark_runner
```

### Option B: Single-Command Container Launch (Docker)
```bash
docker compose up --build
```
The container builds the environment, loads the models, and executes the automated replay benchmark suite without manual intervention.

---

## 5. Interactive Streaming Demonstrator & CLI

The CLI provides live playback simulation of the scenarios specified in the hackathon guide:

### 1. Incremental Multi-Intent Utterance (Example 1)
```bash
python cli.py --stream-example 1
```
*Visualizes:*
- `0.0s`: `"I need to plan a customer workshop in..."` ➔ **WAIT** (semantic instability).
- `0.8s`: `"...Pune for 30 people, and I need..."` ➔ **PROVISIONAL RETRIEVAL** (1.3s early lead time).
- `1.6s`: `"...the cancellation policy and the catering options."` ➔ **DECOMPOSE & PARALLEL RETRIEVE** (3 sub-queries with context anchors).
- `2.1s`: `[Utterance End]` ➔ Grounded response with citations `[Doc_12 §2]`, `[Doc_31 §4]`, `[Doc_09 §1]`.

### 2. Late-Arriving Detail Refinement (Example 2)
```bash
python cli.py --stream-example 2
```
*Visualizes:*
- Turn 1: Travel reimbursement query ➔ Answer Version 1 citing `[Doc_05 §1]`.
- Turn 2: *"The trip was international and the booking was made after travel."* ➔ Targeted delta query, state preserved, Answer Version 2 citing `[Doc_05 §1]`, `[Doc_05 §3]`, `[Doc_07 §2]`.

### 3. Presentation Query Suppression (Example 3)
```bash
python cli.py --stream-example 3
```
*Visualizes:*
- User asks: *"Please repeat your last answer in two bullets."*
- Retrieval Controller evaluates: `action: no_retrieval`, `reason: presentation_restructure`.
- Transforms context into two bullets with **0 vector searches executed**.

### 4. Architectural Ablation Experiments
```bash
python cli.py --ablations
```
Runs:
- Ablation 1: Hybrid (Dense + Sparse RRF) vs Dense-Only vs Sparse-Only.
- Ablation 2: Real-Time Incremental Controller vs End-of-Utterance Baseline vs Eager Token Baseline.

### 5. Automated Acceptance Gate Suite
```bash
python -m pytest tests/ -v
```
Executes all 15 unit, integration, and end-to-end tests.

---

## 6. Project Directory Structure

```
Streaming-Live-RAG/
├── README.md                              # Main documentation and guide
├── Dockerfile                             # Container definition for reproducible evaluation (Gate G1)
├── docker-compose.yml                     # Docker orchestration configuration
├── pyproject.toml                         # Project metadata and pytest configuration
├── requirements.txt                       # Pinned dependency requirements
├── .env.example                           # Environment configuration template
├── run.ps1 / run.sh                       # Single-command runner scripts
├── cli.py                                 # Interactive & streaming simulator CLI
├── docs/
│   ├── System_Architecture_Brief.md       # <= 6 page formal architecture brief
│   ├── Benchmarking_Evaluation_Report.md  # Quantitative performance comparison, 3 edge cases, 2 ablations
│   ├── Telemetry_Observability_Schema.md  # Structured event record JSON schema and field guide
│   └── Video_Demonstration_Script.md      # <= 5 min demo video script and storyboard
├── data/
│   ├── corpus/                            # Isolated evaluation corpora
│   │   ├── venue_booking_corpus.json      # Pune customer workshop facilities & policies (Example 1)
│   │   └── travel_reimbursement_corpus.json # Employee travel, late booking, international rules (Example 2)
│   └── benchmarks/
│       └── benchmark_suite.json           # Held-out replay test cases for Gates G1 - G6
├── streaming_rag/
│   ├── __init__.py
│   ├── config.py                          # Thresholds, RRF weights, and model settings
│   ├── schemas.py                         # Pydantic models for events, decisions, chunks, states
│   ├── pipeline.py                        # Orchestrator integrating all streaming components
│   ├── indexer/
│   │   ├── chunker.py                     # Document loader with [Doc_ID §Section] markers
│   │   ├── dense_index.py                 # Vector store (SentenceTransformers with offline SVD fallback)
│   │   ├── sparse_index.py                # BM25Okapi lexical index
│   │   └── hybrid_fusion.py               # Reciprocal Rank Fusion (RRF k=60) & deduplication
│   ├── controller/
│   │   ├── stability_classifier.py        # Real-time intent stability analyzer & boundary detector
│   │   └── suppression_detector.py        # Presentation query suppression detector
│   ├── decomposer/
│   │   └── multi_intent.py                # Decomposes compound speech into parallel sub-queries
│   ├── session/
│   │   ├── session_manager.py             # Ephemeral session memory store
│   │   └── delta_engine.py                # Mutates claims and increments answer version on late constraints
│   ├── synthesizer/
│   │   ├── generator.py                   # Answer synthesis engine with streaming support
│   │   └── grounding.py                   # Citation verification & explicit uncertainty flagging
│   └── telemetry/
│       └── observer.py                    # Real-time event logger, latency profiler, token cost calculator
├── evaluation/
│   ├── __init__.py
│   ├── benchmark_runner.py                # Replays benchmark streams and computes G1-G6 gate metrics
│   └── ablations.py                       # Runs architectural ablation experiments
└── tests/
    ├── test_controller.py                 # Controller decision & suppression tests
    ├── test_decomposer.py                 # Multi-intent decomposition tests
    ├── test_retriever.py                  # Dense, sparse, and hybrid RRF tests
    ├── test_delta_refinement.py           # State-preserving constraint refinement tests
    ├── test_grounding.py                  # Citation verification & uncertainty tests
    └── test_end_to_end.py                 # End-to-end multi-turn pipeline tests
```

---

## 7. Submission Checklist & Deliverable Links

| Deliverable | Location / Resource Link | Verification Status |
| :--- | :--- | :---: |
| **Public GitHub Repository** | [GitWithAdi/Streaming-Live-RAG](https://github.com/GitWithAdi/Streaming-Live-RAG) | **VERIFIED** |
| **Official Release Tag** | [`PRISM_GENAI_HACKATHON_Y2026`](https://github.com/GitWithAdi/Streaming-Live-RAG/tree/PRISM_GENAI_HACKATHON_Y2026) | **VERIFIED** |
| **Demonstration Video (<= 5 min)** | [Google Drive Video Folder](https://drive.google.com/drive/folders/1ESU7GciUw4PzpmSpQ577GnLWuoR0X458?usp=sharing) | **VERIFIED** |
| **Presentation Slide Deck** | [`VITVellore_SlightlyHallucinating_Submission.pptx`](./VITVellore_SlightlyHallucinating_Submission.pptx) | **VERIFIED** |
| **Language AI Disclosure Document** | [`LangAI3.0_AI_Disclosure.docx`](./LangAI3.0_AI_Disclosure.docx) | **VERIFIED** |
| **System Architecture Brief** | [`docs/System_Architecture_Brief.md`](./docs/System_Architecture_Brief.md) | **VERIFIED** |
| **Benchmarking & Evaluation Report** | [`docs/Benchmarking_Evaluation_Report.md`](./docs/Benchmarking_Evaluation_Report.md) | **VERIFIED** |
| **Telemetry & Observability Schema** | [`docs/Telemetry_Observability_Schema.md`](./docs/Telemetry_Observability_Schema.md) | **VERIFIED** |
| **Video Demonstration Script** | [`docs/Video_Demonstration_Script.md`](./docs/Video_Demonstration_Script.md) | **VERIFIED** |
| **Evaluation Gates (G1–G6)** | Automated benchmark runner (100% Pass across all 6 gates) | **ALL PASSED** |

- [x] **Reproducible Repository**: Source code, pinned dependency lockfile (`requirements.txt`), environment config template (`.env.example`), single-command runners (`docker compose up`, `run.ps1`, `run.sh`, `Makefile`).
- [x] **System Architecture Brief (<= 6 pages)**: Comprehensive design document in `docs/System_Architecture_Brief.md`.
- [x] **Benchmarking & Evaluation Report**: Detailed performance report with 3 edge-case analyses and 2 architectural ablation experiments in `docs/Benchmarking_Evaluation_Report.md`.
- [x] **System Demonstration Video**: Video link in Google Drive with complete minute-by-minute script in `docs/Video_Demonstration_Script.md`.
- [x] **Telemetry & Observability Schema**: Structured logs specification conforming to Page 4 in `docs/Telemetry_Observability_Schema.md`.
- [x] **AI Usage Disclosure**: Fully filled official disclosure form in `LangAI3.0_AI_Disclosure.docx`.
- [x] **Evaluation Gates**: 100% Pass across Gates G1, G2, G3, G4, G5, and G6.

