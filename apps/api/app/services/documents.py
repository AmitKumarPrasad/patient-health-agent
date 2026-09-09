from __future__ import annotations

import hashlib
import re
import zlib
from io import BytesIO
from pathlib import Path
from uuid import UUID, uuid4

from minio import Minio
from pypdf import PdfReader
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.document import PatientDocument
from app.models.patient import Patient
from app.services.antivirus import scan_content
from app.services.document_ingestion import index_document

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "text/plain",
}
MAX_DOCUMENT_BYTES = 10 * 1024 * 1024


def _safe_filename(filename: str) -> str:
    name = Path(filename or "document").name
    name = re.sub(r"[^A-Za-z0-9._ -]", "_", name).strip(" .")
    return name[:255] or "document"


def _validate_content_signature(content_type: str, content: bytes) -> None:
    """Reject binary uploads whose bytes do not match their declared media type."""
    signatures = {
        "application/pdf": content.startswith(b"%PDF-"),
        "image/png": content.startswith(b"\x89PNG\r\n\x1a\n"),
        "image/jpeg": content.startswith(b"\xff\xd8\xff"),
        "text/plain": True,
    }
    if content_type not in signatures or not signatures[content_type]:
        raise ValueError("Document content does not match its declared type")


def _validate_document_structure(content_type: str, content: bytes) -> None:
    """Validate enough structure to reject signature-only polyglot or truncated files."""
    try:
        if content_type == "application/pdf":
            reader = PdfReader(BytesIO(content))
            if not reader.pages:
                raise ValueError("PDF contains no pages")
        elif content_type == "image/png":
            _validate_png_structure(content)
        elif content_type == "image/jpeg":
            _validate_jpeg_structure(content)
    except ValueError:
        raise
    except Exception as exc:  # noqa: BLE001 - normalize parser failures at the upload boundary.
        raise ValueError("Document structure is invalid") from exc


