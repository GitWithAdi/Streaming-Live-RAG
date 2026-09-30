"""
Hybrid Search Engine and Evidence Fusion.
Combines Dense Semantic and Sparse BM25 retrieval using Reciprocal Rank Fusion (RRF)
and candidate deduplication across multiple sub-queries.
"""

from typing import List, Dict, Tuple, Optional
from collections import defaultdict
from streaming_rag.schemas import DocumentChunk, RetrievedCandidate
from streaming_rag.indexer.sparse_index import SparseIndex
from streaming_rag.indexer.dense_index import DenseIndex
from streaming_rag.config import HybridRetrieverConfig


class HybridFusionRetriever:
    """Orchestrates dense and sparse retrieval with Reciprocal Rank Fusion."""

    def __init__(
        self,
        chunks: List[DocumentChunk],
        config: Optional[HybridRetrieverConfig] = None,
        use_fast_fallback: bool = False
    ):
        self.chunks = chunks
        self.config = config or HybridRetrieverConfig()
        self.sparse_index = SparseIndex(chunks)
        self.dense_index = DenseIndex(
            chunks,
            model_name=self.config.dense_model_name,
            use_fast_fallback=use_fast_fallback
        )

    def retrieve_single_query(
        self,
        query: str,
        top_k: Optional[int] = None
    ) -> List[RetrievedCandidate]:
        """Retrieves and fuses dense + sparse candidates for a single query."""
        k_val = top_k or self.config.top_k_candidates
        dense_results = self.dense_index.search(query, top_k=k_val * 2)
        sparse_results = self.sparse_index.search(query, top_k=k_val * 2)

        # Map by chunk citation key
        chunk_map: Dict[str, DocumentChunk] = {}
        dense_ranks: Dict[str, int] = {}
        dense_scores: Dict[str, float] = {}
        for rank, (chunk, score) in enumerate(dense_results, start=1):
            key = chunk.citation_key
            chunk_map[key] = chunk
            dense_ranks[key] = rank
            dense_scores[key] = score

        sparse_ranks: Dict[str, int] = {}
        sparse_scores: Dict[str, float] = {}
        for rank, (chunk, score) in enumerate(sparse_results, start=1):
            key = chunk.citation_key
            chunk_map[key] = chunk
            sparse_ranks[key] = rank
            sparse_scores[key] = score

        # Compute RRF score
        # RRF_Score(d) = w_dense / (k + rank_dense) + w_sparse / (k + rank_sparse)
        rrf_scores: Dict[str, float] = {}
        rrf_k = self.config.rrf_k
        w_dense = self.config.dense_weight
        w_sparse = self.config.sparse_weight

        all_keys = set(dense_ranks.keys()) | set(sparse_ranks.keys())
        for key in all_keys:
            score = 0.0
            if key in dense_ranks:
                score += w_dense / (rrf_k + dense_ranks[key])
            if key in sparse_ranks:
                score += w_sparse / (rrf_k + sparse_ranks[key])
            rrf_scores[key] = score

        # Sort descending by RRF score
        sorted_keys = sorted(all_keys, key=lambda k: rrf_scores[k], reverse=True)

        candidates: List[RetrievedCandidate] = []
        for rank, key in enumerate(sorted_keys[:k_val], start=1):
            chunk = chunk_map[key]
            candidates.append(
                RetrievedCandidate(
                    chunk=chunk,
                    dense_score=dense_scores.get(key),
                    sparse_score=sparse_scores.get(key),
                    rrf_score=rrf_scores[key],
                    rank=rank,
                    matched_sub_query=query
                )
            )

        return candidates

    def retrieve_multi_queries(
        self,
        sub_queries: List[str],
        top_k: Optional[int] = None
    ) -> List[RetrievedCandidate]:
        """
        Executes parallel / multi-intent retrieval across discrete sub-queries,
        fuses cross-query candidates with reciprocal rank fusion, and deduplicates.
        """
        k_val = top_k or self.config.top_k_candidates
        all_candidates_by_query: Dict[str, List[RetrievedCandidate]] = {}

        for sq in sub_queries:
            all_candidates_by_query[sq] = self.retrieve_single_query(sq, top_k=k_val)

        # Cross-query reciprocal rank fusion
        combined_scores: Dict[str, float] = defaultdict(float)
        chunk_map: Dict[str, DocumentChunk] = {}
        best_sub_query: Dict[str, Tuple[str, float]] = {}

        for sq, candidates in all_candidates_by_query.items():
            for c in candidates:
                key = c.chunk.citation_key
                chunk_map[key] = c.chunk
                # Aggregate RRF contribution across sub-intents
                combined_scores[key] += c.rrf_score
                if key not in best_sub_query or c.rrf_score > best_sub_query[key][1]:
                    best_sub_query[key] = (sq, c.rrf_score)

        sorted_keys = sorted(combined_scores.keys(), key=lambda k: combined_scores[k], reverse=True)

        fused_candidates: List[RetrievedCandidate] = []
        for rank, key in enumerate(sorted_keys[:k_val], start=1):
            chunk = chunk_map[key]
            sq_match = best_sub_query[key][0]
            fused_candidates.append(
                RetrievedCandidate(
                    chunk=chunk,
                    rrf_score=combined_scores[key],
                    rank=rank,
                    matched_sub_query=sq_match
                )
            )

        return fused_candidates
