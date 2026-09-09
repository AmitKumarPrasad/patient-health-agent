from __future__ import annotations

import math
from typing import Any

from langchain_openai import OpenAIEmbeddings
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.models.document_chunk import PatientDocumentChunk
from app.models.patient import Patient

MAX_RESULTS = 5
MIN_RELEVANCE_SCORE = 0.01


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        return -1.0
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return -1.0
    return dot / (left_norm * right_norm)


def _query_embedding(query: str) -> list[float] | None:
    if not settings.openai_api_key:
        return None
    embeddings = OpenAIEmbeddings(
        model=settings.openai_embedding_model,
        api_key=settings.openai_api_key,
    )
    return embeddings.embed_query(query)


def search_patient_document_chunks(
    db: Session,
    patient: Patient,
    query: str,
    *,
    limit: int = MAX_RESULTS,
) -> list[dict[str, Any]]:
    """Search relevant indexed chunks for the authenticated patient with source metadata."""
    normalized_query = query.strip()
    if not normalized_query:
        return []
    limit = max(1, min(limit, MAX_RESULTS))

    chunks = db.scalars(
        select(PatientDocumentChunk)
        .options(joinedload(PatientDocumentChunk.document))
        .where(PatientDocumentChunk.patient_id == patient.id)
    ).all()
    if not chunks:
        return []

    query_vector = _query_embedding(normalized_query)
    scored: list[tuple[float, PatientDocumentChunk]] = []
    query_terms = {term.lower() for term in normalized_query.split() if term}

    for chunk in chunks:
        score = -1.0
        if query_vector is not None and chunk.embedding:
            score = _cosine_similarity(query_vector, list(chunk.embedding))
        if score < 0:
            content_lower = chunk.content.lower()
            matched = sum(1 for term in query_terms if term in content_lower)
            score = matched / max(1, len(query_terms))
        if score >= MIN_RELEVANCE_SCORE:
            scored.append((score, chunk))

    scored.sort(key=lambda item: (-item[0], item[1].chunk_index, str(item[1].document_id)))
    results: list[dict[str, Any]] = []
    for score, chunk in scored[:limit]:
        document = chunk.document
        results.append(
            {
                "document_id": str(chunk.document_id),
                "document_name": document.original_filename if document else None,
                "document_category": document.category if document else None,
                "chunk_index": chunk.chunk_index,
                "content": chunk.content,
                "score": round(score, 4),
            }
        )
    return results
