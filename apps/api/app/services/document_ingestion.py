from __future__ import annotations

from io import BytesIO
import re

from pypdf import PdfReader
from langchain_openai import OpenAIEmbeddings

from app.config import settings
from app.models.document import PatientDocument
from app.models.document_chunk import PatientDocumentChunk

CHUNK_SIZE = 1200
CHUNK_OVERLAP = 150
MAX_INDEX_CHARS = 100_000


def extract_text(content: bytes, content_type: str) -> str:
    if content_type == "text/plain":
        return content.decode("utf-8", errors="replace")[:MAX_INDEX_CHARS]
    if content_type == "application/pdf":
        reader = PdfReader(BytesIO(content))
        pages = [(page.extract_text() or "") for page in reader.pages]
        return "\n\n".join(pages)[:MAX_INDEX_CHARS]
    return ""


def chunk_text(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(len(normalized), start + CHUNK_SIZE)
        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == len(normalized):
            break
        start = max(0, end - CHUNK_OVERLAP)
    return chunks


def build_embeddings(texts: list[str]) -> list[list[float] | None]:
    if not texts or not settings.openai_api_key:
        return [None for _ in texts]
    embeddings = OpenAIEmbeddings(
        model=settings.openai_embedding_model,
        api_key=settings.openai_api_key,
    )
    return embeddings.embed_documents(texts)


def index_document(db, document: PatientDocument, content: bytes) -> int:
    text = extract_text(content, document.content_type)
    chunks = chunk_text(text)
    if not chunks:
        return 0

    embeddings = build_embeddings(chunks)
    db.query(PatientDocumentChunk).filter(
        PatientDocumentChunk.document_id == document.id
    ).delete(synchronize_session=False)
    for index, (chunk, embedding) in enumerate(zip(chunks, embeddings, strict=True)):
        db.add(
            PatientDocumentChunk(
                document_id=document.id,
                patient_id=document.patient_id,
                chunk_index=index,
                content=chunk,
                embedding=embedding,
            )
        )
    db.commit()
    return len(chunks)
