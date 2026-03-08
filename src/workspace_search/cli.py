"""Command-line interface for workspace-search."""

import asyncio
import logging
import os
import sys
import time
from pathlib import Path

import click

from .indexer import index_directory
from .ollama import DEFAULT_BASE_URL, DEFAULT_MODEL, check_ollama
from .search import search
from .store import clear_index, get_stats, list_documents


# ANSI color helpers
def _green(s: str) -> str:
    return f"\033[32m{s}\033[0m" if sys.stdout.isatty() else s


def _yellow(s: str) -> str:
    return f"\033[33m{s}\033[0m" if sys.stdout.isatty() else s


def _dim(s: str) -> str:
    return f"\033[2m{s}\033[0m" if sys.stdout.isatty() else s


def _bold(s: str) -> str:
    return f"\033[1m{s}\033[0m" if sys.stdout.isatty() else s


def _score_color(pct: int) -> str:
    if pct >= 85:
        return _green(f"{pct}%")
    elif pct >= 70:
        return _yellow(f"{pct}%")
    else:
        return _dim(f"{pct}%")


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging.")
@click.option("--model", default=DEFAULT_MODEL, show_default=True, help="Ollama embedding model.")
@click.option("--ollama-url", default=DEFAULT_BASE_URL, show_default=True, help="Ollama server URL.")
@click.pass_context
def cli(ctx: click.Context, verbose: bool, model: str, ollama_url: str) -> None:
    """workspace-search — local semantic search for your markdown files."""
    if verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(name)s: %(message)s")
    ctx.ensure_object(dict)
    ctx.obj["model"] = model
    ctx.obj["ollama_url"] = ollama_url


@cli.command()
@click.argument("path", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--exclude", "-e", multiple=True, help="Regex patterns to exclude (repeatable).")
@click.pass_context
def index(ctx: click.Context, path: Path, exclude: tuple[str, ...]) -> None:
    """Index a directory of markdown files."""
    model = ctx.obj["model"]
    ollama_url = ctx.obj["ollama_url"]

    if not check_ollama(ollama_url):
        click.echo(f"Error: Ollama is not reachable at {ollama_url}", err=True)
        click.echo("Start it with: ollama serve", err=True)
        sys.exit(1)

    click.echo(f"Indexing {_bold(str(path))} with model {_bold(model)}...")
    t0 = time.monotonic()

    stats = asyncio.run(
        index_directory(
            path,
            exclude=list(exclude) or None,
            model=model,
            base_url=ollama_url,
        )
    )

    elapsed = time.monotonic() - t0
    click.echo(
        f"\n{_green('Done')} — {stats['indexed']} indexed, "
        f"{stats['skipped']} skipped, {stats['errors']} errors "
        f"in {elapsed:.1f}s"
    )


@cli.command()
@click.argument("text", nargs=-1, required=True)
@click.option("--top-k", "-k", default=5, show_default=True, help="Number of results.")
@click.pass_context
def query(ctx: click.Context, text: tuple[str, ...], top_k: int) -> None:
    """Search indexed documents with a natural language query."""
    query_text = " ".join(text)
    model = ctx.obj["model"]
    ollama_url = ctx.obj["ollama_url"]

    if not check_ollama(ollama_url):
        click.echo(f"Error: Ollama is not reachable at {ollama_url}", err=True)
        sys.exit(1)

    results = search(query_text, top_k=top_k, model=model, base_url=ollama_url)

    if not results:
        click.echo("No results. Index some documents first with: ws-search index <path>")
        return

    click.echo(f'\nResults for: {_bold(repr(query_text))}\n')
    for i, result in enumerate(results, 1):
        path_rel = result.path
        score_str = _score_color(result.score_pct)

        heading_str = f"  [{result.heading}]" if result.heading else ""
        click.echo(f"  {i}. {_bold(path_rel)}{heading_str}  {score_str}")
        click.echo(f"     {_dim(result.content_preview)}")
        click.echo()


@cli.command()
def stats() -> None:
    """Show index statistics."""
    s = get_stats()
    size_mb = s["db_size_bytes"] / 1_048_576
    click.echo(f"Documents : {s['documents']}")
    click.echo(f"Chunks    : {s['chunks']}")
    click.echo(f"DB size   : {size_mb:.2f} MB")
    click.echo(f"DB path   : {s['db_path']}")


@cli.command("list")
def list_docs() -> None:
    """List all indexed documents."""
    docs = list_documents()
    if not docs:
        click.echo("No documents indexed yet.")
        return
    for doc in docs:
        click.echo(f"  {doc['path']}  ({doc['chunk_count']} chunks, {doc['indexed_at'][:10]})")


@cli.command()
@click.confirmation_option(prompt="Delete the entire index?")
def clear() -> None:
    """Delete the index (all documents and chunks)."""
    clear_index()
    click.echo("Index cleared.")


@cli.command()
@click.argument("path", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--interval", default=5, show_default=True, help="Poll interval in seconds.")
@click.option("--exclude", "-e", multiple=True, help="Regex patterns to exclude.")
@click.pass_context
def watch(ctx: click.Context, path: Path, interval: int, exclude: tuple[str, ...]) -> None:
    """Watch a directory and re-index changed markdown files."""
    model = ctx.obj["model"]
    ollama_url = ctx.obj["ollama_url"]

    if not check_ollama(ollama_url):
        click.echo(f"Error: Ollama is not reachable at {ollama_url}", err=True)
        sys.exit(1)

    click.echo(f"Watching {_bold(str(path))} (interval: {interval}s) — Ctrl+C to stop")

    # Track file mtimes to detect changes
    seen_mtimes: dict[str, float] = {}

    try:
        while True:
            changed = False
            for md_file in sorted(path.rglob("*.md")):
                try:
                    mtime = md_file.stat().st_mtime
                except OSError:
                    continue
                key = str(md_file)
                if seen_mtimes.get(key) != mtime:
                    seen_mtimes[key] = mtime
                    changed = True

            if changed:
                click.echo(f"Changes detected — re-indexing...")
                asyncio.run(
                    index_directory(
                        path,
                        exclude=list(exclude) or None,
                        model=model,
                        base_url=ollama_url,
                    )
                )

            time.sleep(interval)

    except KeyboardInterrupt:
        click.echo("\nStopped.")
