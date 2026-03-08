# Getting Started with workspace-search

This guide walks you through setting up `workspace-search` for the first time.

## Prerequisites

Before you begin, make sure you have the following installed:

- Python 3.12 or later
- [Ollama](https://ollama.com/download) for local embedding generation
- The `nomic-embed-text` model pulled via Ollama

To install Ollama and pull the model:

```bash
# Install Ollama (macOS)
brew install ollama

# Start the Ollama server
ollama serve

# In another terminal, pull the embedding model
ollama pull nomic-embed-text
```

## Installation

Install `workspace-search` from PyPI:

```bash
pip install workspace-search
```

Or install from source for development:

```bash
git clone https://github.com/RedBeret/workspace-search.git
cd workspace-search
pip install -e ".[dev]"
```

## First Index

Point `ws-search index` at any directory containing markdown files:

```bash
ws-search index ~/notes
```

You should see output like:

```
Indexing /Users/you/notes with model nomic-embed-text...
  Indexed: 2024-architecture.md (8 chunks)
  Indexed: deployment-runbook.md (12 chunks)
  Indexed: api-design-notes.md (5 chunks)
  ...
Done — 47 indexed, 3 skipped, 0 errors in 42.1s
```

Files are skipped if they haven't changed since the last index run.

## First Search

```bash
ws-search query "how to deploy a stateful service"
```

## Configuration

The index is stored at `~/.workspace-search/index.db`. No configuration file is needed for standard use.

For a different Ollama model or server URL, use global flags:

```bash
ws-search --model mxbai-embed-large --ollama-url http://192.168.1.5:11434 index ~/notes
```

## Troubleshooting

### "Cannot connect to Ollama"

Make sure Ollama is running:
```bash
ollama serve
```

### "Model not available"

Pull the model before indexing:
```bash
ollama pull nomic-embed-text
```

### Index seems stale

Force a full re-index by clearing and re-indexing:
```bash
ws-search clear
ws-search index ~/notes
```
