"""Tests for SQLite store operations."""

import os
import struct
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


# Patch DB_PATH to use a temp file for all tests
@pytest.fixture(autouse=True)
def tmp_db(tmp_path):
    """Redirect the store's DB to a temporary path."""
    test_db = tmp_path / "test.db"
    with patch("workspace_search.store.DB_PATH", test_db):
        yield test_db


from workspace_search.store import (
    clear_index,
    get_all_chunks_with_embeddings,
    get_stats,
    list_documents,
    needs_reindex,
    upsert_document,
)


def make_embedding(dims: int = 4, val: float = 0.5) -> list[float]:
    return [val] * dims


def test_needs_reindex_new_file():
    assert needs_reindex("/nonexistent/file.md", "abc123") is True


def test_needs_reindex_unchanged():
    chunks = [{"content": "hello", "heading": ""}]
    embeddings = [make_embedding()]
    upsert_document("/file.md", "hash1", chunks, embeddings, "2026-01-01T00:00:00Z")
    assert needs_reindex("/file.md", "hash1") is False


def test_needs_reindex_changed():
    chunks = [{"content": "hello", "heading": ""}]
    embeddings = [make_embedding()]
    upsert_document("/file.md", "hash1", chunks, embeddings, "2026-01-01T00:00:00Z")
    assert needs_reindex("/file.md", "hash2") is True


def test_upsert_and_retrieve():
    chunks = [
        {"content": "First section content", "heading": "Intro"},
        {"content": "Second section content", "heading": "Details"},
    ]
    embeddings = [make_embedding(4, 0.1), make_embedding(4, 0.9)]
    upsert_document("/path/to/doc.md", "abc", chunks, embeddings, "2026-01-01T00:00:00Z")

    result = get_all_chunks_with_embeddings()
    assert len(result) == 2
    assert result[0]["path"] == "/path/to/doc.md"
    assert result[0]["heading"] == "Intro"
    assert result[0]["content"] == "First section content"
    assert len(result[0]["embedding"]) == 4
    assert abs(result[0]["embedding"][0] - 0.1) < 1e-5


def test_upsert_replaces_existing():
    """Re-indexing a file replaces old chunks."""
    old_chunks = [{"content": "old content", "heading": "Old"}]
    upsert_document("/file.md", "hash1", old_chunks, [make_embedding()], "2026-01-01T00:00:00Z")

    new_chunks = [
        {"content": "new content A", "heading": "New A"},
        {"content": "new content B", "heading": "New B"},
    ]
    upsert_document("/file.md", "hash2", new_chunks, [make_embedding(), make_embedding()], "2026-01-02T00:00:00Z")

    result = get_all_chunks_with_embeddings()
    assert len(result) == 2
    assert result[0]["content"] == "new content A"


def test_get_stats():
    chunks = [{"content": "text", "heading": ""}]
    upsert_document("/a.md", "h1", chunks, [make_embedding()], "2026-01-01T00:00:00Z")
    upsert_document("/b.md", "h2", chunks * 2, [make_embedding(), make_embedding()], "2026-01-01T00:00:00Z")

    stats = get_stats()
    assert stats["documents"] == 2
    assert stats["chunks"] == 3


def test_clear_index():
    chunks = [{"content": "text", "heading": ""}]
    upsert_document("/file.md", "h1", chunks, [make_embedding()], "2026-01-01T00:00:00Z")
    clear_index()
    stats = get_stats()
    assert stats["documents"] == 0
    assert stats["chunks"] == 0


def test_list_documents():
    chunks = [{"content": "text", "heading": ""}]
    upsert_document("/a.md", "h1", chunks, [make_embedding()], "2026-01-01T00:00:00Z")
    upsert_document("/b.md", "h2", chunks, [make_embedding()], "2026-01-01T00:00:00Z")
    docs = list_documents()
    paths = [d["path"] for d in docs]
    assert "/a.md" in paths
    assert "/b.md" in paths


def test_empty_index():
    result = get_all_chunks_with_embeddings()
    assert result == []
