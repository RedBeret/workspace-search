# API Reference

Complete reference for the workspace-search Python API.

## Installation

```bash
pip install workspace-search
```

## Core Functions

### `index_directory`

```python
from workspace_search import index_directory
import asyncio

stats = asyncio.run(index_directory(
    path="~/notes",
    exclude=["drafts", "archive"],
    model="nomic-embed-text",
    base_url="http://127.0.0.1:11434",
))
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `path` | `Path \| str` | required | Directory to index |
| `exclude` | `list[str] \| None` | `None` | Regex patterns to exclude |
| `model` | `str` | `"nomic-embed-text"` | Ollama model name |
| `base_url` | `str` | `"http://127.0.0.1:11434"` | Ollama server URL |

**Returns:** `dict` with keys `indexed`, `skipped`, `errors`, `total`.

---

### `search`

```python
from workspace_search import search

results = search(
    query="how to handle database migrations",
    top_k=5,
    model="nomic-embed-text",
    base_url="http://127.0.0.1:11434",
)

for result in results:
    print(f"{result.path} [{result.heading}] — {result.score_pct}%")
    print(f"  {result.content_preview}")
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | `str` | required | Natural language query |
| `top_k` | `int` | `5` | Number of results to return |
| `model` | `str` | `"nomic-embed-text"` | Ollama model name |
| `base_url` | `str` | `"http://127.0.0.1:11434"` | Ollama server URL |

**Returns:** `list[SearchResult]`

---

### `SearchResult`

```python
@dataclass
class SearchResult:
    path: str             # Absolute path to the source file
    heading: str          # Markdown heading for this chunk (empty if none)
    content_preview: str  # Truncated chunk content (≤200 chars)
    score: float          # Cosine similarity score (0.0–1.0)
    score_pct: int        # Score as percentage (property)
```

---

### `chunk_markdown`

```python
from workspace_search import chunk_markdown

chunks = chunk_markdown(content, source_path="/path/to/file.md")
# Returns: [{"content": str, "heading": str}, ...]
```

Splits a markdown string into semantic chunks at heading boundaries. Each chunk is at most 4,000 characters. Oversized sections are split at paragraph breaks.

---

### `get_stats`

```python
from workspace_search import get_stats

stats = get_stats()
# {
#   "documents": 47,
#   "chunks": 312,
#   "db_size_bytes": 4194304,
#   "db_path": "/Users/you/.workspace-search/index.db"
# }
```

---

### `clear_index`

```python
from workspace_search import clear_index

clear_index()  # Deletes all documents and chunks
```

---

## Ollama Client

```python
from workspace_search.ollama import get_embedding, check_ollama

# Check if Ollama is running
if not check_ollama():
    print("Ollama is not running. Start with: ollama serve")

# Get an embedding vector
vector = get_embedding("your text here")  # returns list[float] with 768 dims
```

---

## Storage Format

Embeddings are stored as packed binary in SQLite:
```python
struct.pack(f"{len(embedding)}f", *embedding)
```

This gives ~3KB per 768-dim float32 vector, making the index compact for large document collections.

## CLI Reference

All CLI commands support global flags:

```
ws-search [--verbose] [--model TEXT] [--ollama-url TEXT] COMMAND
```

| Command | Description |
|---------|-------------|
| `index <path>` | Index markdown files in a directory |
| `query <text>` | Search indexed documents |
| `stats` | Show index statistics |
| `list` | List all indexed documents |
| `clear` | Delete the entire index |
| `watch <path>` | Watch and auto-reindex on changes |