def _validate_png_structure(content: bytes) -> None:
    if len(content) < 33 or content[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("PNG is structurally invalid")

    offset = 8
    saw_ihdr = False
    saw_iend = False
    while offset < len(content):
        if offset + 12 > len(content):
            raise ValueError("PNG is structurally invalid")
        length = int.from_bytes(content[offset : offset + 4], "big")
        chunk_end = offset + 12 + length
        if chunk_end > len(content):
            raise ValueError("PNG is structurally invalid")
        chunk_type = content[offset + 4 : offset + 8]
        chunk_data = content[offset + 8 : offset + 8 + length]
        stored_crc = int.from_bytes(content[offset + 8 + length : chunk_end], "big")
        expected_crc = zlib.crc32(chunk_type + chunk_data) & 0xFFFFFFFF
        if stored_crc != expected_crc:
            raise ValueError("PNG is structurally invalid")

        if not saw_ihdr:
            if chunk_type != b"IHDR" or length != 13:
                raise ValueError("PNG is structurally invalid")
            width = int.from_bytes(chunk_data[:4], "big")
            height = int.from_bytes(chunk_data[4:8], "big")
            if width == 0 or height == 0:
                raise ValueError("PNG has invalid dimensions")
            saw_ihdr = True
        elif chunk_type == b"IHDR":
            raise ValueError("PNG is structurally invalid")

        offset = chunk_end
        if chunk_type == b"IEND":
            if length != 0 or offset != len(content):
                raise ValueError("PNG is structurally invalid")
            saw_iend = True
            break

    if not saw_ihdr or not saw_iend:
        raise ValueError("PNG is structurally invalid")


def _validate_jpeg_structure(content: bytes) -> None:
    if len(content) < 4 or not content.startswith(b"\xff\xd8") or not content.endswith(b"\xff\xd9"):
        raise ValueError("JPEG is structurally invalid")

    offset = 2
    saw_frame = False
    while offset < len(content) - 2:
        if content[offset] != 0xFF:
            offset += 1
            continue
        while offset < len(content) and content[offset] == 0xFF:
            offset += 1
        if offset >= len(content):
            break

        marker = content[offset]
        offset += 1
        if marker == 0xD9:
            break
        if marker in {0xD8, 0x01} or 0xD0 <= marker <= 0xD7:
            continue
        if offset + 2 > len(content):
            raise ValueError("JPEG is structurally invalid")

        segment_length = int.from_bytes(content[offset : offset + 2], "big")
        if segment_length < 2 or offset + segment_length > len(content):
            raise ValueError("JPEG is structurally invalid")

        if 0xC0 <= marker <= 0xC3 or 0xC5 <= marker <= 0xC7 or 0xC9 <= marker <= 0xCB or 0xCD <= marker <= 0xCF:
            if segment_length < 8:
                raise ValueError("JPEG is structurally invalid")
            height = int.from_bytes(content[offset + 3 : offset + 5], "big")
            width = int.from_bytes(content[offset + 5 : offset + 7], "big")
            if width == 0 or height == 0:
                raise ValueError("JPEG has invalid dimensions")
            saw_frame = True

        offset += segment_length

    if not saw_frame:
        raise ValueError("JPEG is structurally invalid")


def get_storage_client() -> Minio:
    endpoint = settings.minio_endpoint.replace("http://", "").replace("https://", "")
    return Minio(
        endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


def ensure_bucket(client: Minio) -> None:
    if not client.bucket_exists(settings.minio_bucket):
        client.make_bucket(settings.minio_bucket)


def list_documents(db: Session, patient: Patient) -> list[PatientDocument]:
    return db.scalars(
        select(PatientDocument)
        .where(PatientDocument.patient_id == patient.id)
        .order_by(PatientDocument.created_at.desc())
    ).all()


def upload_document(
    db: Session,
    patient: Patient,
    *,
    filename: str,
    content_type: str,
    content: bytes,
    category: str | None,
    description: str | None,
) -> PatientDocument:
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise ValueError("Unsupported document type")
    if not content:
        raise ValueError("Document is empty")
    if len(content) > MAX_DOCUMENT_BYTES:
        raise ValueError("Document exceeds the 10 MB limit")
    _validate_content_signature(content_type, content)
    _validate_document_structure(content_type, content)
    scan_content(content)

    sha256 = hashlib.sha256(content).hexdigest()
    client = get_storage_client()
    ensure_bucket(client)

    safe_name = _safe_filename(filename)
    document = PatientDocument(
        patient_id=patient.id,
        object_key=f"patients/{patient.id}/{uuid4()}/{safe_name}",
        original_filename=safe_name,
        content_type=content_type,
        size_bytes=len(content),
        sha256=sha256,
        category=category,
        description=description,
    )
    client.put_object(
        settings.minio_bucket,
        document.object_key,
        BytesIO(content),
        length=len(content),
        content_type=content_type,
    )
    db.add(document)
    try:
        db.commit()
    except Exception:
        db.rollback()
        try:
            client.remove_object(settings.minio_bucket, document.object_key)
        except Exception:
            pass
        raise
    db.refresh(document)

    try:
        index_document(db, document, content)
    except Exception:  # noqa: BLE001 - upload remains available if AI indexing is unavailable.
        db.rollback()
    return document


def get_document(db: Session, patient: Patient, document_id: UUID) -> PatientDocument:
    document = db.scalar(
        select(PatientDocument).where(
            PatientDocument.id == document_id,
            PatientDocument.patient_id == patient.id,
        )
    )
    if document is None:
        raise LookupError("Document not found")
    return document


def download_document(db: Session, patient: Patient, document_id: UUID) -> tuple[PatientDocument, bytes]:
    document = get_document(db, patient, document_id)
    client = get_storage_client()
    try:
        response = client.get_object(settings.minio_bucket, document.object_key)
        try:
            content = response.read()
        finally:
            response.close()
            response.release_conn()
    except Exception as exc:  # noqa: BLE001 - normalize storage errors at service boundary.
        raise RuntimeError("Unable to read document from object storage") from exc

    if document.sha256 is not None and hashlib.sha256(content).hexdigest() != document.sha256:
        raise RuntimeError("Stored document integrity check failed")
    return document, content


def delete_document(db: Session, patient: Patient, document_id: UUID) -> None:
    document = get_document(db, patient, document_id)
    client = get_storage_client()
    try:
        response = client.get_object(settings.minio_bucket, document.object_key)
        try:
            content = response.read()
        finally:
            response.close()
            response.release_conn()
    except Exception as exc:  # noqa: BLE001 - normalize storage errors at service boundary.
        raise RuntimeError("Unable to read document before deletion") from exc

    try:
        client.remove_object(settings.minio_bucket, document.object_key)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("Unable to delete document from object storage") from exc

    db.delete(document)
    try:
        db.commit()
    except Exception:
        db.rollback()
        try:
            client.put_object(
                settings.minio_bucket,
                document.object_key,
                BytesIO(content),
                length=len(content),
                content_type=document.content_type,
            )
        except Exception as restore_exc:  # noqa: BLE001 - preserve the original DB failure.
            raise RuntimeError("Unable to restore document after database deletion failure") from restore_exc
        raise
