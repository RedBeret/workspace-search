"""Tests for search logic (cosine similarity, result ranking)."""

import math
import pytest
from unittest.mock import patch

from workspace_search.search import SearchResult, cosine_similarity, _make_preview, search


def test_cosine_identical_vectors():
    a = [1.0, 0.0, 0.0]
    b = [1.0, 0.0, 0.0]
    assert abs(cosine_similarity(a, b) - 1.0) < 1e-6


def test_cosine_orthogonal_vectors():
    a = [1.0, 0.0]
    b = [0.0, 1.0]
    assert abs(cosine_similarity(a, b)) < 1e-6


def test_cosine_opposite_vectors():
    a = [1.0, 0.0]
    b = [-1.0, 0.0]
    assert abs(cosine_similarity(a, b) + 1.0) < 1e-6


def test_cosine_zero_vector():
    a = [0.0, 0.0]
    b = [1.0, 0.0]
    assert cosine_similarity(a, b) == 0.0


def test_cosine_length_mismatch():
    with pytest.raises(ValueError, match="length mismatch"):
        cosine_similarity([1.0, 2.0], [1.0])


def test_make_preview_short():
    text = "Short content."
    assert _make_preview(text, max_chars=200) == "Short content."


def test_make_preview_truncates():
    text = "word " * 100  # 500 chars
    preview = _make_preview(text, max_chars=50)
    assert len(preview) <= 60  # some slack for word boundary
    assert "…" in preview


def test_make_preview_strips_headings():
    text = "## My Section\nActual content here."
    preview = _make_preview(text)
    assert "##" not in preview
    assert "Actual content" in preview


def test_search_result_score_pct():
    result = SearchResult(
        path="/a.md",
        heading="Test",
        content_preview="preview",
        score=0.876,
    )
    assert result.score_pct == 88


def test_search_returns_top_k():
    """Search should return at most top_k results, ranked by similarity."""
    fake_query_emb = [1.0, 0.0, 0.0, 0.0]
    fake_chunks = [
        {"path": "/a.md", "heading": "A", "content": "content A", "embedding": [1.0, 0.0, 0.0, 0.0]},  # sim=1.0
        {"path": "/b.md", "heading": "B", "content": "content B", "embedding": [0.7, 0.7, 0.0, 0.0]},  # sim~0.7
        {"path": "/c.md", "heading": "C", "content": "content C", "embedding": [0.0, 1.0, 0.0, 0.0]},  # sim=0.0
        {"path": "/d.md", "heading": "D", "content": "content D", "embedding": [0.5, 0.5, 0.5, 0.5]},  # sim~0.5
    ]

    with patch("workspace_search.search.get_embedding", return_value=fake_query_emb), \
         patch("workspace_search.search.get_all_chunks_with_embeddings", return_value=fake_chunks):
        results = search("test query", top_k=2)

    assert len(results) == 2
    assert results[0].path == "/a.md"
    assert results[0].score > results[1].score


def test_search_empty_index():
    with patch("workspace_search.search.get_embedding", return_value=[1.0, 0.0]), \
         patch("workspace_search.search.get_all_chunks_with_embeddings", return_value=[]):
        results = search("test query")

    assert results == []


def test_search_sorts_descending():
    fake_emb = [1.0, 0.0]
    chunks = [
        {"path": f"/{i}.md", "heading": "", "content": "x", "embedding": [float(i) / 10, 0.0]}
        for i in range(1, 6)
    ]
    with patch("workspace_search.search.get_embedding", return_value=fake_emb), \
         patch("workspace_search.search.get_all_chunks_with_embeddings", return_value=chunks):
        results = search("test", top_k=5)

    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)
