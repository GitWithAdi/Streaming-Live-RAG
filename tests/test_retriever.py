"""
Unit tests for Dense, Sparse, and Hybrid RRF Retrieval.
"""

from streaming_rag.indexer.chunker import CorpusChunker
from streaming_rag.indexer.sparse_index import SparseIndex
from streaming_rag.indexer.dense_index import DenseIndex
from streaming_rag.indexer.hybrid_fusion import HybridFusionRetriever


def test_sparse_retrieval():
    chunks = CorpusChunker.load_corpus("data/corpus/venue_booking_corpus.json")
    sparse = SparseIndex(chunks)
    results = sparse.search("cancellation refund terms", top_k=2)

    assert len(results) > 0
    top_chunk, score = results[0]
    assert "Doc_31" in top_chunk.doc_id
    assert score > 0


def test_dense_retrieval():
    chunks = CorpusChunker.load_corpus("data/corpus/venue_booking_corpus.json")
    dense = DenseIndex(chunks, use_fast_fallback=False)
    results = dense.search("places to host 30 people in Pune", top_k=2)

    assert len(results) > 0
    top_chunk, score = results[0]
    assert "Doc_12" in top_chunk.doc_id
    assert "2" in top_chunk.section


def test_hybrid_rrf_fusion():
    chunks = CorpusChunker.load_corpus("data/corpus/venue_booking_corpus.json")
    retriever = HybridFusionRetriever(chunks, use_fast_fallback=False)
    candidates = retriever.retrieve_single_query("catering and lunch options in Pune", top_k=3)

    assert len(candidates) > 0
    citation_keys = [c.chunk.citation_key for c in candidates]
    assert any("Doc_09" in k for k in citation_keys)
    assert candidates[0].rrf_score > 0
