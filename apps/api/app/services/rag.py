from __future__ import annotations

from langchain_openai import OpenAIEmbeddings
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.document import PatientDocument
from app.models.document_chunk import PatientDocumentChunk
from app.models.patient import Patient

MAX_RESULTS = 5


def _embed_query(query_text: str) -> list[float] | None:
    if not settings.openai_api_key or not query_text:
        return None
    embeddings = OpenAIEmbeddings(
        model=settings.openai_embedding_model,
        api_key=settings.openai_api_key,
    )
    return embeddings.embed_query(query_text)


def _lexical_retrieval(
    db: Session,
    patient: Patient,
    query_text: str,
    *,
    limit: int,
) -> list[dict[str, str | float]]:
    terms = [term for term in query_text.lower().split() if len(term) > 2]
    if not terms:
        return []

    rows = db.execute(
        select(PatientDocumentChunk, PatientDocument.original_filename)
        .join(PatientDocument, PatientDocument.id == PatientDocumentChunk.document_id)
        .where(PatientDocumentChunk.patient_id == patient.id)
    ).all()

    scored: list[tuple[float, PatientDocumentChunk, str]] = []
    for chunk, document_name in rows:
        lowered = chunk.content.lower()
        score = float(sum(lowered.count(term) for term in terms))
        if score > 0:
            scored.append((score, chunk, document_name))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [_result(chunk, document_name, score) for score, chunk, document_name in scored[:limit]]


def _result(chunk: PatientDocumentChunk, document_name: str, score: float) -> dict[str, str | float]:
    return {
        "chunk_id": str(chunk.id),
        "document_id": str(chunk.document_id),
        "document_name": document_name,
        "chunk_index": chunk.chunk_index,
        "content": chunk.content,
        "score": round(max(0.0, min(1.0, score)), 6),
    }


def retrieve_patient_chunks(
    db: Session,
    patient: Patient,
    query_text: str,
    *,
    limit: int = MAX_RESULTS,
) -> list[dict[str, str | float]]:
    """Retrieve only the authenticated patient's document chunks by semantic similarity."""
    safe_limit = max(1, min(limit, MAX_RESULTS))
    query_text = query_text.strip()
    if not query_text:
        return []

    query_embedding = _embed_query(query_text)
    if query_embedding is None:
        return _lexical_retrieval(db, patient, query_text, limit=safe_limit)

    distance = PatientDocumentChunk.embedding.cosine_distance(query_embedding)
    rows = db.execute(
        select(
            PatientDocumentChunk,
            PatientDocument.original_filename,
            distance.label("distance"),
        )
        .join(PatientDocument, PatientDocument.id == PatientDocumentChunk.document_id)
        .where(
            PatientDocumentChunk.patient_id == patient.id,
            PatientDocumentChunk.embedding.is_not(None),
        )
        .order_by(distance)
        .limit(safe_limit)
    ).all()

    return [
        _result(chunk, document_name, 1.0 - float(distance_value))
        for chunk, document_name, distance_value in rows
        if distance_value is not None
    ]
