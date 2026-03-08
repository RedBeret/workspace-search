# workspace-search

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Local semantic search for your markdown notes and docs — powered by Ollama. Zero cloud, zero tracking.**

`grep` is exact-match only. `workspace-search` understands meaning: query *"how do I handle timeouts"* and it finds your notes on connection resilience, error budgets, and retry logic — even when those words never appear together.

---

## Why local?

Your notes probably contain things you don't want sent to an API: internal project names, architecture decisions, credentials references, personal thoughts. `workspace-search` uses [Ollama](https://ollama.com) to generate embeddings on your machine. No data leaves.

---

## Prerequisites

1. **Ollama** — [Install](https://ollama.com/download), then pull the embedding model:
   ```bash
   ollama pull nomic-embed-text
   ```

2. **Python 3.12+**

---

## Install

```bash
pip install workspace-search
```

Or from source:
```bash
git clone https://github.com/RedBeret/workspace-search.git
cd workspace-search
pip install -e .
```

---

## Usage

### Index a directory

```bash
ws-search index ~/notes
```

This walks `~/notes`, chunks each `.md` file by heading, embeds each chunk using `nomic-embed-text` via Ollama, and stores everything in `~/.workspace-search/index.db`.

Files that haven't changed (same SHA256) are skipped on subsequent runs.

### Search

```bash
ws-search query "deployment strategies for stateful services"
```

Example output:
```
Results for: "deployment strategies for stateful services"

  1. docs/kubernetes/deployments.md  [Rolling Updates]          92%
     Rolling deployments allow you to update pods incrementally without
     downtime. For stateful services, consider PodDisruptionBudgets...

  2. notes/2025-06-architecture.md  [Database Migration Notes]  87%
     Blue-green deployments work well here. The key risk is data schema
     drift between the two versions running simultaneously...

  3. ops/runbooks/deploy.md  [Deployment Checklist]             81%
     Before deploying a stateful service: snapshot the database, verify
     replication lag is <100ms, coordinate with on-call...
```

### Other commands

```bash
ws-search stats          # index statistics
ws-search list           # list all indexed documents
ws-search clear          # delete the index and start fresh
ws-search watch ~/notes  # watch for changes and re-index automatically
```

---

## How it works

1. **Chunking** — Each markdown file is split into chunks at heading boundaries (`##`, `###`). Oversized chunks are split further at paragraph breaks. This keeps each embedding chunk semantically coherent.

2. **Embedding** — Each chunk is sent to Ollama's `nomic-embed-text` model, producing a 768-dimensional vector that represents the chunk's meaning.

3. **Storage** — Embeddings are stored as raw binary in SQLite (via `struct.pack`). No external vector database required.

4. **Search** — Your query is embedded the same way, then cosine similarity is computed against all stored chunks. Top-k results are returned with their source file and section heading.

---

## Configuration

The index lives at `~/.workspace-search/index.db`. No config file needed for basic use.

For custom Ollama URLs or models, pass flags:

```bash
ws-search index ~/notes --model nomic-embed-text --ollama-url http://localhost:11434
ws-search query "something" --model nomic-embed-text --top-k 10
```

---

## Compared to grep

| | `grep` | `workspace-search` |
|---|---|---|
| Exact keyword match | ✅ | ✅ |
| Semantic / meaning match | ❌ | ✅ |
| Fuzzy matching | ❌ | ✅ |
| Cloud dependency | ✅ none | ✅ none |
| Setup required | ✅ none | Ollama + model pull |
| Speed (after index) | Fast | Fast |

**When to use grep:** You know the exact word you're looking for.
**When to use workspace-search:** You know what you mean but not the exact words.

---

## Contributing

Issues and PRs welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

MIT — see [LICENSE](LICENSE).
