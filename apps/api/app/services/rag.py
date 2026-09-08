from __future__ import annotations

import math

from langchain_openai import OpenAIEmbeddings
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.document_chunk import PatientDocumentChunk
from app.models.patient import Patient

MAX_RESULTS = 5


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    numerator = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if not left_norm or not right_norm:
        return 0.0
    return numerator / (left_norm * right_norm)


def retrieve_patient_chunks(
    db: Session,
    patient: Patient,
    query_text: str,
    *,
    limit: int = MAX_RESULTS,
) -> list[dict[str, str | float]]:
    chunks = db.scalars(
        select(PatientDocumentChunk).where(PatientDocumentChunk.patient_id == patient.id)
    ).all()
    if not chunks:
        return []

    query_embedding: list[float] | None = None
    if settings.openai_api_key:
        query_embedding = OpenAIEmbeddings(
            model=settings.openai_embedding_model,
            api_key=settings.openai_api_key,
        ).embed_query(query_text)

    scored: list[tuple[float, PatientDocumentChunk]] = []
    terms = [term for term in query_text.lower().split() if len(term) > 2]
    for chunk in chunks:
        if query_embedding and chunk.embedding:
            score = _cosine_similarity(query_embedding, [float(x) for x in chunk.embedding])
        else:
            lowered = chunk.content.lower()
            score = sum(lowered.count(term) for term in terms)
        if score > 0:
            scored.append((float(score), chunk))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [
        {
            "chunk_id": str(chunk.id),
            "document_id": str(chunk.document_id),
            "content": chunk.content,
            "score": score,
        }
        for score, chunk in scored[:limit]
    ]
