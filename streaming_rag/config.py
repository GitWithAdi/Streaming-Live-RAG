"""
Configuration settings for Streaming Live RAG.
Includes parameters for retrieval controller thresholds, hybrid search weights,
reciprocal rank fusion (RRF), session state management, and telemetry.
"""

from typing import Dict, Any
from pydantic import BaseModel, Field


class RetrievalControllerConfig(BaseModel):
    """Thresholds and flags for the real-time Retrieval Controller."""
    min_tokens_for_intent: int = 4
    min_entities_for_provisional: int = 2
    stability_confidence_threshold: float = 0.65
    compound_conjunction_weight: float = 0.4
    suppression_confidence_threshold: float = 0.75
    provisional_lead_target_ratio: float = 0.80  # Target >= 80% early retrieval lead


class HybridRetrieverConfig(BaseModel):
    """Parameters for Dense, Sparse (BM25), and RRF Fusion."""
    dense_model_name: str = "all-MiniLM-L6-v2"
    dense_weight: float = 0.5
    sparse_weight: float = 0.5
    rrf_k: int = 60
    top_k_candidates: int = 5
    deduplication_similarity_threshold: float = 0.88


class GroundingConfig(BaseModel):
    """Parameters for citation attribution and uncertainty detection."""
    min_citation_support_ratio: float = 0.85  # Target Gate G4 >= 85%
    citation_regex: str = r"\[Doc_\d+\s*§\d+\]"
    uncertainty_phrase_template: str = "{sub_intent} could not be verified from the retrieved corpus."


class TelemetryConfig(BaseModel):
    """Instrumentation settings for observability traces."""
    track_latencies: bool = True
    track_token_costs: bool = True
    cost_per_1k_prompt_tokens_usd: float = 0.00015
    cost_per_1k_completion_tokens_usd: float = 0.00060


class SystemConfig(BaseModel):
    """Master system configuration."""
    controller: RetrievalControllerConfig = Field(default_factory=RetrievalControllerConfig)
    retriever: HybridRetrieverConfig = Field(default_factory=HybridRetrieverConfig)
    grounding: GroundingConfig = Field(default_factory=GroundingConfig)
    telemetry: TelemetryConfig = Field(default_factory=TelemetryConfig)
    corpus_directory: str = "data/corpus"
    benchmark_directory: str = "data/benchmarks"


# Default global instance
CONFIG = SystemConfig()
