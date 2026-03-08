"""Ollama API client for generating text embeddings."""

import logging
import urllib.error
import urllib.request
import json

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "nomic-embed-text"
DEFAULT_BASE_URL = "http://127.0.0.1:11434"


def get_embedding(
    text: str,
    model: str = DEFAULT_MODEL,
    base_url: str = DEFAULT_BASE_URL,
) -> list[float]:
    """Generate an embedding vector for the given text.

    Args:
        text: The text to embed.
        model: Ollama model name (default: nomic-embed-text).
        base_url: Ollama server URL (default: http://127.0.0.1:11434).

    Returns:
        A list of floats representing the embedding vector.

    Raises:
        RuntimeError: If Ollama is not running or the model is not available.
    """
    url = f"{base_url.rstrip('/')}/api/embeddings"
    payload = json.dumps({"model": model, "prompt": text}).encode()

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Cannot connect to Ollama at {base_url}. "
            "Make sure Ollama is running: `ollama serve`"
        ) from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Unexpected response from Ollama: {exc}") from exc

    if "embedding" not in data:
        raise RuntimeError(
            f"Model '{model}' is not available. "
            f"Pull it first: `ollama pull {model}`\n"
            f"Ollama response: {data}"
        )

    embedding: list[float] = data["embedding"]
    logger.debug("Embedded %d chars → %d dims", len(text), len(embedding))
    return embedding


def check_ollama(base_url: str = DEFAULT_BASE_URL) -> bool:
    """Return True if Ollama is reachable at the given URL."""
    try:
        with urllib.request.urlopen(f"{base_url.rstrip('/')}/api/tags", timeout=5):
            return True
    except Exception:
        return False
