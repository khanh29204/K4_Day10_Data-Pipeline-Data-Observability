from __future__ import annotations

from functools import lru_cache
import hashlib
import os
import requests

from langchain_core.embeddings import Embeddings


class MiniLMEmbeddings(Embeddings):
    def __init__(self, model_name: str = "all-minilm"):
        self.model_name = model_name
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self._st_model = None

        # Optional check for sentence_transformers if already installed
        try:
            from sentence_transformers import SentenceTransformer
            self._st_model = SentenceTransformer(model_name)
        except Exception:
            self._st_model = None

    def _get_ollama_embedding(self, text: str) -> list[float] | None:
        try:
            resp = requests.post(
                f"{self.ollama_base_url}/api/embeddings",
                json={"model": self.model_name, "prompt": text},
                timeout=5,
            )
            if resp.status_code == 200:
                data = resp.json()
                if "embedding" in data:
                    return data["embedding"]
        except Exception:
            pass
        return None

    def _fallback_hash_embedding(self, text: str, dim: int = 384) -> list[float]:
        """Fast, lightweight deterministic hashing vectorizer for zero-dependency local embedding."""
        vec = [0.0] * dim
        words = text.lower().split()
        if not words:
            return vec
        for word in words:
            h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
            idx = h % dim
            vec[idx] += 1.0
        norm = sum(x * x for x in vec) ** 0.5
        if norm > 0:
            vec = [x / norm for x in vec]
        return vec

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if self._st_model is not None:
            try:
                embeddings = self._st_model.encode(texts, normalize_embeddings=True)
                return embeddings.tolist()
            except Exception:
                pass

        results: list[list[float]] = []
        for text in texts:
            emb = self._get_ollama_embedding(text)
            if emb is None:
                emb = self._fallback_hash_embedding(text)
            results.append(emb)
        return results

    def embed_query(self, text: str) -> list[float]:
        if self._st_model is not None:
            try:
                embedding = self._st_model.encode([text], normalize_embeddings=True)
                return embedding[0].tolist()
            except Exception:
                pass

        emb = self._get_ollama_embedding(text)
        if emb is None:
            emb = self._fallback_hash_embedding(text)
        return emb

