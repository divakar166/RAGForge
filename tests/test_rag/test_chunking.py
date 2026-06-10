"""Tests for the chunking module."""

from app.rag.chunking.recursive import RecursiveChunking


def test_recursive_chunking_splits_by_paragraphs():
    chunker = RecursiveChunking(chunk_size=100, overlap=0)
    text = "First paragraph content here.\n\nSecond paragraph content here.\n\nThird paragraph."
    chunks = chunker.chunk(text)
    assert len(chunks) >= 1
    for c in chunks:
        assert c.content
        assert c.strategy == "recursive"


def test_recursive_chunking_respects_headings():
    chunker = RecursiveChunking(chunk_size=500, overlap=0)
    text = "# Introduction\n\nHello world.\n\n# Methods\n\nWe did stuff.\n\n# Results\n\nIt worked."
    chunks = chunker.chunk(text, doc_title="Test Doc")
    assert len(chunks) == 3
    for c in chunks:
        assert "[Test Doc]" in c.content


def test_recursive_chunking_empty_text():
    chunker = RecursiveChunking(chunk_size=100, overlap=0)
    chunks = chunker.chunk("")
    assert chunks == []
