"""SQLite storage for document chunks and embeddings."""

import logging
import sqlite3
import struct
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = Path("~/.workspace-search/index.db").expanduser()


def _connect() -> sqlite3.Connection:
    """Open and initialize the SQLite database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS documents (
            id          INTEGER PRIMARY KEY,
            path        TEXT UNIQUE NOT NULL,
            file_hash   TEXT NOT NULL,
            chunk_count INTEGER NOT NULL DEFAULT 0,
            indexed_at  TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS chunks (
            id          INTEGER PRIMARY KEY,
            doc_id      INTEGER NOT NULL,
            chunk_index INTEGER NOT NULL,
            content     TEXT NOT NULL,
            heading     TEXT NOT NULL DEFAULT '',
            embedding   BLOB NOT NULL,
            FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON chunks(doc_id);
    """)
    conn.commit()
    return conn


def _pack_embedding(embedding: list[float]) -> bytes:
    """Pack a float list into raw bytes."""
    return struct.pack(f"{len(embedding)}f", *embedding)


def _unpack_embedding(blob: bytes) -> list[float]:
    """Unpack raw bytes into a float list."""
    n = len(blob) // 4
    return list(struct.unpack(f"{n}f", blob))


def needs_reindex(path: str, file_hash: str) -> bool:
    """Return True if the file has changed since last index."""
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT file_hash FROM documents WHERE path = ?", (path,)
        ).fetchone()
        if row is None:
            return True
        return row["file_hash"] != file_hash
    finally:
        conn.close()


def upsert_document(
    path: str,
    file_hash: str,
    chunks: list[dict],
    embeddings: list[list[float]],
    indexed_at: str,
) -> None:
    """Insert or replace a document and its chunks.

    Args:
        path: Absolute file path.
        file_hash: SHA256 of file content.
        chunks: List of {content, heading} dicts from the indexer.
        embeddings: Parallel list of embedding vectors.
        indexed_at: ISO 8601 timestamp.
    """
    conn = _connect()
    try:
        with conn:
            # Delete existing entry (cascades to chunks)
            conn.execute("DELETE FROM documents WHERE path = ?", (path,))

            cur = conn.execute(
                "INSERT INTO documents (path, file_hash, chunk_count, indexed_at) "
                "VALUES (?, ?, ?, ?)",
                (path, file_hash, len(chunks), indexed_at),
            )
            doc_id = cur.lastrowid

            for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
                conn.execute(
                    "INSERT INTO chunks (doc_id, chunk_index, content, heading, embedding) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (doc_id, i, chunk["content"], chunk.get("heading", ""), _pack_embedding(emb)),
                )
    finally:
        conn.close()


def get_all_chunks_with_embeddings() -> list[dict]:
    """Return all chunks with their embeddings for search.

    Returns:
        List of dicts with keys: path, heading, content, embedding (list[float]).
    """
    conn = _connect()
    try:
        rows = conn.execute("""
            SELECT d.path, c.heading, c.content, c.embedding
            FROM chunks c
            JOIN documents d ON c.doc_id = d.id
            ORDER BY d.path, c.chunk_index
        """).fetchall()
        return [
            {
                "path": row["path"],
                "heading": row["heading"],
                "content": row["content"],
                "embedding": _unpack_embedding(row["embedding"]),
            }
            for row in rows
        ]
    finally:
        conn.close()


def get_stats() -> dict:
    """Return index statistics."""
    conn = _connect()
    try:
        doc_count = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        chunk_count = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        db_size = DB_PATH.stat().st_size if DB_PATH.exists() else 0
        return {
            "documents": doc_count,
            "chunks": chunk_count,
            "db_size_bytes": db_size,
            "db_path": str(DB_PATH),
        }
    finally:
        conn.close()


def clear_index() -> None:
    """Delete all documents and chunks from the index."""
    conn = _connect()
    try:
        with conn:
            conn.execute("DELETE FROM chunks")
            conn.execute("DELETE FROM documents")
    finally:
        conn.close()


def list_documents() -> list[dict]:
    """Return all indexed documents."""
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT path, chunk_count, indexed_at FROM documents ORDER BY path"
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
