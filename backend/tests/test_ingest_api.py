"""Tests for document ingestion API (POST /api/ingest-doc)."""
from io import BytesIO
from unittest.mock import patch

import pytest


def test_ingest_doc_requires_pdf(client):
    resp = client.post(
        "/api/ingest-doc",
        files={"file": ("report.txt", BytesIO(b"not a pdf"), "text/plain")},
    )
    assert resp.status_code == 400
    assert "PDF" in resp.json()["detail"]


def test_ingest_doc_rejects_empty_extracted_text(client):
    with (
        patch("app.api.ingest.extract_text_from_pdf", return_value="   "),
        patch("app.api.ingest.ingest_document_to_rag"),
    ):
        resp = client.post(
            "/api/ingest-doc",
            files={"file": ("doc.pdf", BytesIO(b"%PDF-1.4 minimal"), "application/pdf")},
        )
    assert resp.status_code == 400
    assert "No text" in resp.json()["detail"]


def test_ingest_doc_success(client):
    with (
        patch("app.api.ingest.extract_text_from_pdf", return_value="Some report content."),
        patch("app.api.ingest.ingest_document_to_rag", return_value=3),
    ):
        resp = client.post(
            "/api/ingest-doc",
            files={"file": ("doc.pdf", BytesIO(b"%PDF-1.4 x"), "application/pdf")},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ingested"] == 3
    assert data["source"] == "doc.pdf"
