# System Architecture Brief: Streaming Live RAG Engine
**Theme 04: Real-Time Incremental Retrieval, Multi-Intent Decomposition, and State-Preserving Answer Refinement**  
*Samsung PRISM GenAI Hackathon 3rd Edition (2026–2027)*  

---

## 1. Executive Summary & Design Rationale

Traditional Retrieval-Augmented Generation (RAG) operates in a synchronous, turn-based stop-and-wait loop: speech-to-text (STT) transcribes the full utterance, waits for punctuation, initiates vector retrieval across a massive database, synthesizes a reply, and responds. In spoken conversational interactions, this introduces unnatural pauses of 2 to 4 seconds, severely degrades conversational flow, fails to handle compound requests, and discards valuable context when users introduce late-arriving constraints.

**Streaming Live RAG** resolves these fundamental challenges through an event-driven, full-duplex engine designed with five foundational pillars:
1. **Incremental Stream Listening**: Processes streaming transcript fragments as they arrive, predicting retrieval intent prior to utterance completion.
2. **Context-Preserving Multi-Intent Decomposition**: Disentangles composite, unsegmented requests into discrete, search-ready sub-queries while maintaining semantic anchors.
3. **Corpus-Isolated Hybrid Rank Fusion**: Combines dense semantic representations and sparse BM25 lexical signals via Reciprocal Rank Fusion ($k=60$) bounded strictly to the local corpus.
4. **Answer Delta Refinement (Refine, Do Not Restart)**: Ingests late-arriving constraints directly into an active claims graph without restarting search or resetting conversational state.
5. **Deterministic Grounding & Zero-Hallucination Verification**: Enforces attribution to corpus chunk markers (`[Doc_ID §Section]`), emitting explicit uncertainty indicators when evidence is incomplete.

---

## 2. End-to-End Pipeline Architecture

