"""Document chunking and embedding pipeline."""

import asyncio
import hashlib
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

from .ollama import get_embedding
from .store import needs_reindex, upsert_document

logger = logging.getLogger(__name__)

MAX_CHUNK_CHARS = 4000
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".tox"}


def chunk_markdown(content: str, source_path: str = "") -> list[dict]:
    """Split markdown content into semantic chunks at heading boundaries.

    Each chunk is at most MAX_CHUNK_CHARS characters. Oversized sections
    are split further at paragraph breaks.

    Args:
        content: Raw markdown content.
        source_path: File path (used for logging only).

    Returns:
        List of dicts with keys: content (str), heading (str).
    """
    # Split on ## or ### headings
    heading_pattern = re.compile(r'^(#{2,3})\s+(.+)$', re.MULTILINE)
    chunks: list[dict] = []

    # Find all heading positions
    boundaries = [(m.start(), m.group(2)) for m in heading_pattern.finditer(content)]

    if not boundaries:
        # No headings — treat entire file as one chunk
        return _split_large_chunk(content, heading="")

    # Content before the first heading
    preamble = content[: boundaries[0][0]].strip()
    if preamble:
        chunks.extend(_split_large_chunk(preamble, heading=""))

    # Content between headings
    for i, (start, heading) in enumerate(boundaries):
        end = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(content)
        # Include heading line itself in the chunk text
        section = content[start:end].strip()
        chunks.extend(_split_large_chunk(section, heading=heading))

    return [c for c in chunks if c["content"].strip()]


def _split_large_chunk(text: str, heading: str) -> list[dict]:
    """Split text into chunks of at most MAX_CHUNK_CHARS by paragraph breaks."""
    if len(text) <= MAX_CHUNK_CHARS:
        return [{"content": text, "heading": heading}]

    paragraphs = re.split(r'\n{2,}', text)
    chunks: list[dict] = []
    current_parts: list[str] = []
    current_len = 0

    for para in paragraphs:
        if current_len + len(para) > MAX_CHUNK_CHARS and current_parts:
            chunks.append({"content": "\n\n".join(current_parts), "heading": heading})
            current_parts = [para]
            current_len = len(para)
        else:
            current_parts.append(para)
            current_len += len(para)

    if current_parts:
        chunks.append({"content": "\n\n".join(current_parts), "heading": heading})

    return chunks


def _file_hash(path: Path) -> str:
    """Compute SHA256 of file content."""
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _should_skip(path: Path, exclude: list[str] | None) -> bool:
    """Return True if the path should be excluded from indexing."""
    # Skip hidden directories and standard skip dirs
    for part in path.parts:
        if part in SKIP_DIRS or (part.startswith('.') and part != '.'):
            return True

    if exclude:
        path_str = str(path)
        for pattern in exclude:
            if re.search(pattern, path_str):
                return True

    return False


async def index_directory(
    path: Path,
    *,
    exclude: list[str] | None = None,
    model: str = "nomic-embed-text",
    base_url: str = "http://127.0.0.1:11434",
) -> dict:
    """Index all markdown files in a directory.

    Args:
        path: Directory to index.
        exclude: List of regex patterns to exclude.
        model: Ollama model name.
        base_url: Ollama server URL.

    Returns:
        Dict with indexed, skipped, and error counts.
    """
    path = Path(path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Directory not found: {path}")

    md_files = sorted(path.rglob("*.md"))
    stats = {"indexed": 0, "skipped": 0, "errors": 0, "total": 0}
    now = datetime.now(timezone.utc).isoformat()

    for md_file in md_files:
        if _should_skip(md_file, exclude):
            stats["skipped"] += 1
            continue

        stats["total"] += 1

        try:
            fhash = _file_hash(md_file)
            path_str = str(md_file)

            if not needs_reindex(path_str, fhash):
                logger.debug("Unchanged: %s", md_file)
                stats["skipped"] += 1
                continue

            content = md_file.read_text(encoding="utf-8", errors="replace")
            chunks = chunk_markdown(content, source_path=path_str)

            if not chunks:
                stats["skipped"] += 1
                continue

            # Embed each chunk (synchronously — Ollama is local, fast enough)
            embeddings = []
            for chunk in chunks:
                emb = get_embedding(chunk["content"], model=model, base_url=base_url)
                embeddings.append(emb)

            upsert_document(path_str, fhash, chunks, embeddings, now)
            stats["indexed"] += 1
            print(f"  Indexed: {md_file.relative_to(path)} ({len(chunks)} chunks)")

        except Exception as exc:
            logger.error("Error indexing %s: %s", md_file, exc)
            stats["errors"] += 1
            print(f"  Error:   {md_file}: {exc}")

    return stats
