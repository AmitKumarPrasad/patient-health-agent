from __future__ import annotations

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.document import PatientDocument
from app.services.documents import get_storage_client
from app.services.document_ingestion import index_document
from app.config import settings


def main() -> None:
    client = get_storage_client()
    processed = 0
    with SessionLocal() as db:
        documents = db.scalars(select(PatientDocument).order_by(PatientDocument.created_at)).all()
        for document in documents:
            response = client.get_object(settings.minio_bucket, document.object_key)
            try:
                index_document(db, document, response.read())
                processed += 1
            finally:
                response.close()
                response.release_conn()
    print(f"Reindexed {processed} documents")


if __name__ == "__main__":
    main()
