"""Unit tests for RAG ingest (chunking)."""
import pytest

from app.services.rag_ingest import chunk_text


def test_chunk_text_empty():
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_chunk_text_small():
    assert chunk_text("hello", chunk_size=10) == ["hello"]


def test_chunk_text_exact_chunk():
    out = chunk_text("abcdefghij", chunk_size=10, overlap=0)
    assert out == ["abcdefghij"]


def test_chunk_text_with_overlap():
    out = chunk_text("abcdefghijklmnop", chunk_size=5, overlap=2)
    assert len(out) >= 2
    assert "abcde" in out[0]
    # overlap 2: next starts at index 3
    assert out[0][-2:] == "de" or out[1][:2] == "de"


def test_chunk_text_chunk_size_zero():
    assert chunk_text("hello", chunk_size=0) == []
