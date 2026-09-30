# System Demonstration Video Script & Storyboard (<= 5 Minutes)
**Theme 04: Streaming Live RAG**  
*Samsung PRISM GenAI Hackathon 3rd Edition*  

---

## Video Outline & Timing Breakdown

| Section | Timestamp | Focus Area | Live Visual / Screen Activity |
| :--- | :---: | :--- | :--- |
| **1. Introduction & Motivation** | 0:00 – 0:45 | The High-Conversational Latency Problem | Comparison slide: Traditional stop-and-wait RAG vs Full-Duplex Streaming Live RAG. |
| **2. Incremental Listening & Early Retrieval** | 0:45 – 1:45 | Example 1: Provisional Trigger & Lead Time | Run `python cli.py --stream-example 1`. Highlight `0.0s WAIT` ➔ `0.8s PROVISIONAL RETRIEVE` (1.3s lead time). |
| **3. Multi-Intent Decomposition** | 1:45 – 2:40 | Compound Query Deconstruction | Show 3 parallel sub-queries extracted at `1.6s` with contextual anchor propagation (`Pune`, `workshop`). |
| **4. State-Preserving Refinement** | 2:40 – 3:35 | Example 2: Answer Delta Refinement (v1 ➔ v2) | Run `python cli.py --stream-example 2`. Show late constraint injected, state continuity verified, targeted delta search. |
| **5. Query Suppression & Grounding** | 3:35 – 4:15 | Example 3: Presentation Suppression & Citations | Show bullet point command executed with 0 vector searches, preserving `[Doc_05 §1]`. Show uncertainty indicator on missing data. |
| **6. Benchmark & Telemetry Summary** | 4:15 – 5:00 | Acceptance Gates G1 – G6 Scorecard | Run `python cli.py --benchmark`. Display 100% Pass across all 6 gates and telemetry traces. |

---

## Detailed Narration Script

### [0:00 – 0:45] Section 1: Introduction & The Core Problem
*(Visual: Architecture diagram from System Architecture Brief)*  
**Speaker**:  
"Hello, we are presenting our prototype for Samsung PRISM Theme 04: **Streaming Live RAG**. In conversational voice assistants, conventional RAG systems force users to wait several seconds after they finish speaking before initiating vector searches. Furthermore, human speech naturally packages multiple implied intents and introduces late-arriving constraints mid-conversation. Traditional pipelines either discard context or trigger expensive restarts.  

Our solution is an event-driven **Streaming Live RAG Engine** that listens incrementally, predicts retrieval intent before speech completion, parallelizes multi-intent searches, and mutates active answer states in-place."

---

### [0:45 – 1:45] Section 2: Incremental Listening & Provisional Retrieval
*(Visual: Terminal running `python cli.py --stream-example 1`)*  
**Speaker**:  
"Let’s watch the streaming simulator in action.  
At timestamp `0.0s`, the user starts: *'I need to plan a customer workshop in...'*  
Notice our Retrieval Controller. Because the phrase ends with a dangling preposition and lacks stable entities, the controller issues **WAIT**. This prevents eager retrieval thrashing on premature noise.  

At timestamp `0.8s`, the user continues: *'...Pune for 30 people, and I need...'*.  
Instantly, the Intent Stability Classifier detects stable geographic and capacity entities. It triggers a **PROVISIONAL RETRIEVAL** for *'Pune workshop venue capacity 30'*. This grants the system a **1,300 ms lead-time advantage** while the user is still speaking!"

---

### [1:45 – 2:40] Section 3: Multi-Intent Decomposition & Hybrid Evidence Fusion
*(Visual: Highlight sub-queries and RRF ranking in terminal output)*  
**Speaker**:  
"At timestamp `1.6s`, the user completes the compound request: *'...the cancellation policy and the catering options.'*  
Our Multi-Intent Decomposer detects compound intent boundaries and parses the utterance into three search-ready sub-queries:
1. Venue capacity for 30 attendees in Pune
2. Cancellation terms and refund policies for Pune workshop venues
3. Catering service options for Pune workshops  

Notice that context anchors—such as *Pune* and *workshop*—are automatically preserved across all sub-queries to prevent context drift.  
The engine executes these searches in parallel across our isolated corpus, fusing dense semantic embeddings and sparse BM25 scores using **Reciprocal Rank Fusion** with $k=60$.  
When speech ends at `2.1s`, the answer is synthesized immediately: fully grounded with verified citations `[Doc_12 §2]`, `[Doc_31 §4]`, and `[Doc_09 §1]`."

---

### [2:40 – 3:35] Section 4: Late-Arriving Detail Refinement (Refine, Do Not Restart)
*(Visual: Terminal running `python cli.py --stream-example 2`)*  
**Speaker**:  
"Now let's look at how the engine handles conversational updates. In Turn 1, the user asks to summarize the travel reimbursement policy. The engine generates Answer Version 1 citing `[Doc_05 §1]`.  

In Turn 2, the user introduces a late constraint: *'The trip was international and the booking was made after travel.'*  
Instead of wiping session memory or restarting full-corpus retrieval, our **Answer Delta Engine** recognizes a constraint modification on an active topic. It issues targeted delta queries for international receipts and late-booking exceptions.  
It mutates only the affected claims in the active state, preserves prior citations, adds delta citations `[Doc_05 §3]` and `[Doc_07 §2]`, and seamlessly increments to **Answer Version 2**."

---

### [3:35 – 4:15] Section 5: Query Suppression & Strict Grounding Verification
*(Visual: Terminal running `python cli.py --stream-example 3`)*  
**Speaker**:  
"What happens when the user asks a presentation-only question? *'Please repeat your last answer in two bullets.'*  
Our `PresentationSuppressionDetector` detects formatting intent and emits `action: no_retrieval`. Notice in the event log: **zero vector queries are dispatched**. The engine converts existing session context into two clear bullets while retaining citations without hallucination.  

Additionally, if a user requests unindexed details—such as overnight hotel accommodations—the engine emits an explicit uncertainty indicator rather than hallucinating answers."

---

### [4:15 – 5:00] Section 6: Evaluation Gates & Single-Command Launch
*(Visual: Terminal running `python -m evaluation.benchmark_runner`)*  
**Speaker**:  
"Finally, we run our automated replay suite evaluating all six quantitative acceptance gates:
- **Gate G1 Reproducibility**: PASS via single-command container or CLI runner
- **Gate G2 Early Retrieval**: 100% of eligible queries triggered before speech end
- **Gate G3 Multi-Intent Identification**: 100% compound query decomposition
- **Gate G4 Factual Grounding**: 100% citation support with 0 hallucinated IDs
- **Gate G5 Session Refinement**: 100% state continuity verified
- **Gate G6 Telemetry & Observability**: 100% structured trace coverage  

The system is packaged with Docker, pinned dependency lockfiles, and full telemetry logging. Thank you!"
