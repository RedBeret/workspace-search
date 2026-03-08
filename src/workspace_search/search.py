"""Cosine similarity search over indexed documents."""

import logging
import math
from dataclasses import dataclass

from .ollama import get_embedding
from .store import get_all_chunks_with_embeddings

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """A single search result."""

    path: str
    heading: str
    content_preview: str
    score: float

    @property
    def score_pct(self) -> int:
        """Return score as a percentage (0–100)."""
        return round(self.score * 100)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors.

    Returns a value in [-1, 1], where 1 is identical direction.
    """
    if len(a) != len(b):
        raise ValueError(f"Vector length mismatch: {len(a)} vs {len(b)}")

    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot / (norm_a * norm_b)


def _make_preview(content: str, max_chars: int = 200) -> str:
    """Return a truncated preview of chunk content."""
    # Strip markdown heading from preview
    lines = content.split('\n')
    # Skip heading lines (starting with #)
    body_lines = [ln for ln in lines if not ln.startswith('#')]
    body = ' '.join(' '.join(body_lines).split())  # normalize whitespace
    if len(body) <= max_chars:
        return body
    return body[:max_chars].rsplit(' ', 1)[0] + '…'


def search(
    query: str,
    top_k: int = 5,
    model: str = "nomic-embed-text",
    base_url: str = "http://127.0.0.1:11434",
) -> list[SearchResult]:
    """Search the index for chunks semantically similar to the query.

    Args:
        query: Natural language search query.
        top_k: Number of results to return.
        model: Ollama model name.
        base_url: Ollama server URL.

    Returns:
        List of SearchResult objects, sorted by score descending.
    """
    query_embedding = get_embedding(query, model=model, base_url=base_url)
    chunks = get_all_chunks_with_embeddings()

    if not chunks:
        return []

    scored: list[tuple[float, dict]] = []
    for chunk in chunks:
        try:
            score = cosine_similarity(query_embedding, chunk["embedding"])
            scored.append((score, chunk))
        except ValueError as exc:
            logger.warning("Skipping chunk due to embedding mismatch: %s", exc)

    scored.sort(key=lambda x: x[0], reverse=True)

    results = []
    for score, chunk in scored[:top_k]:
        results.append(
            SearchResult(
                path=chunk["path"],
                heading=chunk["heading"],
                content_preview=_make_preview(chunk["content"]),
                score=score,
            )
        )

    return results
