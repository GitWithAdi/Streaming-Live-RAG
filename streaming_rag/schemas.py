"""
Data schemas for Streaming Live RAG Engine.
Adheres strictly to the structured event record specification from Samsung PRISM Theme 04.
"""

from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field


class TranscriptChunk(BaseModel):
    """Represents an incoming streaming speech transcript chunk with timestamp."""
    timestamp_s: float = Field(..., description="Timestamp in seconds from stream start")
    text: str = Field(..., description="Incremental or delta transcript text chunk")
    is_final: bool = Field(False, description="Whether this marks utterance end / final transcript")


class RetrievalEvent(BaseModel):
    """Log record of a triggered retrieval event during streaming."""
    timestamp_s: float = Field(..., description="Timestamp in seconds when retrieval commenced")
    query: str = Field(..., description="Formulated search query dispatched to the index")
    trigger: Literal["provisional", "multi_intent", "delta_refinement", "manual"] = Field(
        ..., description="Trigger category: provisional early search, decomposed multi-intent, or late constraint delta"
    )
    sub_intent_id: Optional[str] = Field(None, description="Identifier of the associated sub-intent if decomposed")


class ControllerDecision(BaseModel):
    """Decision emitted by the Retrieval Controller at each streaming chunk."""
    action: Literal["wait", "retrieve", "no_retrieval"] = Field(
        ..., description="Controller decision: wait for stabilization, retrieve, or suppress retrieval"
    )
    confidence: float = Field(..., description="Decision confidence score [0.0, 1.0]")
    reason: str = Field(..., description="Explanation (e.g. semantic_instability, provisional_entities, presentation_restructure)")
    extracted_entities: List[str] = Field(default_factory=list, description="Entities recognized in accumulated stream")
    is_compound: bool = Field(False, description="Whether multiple implied sub-intents are present")
    sub_queries: List[str] = Field(default_factory=list, description="Decomposed search-ready sub-queries if triggered")


class DocumentChunk(BaseModel):
    """A granular document chunk in the isolated corpus with verifiable section markers."""
    doc_id: str = Field(..., description="Document identifier, e.g. Doc_12")
    section: str = Field(..., description="Section marker, e.g. §2 or 2")
    title: str = Field(..., description="Document or section heading")
    text: str = Field(..., description="Verbatim text content of the chunk")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata, tags, domain")

    @property
    def citation_key(self) -> str:
        """Returns standard citation format, e.g. Doc_12 §2."""
        sec = self.section.replace("§", "").strip()
        return f"{self.doc_id} §{sec}"


class RetrievedCandidate(BaseModel):
    """Retrieved document chunk with retrieval source and fusion score."""
    chunk: DocumentChunk
    dense_score: Optional[float] = None
    sparse_score: Optional[float] = None
    rrf_score: float = Field(..., description="Reciprocal Rank Fusion score")
    rank: int = Field(..., description="Rank in final fused evidence list")
    matched_sub_query: Optional[str] = None


class ClaimNode(BaseModel):
    """An individual factual claim and its corpus citation provenance."""
    claim_id: str
    statement: str
    citations: List[str] = Field(default_factory=list, description="Corpus citations like ['Doc_12 §2']")
    status: Literal["active", "mutated", "superseded", "unverified"] = "active"


class SessionAnswerState(BaseModel):
    """State-preserving answer state across conversation turns."""
    session_id: str
    version: int = Field(1, description="Answer version, incremented on late-arriving constraint refinement")
    base_query: str = Field(..., description="Initial request or topic")
    active_constraints: List[str] = Field(default_factory=list, description="All active constraints including late additions")
    claims: List[ClaimNode] = Field(default_factory=list, description="Current claims graph")
    citations: List[str] = Field(default_factory=list, description="Unique ordered citations supporting the answer")
    raw_answer: str = Field("", description="Current synthesized answer text")
    cached_evidence: List[DocumentChunk] = Field(default_factory=list, description="Retrieved chunks preserved in session")


class StructuredOutputRecord(BaseModel):
    """
    Standard output event record matching Page 4 of the hackathon specification.
    """
    retrieval_events: List[RetrievalEvent] = Field(
        default_factory=list,
        description="Chronological log of all retrieval triggers during the turn"
    )
    sub_queries: List[str] = Field(
        default_factory=list,
        description="List of discrete search-ready sub-queries parsed from compound input"
    )
    answer: str = Field(
        ...,
        description="Streamed / synthesized response addressing all sub-intents with inline citations"
    )
    citations: List[str] = Field(
        default_factory=list,
        description="List of verified corpus chunk citations, e.g. ['Doc_12 §2', 'Doc_31 §4']"
    )
    uncertainty: Optional[str] = Field(
        None,
        description="Explicit uncertainty indicator if corpus lacks evidence for any sub-intent"
    )

    # Extended telemetry fields (Phase 5 / Gate G6)
    session_id: Optional[str] = None
    answer_version: int = 1
    total_latency_ms: Optional[float] = None
    time_to_first_token_ms: Optional[float] = None
    early_retrieval_lead_time_ms: Optional[float] = None
    token_usage: Dict[str, int] = Field(default_factory=dict)
    estimated_cost_usd: Optional[float] = None
