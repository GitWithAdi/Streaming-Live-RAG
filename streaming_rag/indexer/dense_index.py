"""
Dense semantic retrieval index using vector embeddings and cosine similarity.
Supports SentenceTransformers with an offline fallback dense semantic embedder.
"""

from typing import List, Tuple, Optional
import numpy as np
from streaming_rag.schemas import DocumentChunk


_MODEL_CACHE = {}


class DenseIndex:
    """Vector embedding index for semantic matching over DocumentChunks."""

    def __init__(self, chunks: List[DocumentChunk], model_name: str = "all-MiniLM-L6-v2", use_fast_fallback: bool = False):
        self.chunks = chunks
        self.model_name = model_name
        self.model = None
        self.use_fallback = use_fast_fallback
        self.chunk_embeddings: Optional[np.ndarray] = None
        self._init_encoder()

    def _init_encoder(self):
        corpus_texts = [f"{c.title}. {c.text}" for c in self.chunks]

        if not self.use_fallback:
            try:
                from sentence_transformers import SentenceTransformer
                if self.model_name not in _MODEL_CACHE:
                    _MODEL_CACHE[self.model_name] = SentenceTransformer(self.model_name)
                self.model = _MODEL_CACHE[self.model_name]
                embeddings = self.model.encode(corpus_texts, convert_to_numpy=True, normalize_embeddings=True)
                self.chunk_embeddings = embeddings
                return
            except Exception as e:
                # Fallback gracefully if model cannot be loaded
                self.use_fallback = True

        # Fast offline TF-IDF + Subword dense embedding fallback
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.decomposition import TruncatedSVD
        from sklearn.preprocessing import normalize

        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            sublinear_tf=True,
            stop_words="english"
        )
        tfidf_matrix = self.vectorizer.fit_transform(corpus_texts)
        n_features = tfidf_matrix.shape[1]
        n_components = min(64, max(2, n_features - 1, len(corpus_texts) - 1))

        if n_components >= 2 and n_features > n_components:
            self.svd = TruncatedSVD(n_components=n_components, random_state=42)
            dense = self.svd.fit_transform(tfidf_matrix)
        else:
            self.svd = None
            dense = tfidf_matrix.toarray()

        self.chunk_embeddings = normalize(dense, norm="l2")

    def search(self, query: str, top_k: int = 5) -> List[Tuple[DocumentChunk, float]]:
        """Computes cosine similarity between query embedding and indexed chunks."""
        if not self.chunks or self.chunk_embeddings is None:
            return []

        if not self.use_fallback and self.model is not None:
            q_emb = self.model.encode([query], convert_to_numpy=True, normalize_embeddings=True)[0]
        else:
            q_vec = self.vectorizer.transform([query])
            if self.svd is not None:
                dense_q = self.svd.transform(q_vec)
            else:
                dense_q = q_vec.toarray()
            norm = np.linalg.norm(dense_q)
            q_emb = dense_q[0] / (norm + 1e-9)

        # Cosine similarity (both vectors are normalized)
        sims = np.dot(self.chunk_embeddings, q_emb)
        top_indices = np.argsort(sims)[::-1][:top_k]

        return [(self.chunks[i], float(sims[i])) for i in top_indices]