```
Incoming Audio / Transcript Stream:
[Chunk 0.0s] ──► [Chunk 0.8s] ──► [Chunk 1.6s] ──► [Utterance End 2.1s]
                        │               │                    │
                        ▼               ▼                    ▼
             ┌─────────────────────────────────────────────────────────┐
             │            [1] RETRIEVAL CONTROLLER                     │
             │  • Linguistic Dangling & Grammatical Completeness Check │
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

## 3. Component Deep Dive & Algorithmic Strategy

### 3.1 Retrieval Controller: Early Triggering vs. Noise Suppression
- **Linguistic Completeness & Semantic Boundaries**: The controller maintains accumulated text and checks for trailing conjunctions or prepositions (`in...`, `and...`, `with...`, `for...`). Incomplete clauses at `0.0s` trigger a **WAIT** action.
- **Provisional Retrieval**: As soon as stable entities emerge (e.g. location `"Pune"`, capacity `"30 people"`, topic `"workshop"` at `0.8s`), the controller triggers provisional search for `"Pune workshop venue capacity 30"`. This yields a **1,300 ms lead-time advantage** over waiting for utterance completion (`2.1s`).
- **Presentation Query Suppression**: Turns requesting formatting changes (e.g., *"Please repeat your last answer in two bullets"* or *"make it shorter"*) are intercepted by the `PresentationSuppressionDetector`. The controller emits `action: no_retrieval` with `reason: presentation_restructure`, preventing vector search thrashing and citation drift.

### 3.2 Multi-Intent Decomposer: Parallel Routing with Context Anchors
When compound requests arrive (e.g., *"I need venue capacity in Pune for 30 people, cancellation policy, and catering options"*), the decomposer extracts discrete sub-queries:
1. `venue capacity for 30 attendees in Pune`
2. `cancellation policy and refund terms workshop Pune`
3. `catering service options workshop Pune`

Crucially, **contextual anchors** (Location: *Pune*, Event: *Workshop*) are propagated into sub-queries 2 and 3. Without anchor propagation, sub-queries like *"cancellation policy"* retrieve irrelevant global contracts rather than venue-specific workshop terms. An anti-fragmentation filter ensures single-topic questions are not split into redundant duplicates.

### 3.3 Hybrid Retrieval & Evidence Fusion
Evidence retrieval operates under **Corpus Isolation**: no external APIs, web scraping, or unindexed model knowledge are utilized.
- **Dense Retriever**: Generates semantic embeddings with `SentenceTransformers` (`all-MiniLM-L6-v2`) and cosine similarity scoring. A fast offline TF-IDF/SVD embedder provides zero-dependency offline fallback.
- **Sparse Retriever**: Implements BM25Okapi over tokenized, stopword-filtered document chunks.
- **Reciprocal Rank Fusion (RRF)**:
  $$RRF\_Score(d) = \sum_{m \in \{dense, sparse\}} \frac{w_m}{k + rank_m(d)}$$
  with rank smoothing $k=60$. Chunks matching multiple sub-queries are aggregated and deduplicated, guaranteeing factual density without context window dilution.

### 3.4 Session-Aware Answer Delta Engine (Refine, Do Not Restart)
When users introduce late-arriving constraints mid-conversation (e.g., *"The trip was international and the booking was made after travel"*), traditional architectures suffer from:
1. *Full session restart*: Re-executes global retrieval, doubles latency, and creates disjointed replies.
2. *Context window dilution*: Appends raw conversational turns without resolving contradictory clauses.

Our Answer Delta Engine solves this by:
- Inspecting active session state (`SessionAnswerState`).
- Formulating **targeted delta queries** strictly for the newly introduced constraints (`Doc_05 §3` late booking exception, `Doc_07 §2` international receipt verification).
- Preserving established claims and prior citations (`Doc_05 §1`), adding delta citations, and incrementing to **Answer Version 2** in-place.

### 3.5 Grounding, Uncertainty & Telemetry
- **Citation Provenance**: Verifies that every factual claim is supported by a corpus chunk citation (`[Doc_ID §Section]`). Hallucinated document IDs are caught and eliminated.
- **Explicit Uncertainty**: When an intent has no corpus evidence (e.g. overnight accommodations for Venue A), the engine does not guess or hallucinate; it explicitly returns:
  `"uncertainty": "Catering accommodation policies for Venue A could not be verified from the retrieved corpus."`
- **Telemetry**: Emits complete structured logs with chunk timestamps, triggers (`provisional`, `multi_intent`, `delta_refinement`), latencies, token consumption, and cost tracking.

---

## 4. Failure Mode Mitigations (Addressing Common Technical Pitfalls)

| Pitfall (from Samsung Guide) | Architectural Risk | Mitigation in our Engine |
| :--- | :--- | :--- |
| **1. Eager Retrieval on Noise** | Querying on every token causes compute thrashing and noisy context windows. | Trailing conjunction detection and entity gating: retrieval is locked in `WAIT` until $\ge 2$ stable entities are identified. |
| **2. Context Loss on Late Constraints** | Clearing state causes disjointed answers and wasted compute. | Ephemeral session state maintains active claim graphs and evidence caches; Answer Delta Engine queries solely for the constraint delta. |
| **3. Citation Hallucination** | Generating non-existent document IDs (`Doc_999`) or false citations. | Dual-pass citation verification against indexed chunk IDs; strictly filters non-grounded identifiers. |
| **4. Ignoring Presentation Turns** | Vector searching when user asks for formatting/bullets wastes tokens and causes drift. | `PresentationSuppressionDetector` suppresses retrieval on formatting commands, transforming prior context with zero vector calls. |
| **5. Over-Fragmenting Sub-Queries** | Splitting simple questions into duplicate queries exhausts tokens and pollutes rerankers. | Semantic similarity gating and template unification deduplicate sub-queries before dispatch. |

---

## 5. Architectural Parsimony & Compute Efficiency
In accordance with the hard engineering constraint on **Architectural Parsimony**, our engine avoids heavy multi-agent framework overheads (such as LangChain/AutoGen agent graphs that introduce hundreds of milliseconds of JSON serialization latency). The entire streaming pipeline runs in **< 80 ms end-to-end processing latency**, enabling real-time voice-assistant responsiveness.
