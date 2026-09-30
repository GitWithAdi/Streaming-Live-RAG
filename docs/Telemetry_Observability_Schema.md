# Telemetry & Observability Schema
**Streaming Live RAG Engine Structured Event Specification**  
*Samsung PRISM Theme 04 Deliverable*  

---

## 1. Schema Overview

The Streaming Live RAG engine emits structured telemetry event records for every conversational turn, ensuring **100% trace coverage** (Gate G6). The schema captures:
- Chronological retrieval trigger logs with sub-second timestamps
- Decomposed sub-queries and parallel routing
- Synthesized grounded answer text
- Grounded citations attributing assertions to `[Doc_ID §Section]`
- Explicit uncertainty indicators
- Answer version transitions and lineage
- Processing latencies (TTFT, early retrieval lead time, total turn latency)
- Token consumption and cost estimations

---

## 2. Output Event Record JSON Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "StructuredOutputRecord",
  "type": "object",
  "required": [
    "retrieval_events",
    "sub_queries",
    "answer",
    "citations"
  ],
  "properties": {
    "retrieval_events": {
      "type": "array",
      "description": "Chronological log of all retrieval triggers executed during the streaming turn",
      "items": {
        "type": "object",
        "required": ["timestamp_s", "query", "trigger"],
        "properties": {
          "timestamp_s": {
            "type": "number",
            "description": "Timestamp in seconds from stream onset when retrieval was triggered"
          },
          "query": {
            "type": "string",
            "description": "Exact query string dispatched to hybrid search index"
          },
          "trigger": {
            "type": "string",
            "enum": ["provisional", "multi_intent", "delta_refinement", "manual"],
            "description": "Trigger category explaining why retrieval was dispatched"
          },
          "sub_intent_id": {
            "type": ["string", "null"],
            "description": "Optional identifier for associated sub-intent topic"
          }
        }
      }
    },
    "sub_queries": {
      "type": "array",
      "description": "Discrete, search-ready sub-queries parsed from compound utterance",
      "items": { "type": "string" }
    },
    "answer": {
      "type": "string",
      "description": "Final synthesized or streamed response addressing all sub-intents with inline citations"
    },
    "citations": {
      "type": "array",
      "description": "Verified corpus chunk citations in [Doc_ID §Section] format",
      "items": { "type": "string" }
    },
    "uncertainty": {
      "type": ["string", "null"],
      "description": "Explicit statement of uncertainty if any sub-intent lacked corpus evidence"
    },
    "session_id": {
      "type": "string",
      "description": "Identifier for active ephemeral session"
    },
    "answer_version": {
      "type": "integer",
      "description": "Lineage version of answer (increments upon late-arriving constraint refinement)"
    },
    "total_latency_ms": {
      "type": "number",
      "description": "Total wall-clock processing time in milliseconds"
    },
    "time_to_first_token_ms": {
      "type": "number",
      "description": "Estimated time in milliseconds before first output token is generated"
    },
    "early_retrieval_lead_time_ms": {
      "type": ["number", "null"],
      "description": "Lead time in milliseconds gained between provisional search start and utterance completion"
    },
    "token_usage": {
      "type": "object",
      "properties": {
        "prompt_tokens": { "type": "integer" },
        "completion_tokens": { "type": "integer" },
        "total_tokens": { "type": "integer" }
      }
    },
    "estimated_cost_usd": {
      "type": "number",
      "description": "Estimated monetary inference cost in USD"
    }
  }
}
```

---

## 3. Example Telemetry Payloads

### 3.1 Example 1: Incremental Multi-Intent Stream Record
```json
{
  "retrieval_events": [
    {
      "timestamp_s": 0.8,
      "query": "Pune workshop venue capacity 30",
      "trigger": "provisional",
      "sub_intent_id": null
    },
    {
      "timestamp_s": 1.6,
      "query": "venue capacity for 30 attendees in Pune",
      "trigger": "multi_intent",
      "sub_intent_id": null
    },
    {
      "timestamp_s": 1.6,
      "query": "cancellation policy and refund terms workshop Pune",
      "trigger": "multi_intent",
      "sub_intent_id": null
    },
    {
      "timestamp_s": 1.6,
      "query": "catering service options workshop Pune",
      "trigger": "multi_intent",
      "sub_intent_id": null
    }
  ],
  "sub_queries": [
    "venue capacity for 30 attendees in Pune",
    "cancellation policy and refund terms workshop Pune",
    "catering service options workshop Pune"
  ],
  "answer": "For a 30-person workshop in Pune, documented options include Venue A and Venue B. Venue A provides classroom seating for up to 45 delegates with interactive AV staging [Doc_12 §2]. Cancellation terms require written notice 5 business days prior to qualify for an 80% refund [Doc_31 §4]. Catering packages cover morning breakfast, working lunch buffets, and continuous beverage stations [Doc_09 §1].",
  "citations": [
    "Doc_12 §2",
    "Doc_31 §4",
    "Doc_09 §1"
  ],
  "uncertainty": null,
  "session_id": "sim_ex1",
  "answer_version": 1,
  "total_latency_ms": 78.62,
  "time_to_first_token_ms": 35.38,
  "early_retrieval_lead_time_ms": 1300.0,
  "token_usage": {
    "prompt_tokens": 69,
    "completion_tokens": 61,
    "total_tokens": 130
  },
  "estimated_cost_usd": 0.000047
}
```

### 3.2 Example 2: Late-Arriving Refinement Record (Answer Version 2)
```json
{
  "retrieval_events": [
    {
      "timestamp_s": 0.0,
      "query": "international travel reimbursement foreign currency receipt verification",
      "trigger": "delta_refinement",
      "sub_intent_id": null
    },
    {
      "timestamp_s": 0.0,
      "query": "late booking exception policy senior director approval",
      "trigger": "delta_refinement",
      "sub_intent_id": null
    }
  ],
  "sub_queries": [
    "international travel reimbursement foreign currency receipt verification",
    "late booking exception policy senior director approval"
  ],
  "answer": "The standard reimbursement rule still applies [Doc_05 §1]. However, the late-booking exception requires senior director approval [Doc_05 §3], and international travel introduces a mandatory foreign currency receipt verification requirement [Doc_07 §2].",
  "citations": [
    "Doc_05 §1",
    "Doc_07 §2",
    "Doc_05 §3"
  ],
  "uncertainty": null,
  "session_id": "sim_ex2",
  "answer_version": 2,
  "total_latency_ms": 42.15,
  "time_to_first_token_ms": 18.96,
  "token_usage": {
    "prompt_tokens": 48,
    "completion_tokens": 42,
    "total_tokens": 90
  },
  "estimated_cost_usd": 0.000032
}
```
