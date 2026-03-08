# Contributing

Contributions welcome! Here's how to get started.

## Development Setup

```bash
git clone https://github.com/RedBeret/workspace-search.git
cd workspace-search
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Running Tests

```bash
pytest tests/ -v
```

Tests for the store, indexer, and search logic do not require Ollama — they mock all embedding calls.

## Adding Tests

- `tests/test_store.py` — SQLite operations
- `tests/test_indexer.py` — markdown chunking
- `tests/test_search.py` — cosine similarity and result ranking

## Submitting a PR

1. Fork the repo
2. Create a branch: `git checkout -b feat/my-feature`
3. Make your changes with tests
4. Push and open a PR

## Code Style

- Type hints on all public functions
- Docstrings on classes and public methods
- `logging` not `print()` for library code
- No hardcoded paths or secrets
