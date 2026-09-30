"""
Sparse lexical retrieval using BM25Okapi.
"""

import re
from typing import List, Tuple
from rank_bm25 import BM25Okapi
from streaming_rag.schemas import DocumentChunk

STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "because", "as", "what",
    "which", "this", "that", "these", "those", "then", "just", "so", "than",
    "such", "both", "through", "about", "for", "is", "of", "while", "during",
    "to", "from", "in", "out", "on", "off", "again", "further", "then", "once",
    "here", "there", "when", "where", "why", "how", "all", "any", "both",
    "each", "few", "more", "most", "other", "some", "such", "no", "nor",
    "not", "only", "own", "same", "so", "than", "too", "very", "s", "t",
    "can", "will", "just", "don", "should", "now"
}


class SparseIndex:
    """BM25Okapi index for lexical matching over DocumentChunks."""

    def __init__(self, chunks: List[DocumentChunk]):
        self.chunks = chunks
        self.tokenized_corpus = [self._tokenize(f"{c.title} {c.text}") for c in chunks]
        self.bm25 = BM25Okapi(self.tokenized_corpus)

    def _tokenize(self, text: str) -> List[str]:
        tokens = re.findall(r"\b[a-zA-Z0-9_\-]+\b", text.lower())
        return [t for t in tokens if t not in STOPWORDS and len(t) > 1]

    def search(self, query: str, top_k: int = 5) -> List[Tuple[DocumentChunk, float]]:
        tokenized_query = self._tokenize(query)
        if not tokenized_query:
            return []

        doc_scores = self.bm25.get_scores(tokenized_query)
        # Pair with chunk and sort
        scored = list(zip(self.chunks, doc_scores))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]
