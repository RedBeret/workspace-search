"""Tests for markdown chunking logic."""

import pytest
from workspace_search.indexer import chunk_markdown, _split_large_chunk


def test_no_headings_single_chunk():
    content = "This is a document with no headings.\n\nJust some paragraphs."
    chunks = chunk_markdown(content)
    assert len(chunks) == 1
    assert chunks[0]["heading"] == ""
    assert "no headings" in chunks[0]["content"]


def test_single_heading():
    content = "Preamble text.\n\n## Section One\n\nSection content here."
    chunks = chunk_markdown(content)
    # Should produce preamble chunk + section chunk
    headings = [c["heading"] for c in chunks]
    assert "Section One" in headings
    assert any(c["content"] for c in chunks if "Preamble" in c["content"])


def test_multiple_headings():
    content = """# Title

Intro paragraph.

## First Section

Content for first section.

## Second Section

Content for second section.

### Sub-section

Sub-section content.
"""
    chunks = chunk_markdown(content)
    headings = {c["heading"] for c in chunks}
    assert "First Section" in headings
    assert "Second Section" in headings
    assert "Sub-section" in headings


def test_empty_content():
    chunks = chunk_markdown("")
    assert chunks == [] or all(not c["content"].strip() for c in chunks)


def test_heading_only():
    content = "## Just a heading\n"
    chunks = chunk_markdown(content)
    # Should not crash; heading might produce one chunk
    assert isinstance(chunks, list)


def test_oversized_chunk_split():
    """Chunks over MAX_CHUNK_CHARS are split at paragraph breaks."""
    big_para = "Word " * 200  # ~1000 chars each
    content = "\n\n".join([big_para] * 10)  # ~10,000 chars
    chunks = _split_large_chunk(content, heading="Big Section")
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk["content"]) <= 4000 + 500  # some slack for paragraph boundaries


def test_chunk_preserves_heading():
    content = "## My Heading\n\nContent under this heading."
    chunks = chunk_markdown(content)
    # The section chunk should have the heading
    section_chunks = [c for c in chunks if c["heading"] == "My Heading"]
    assert len(section_chunks) >= 1


def test_no_empty_chunks():
    """Chunks with only whitespace are filtered."""
    content = "## Section\n\n   \n\n## Another\n\nContent."
    chunks = chunk_markdown(content)
    for chunk in chunks:
        assert chunk["content"].strip() != ""


def test_code_block_preserved():
    """Code blocks should not be split mid-block."""
    content = """## Example

Some intro text.

```python
def hello():
    return "world"
```

More text after code.
"""
    chunks = chunk_markdown(content)
    # The chunk containing the code block should be intact
    code_chunks = [c for c in chunks if "```python" in c["content"]]
    assert len(code_chunks) == 1
    assert "return" in code_chunks[0]["content"]


def test_three_hash_heading():
    content = "### Deep Section\n\nContent here."
    chunks = chunk_markdown(content)
    assert any(c["heading"] == "Deep Section" for c in chunks)


def test_preamble_before_first_heading():
    content = "This is a preamble.\n\n## Section\n\nSection content."
    chunks = chunk_markdown(content)
    preambles = [c for c in chunks if c["heading"] == "" and "preamble" in c["content"]]
    assert len(preambles) == 1
