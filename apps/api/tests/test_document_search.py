from app.models.document import PatientDocument
from app.models.document_chunk import PatientDocumentChunk
from app.models.patient import Patient
from app.services.document_search import search_patient_document_chunks


def _fake_db(chunks):
    class FakeScalarResult:
        def __init__(self, values):
            self.values = values

        def all(self):
            return self.values

    class FakeDB:
        def scalars(self, query):
            return FakeScalarResult(self.chunks)

    db = FakeDB()
    db.chunks = chunks
    return db


def test_document_search_is_patient_scoped() -> None:
    patient_a = Patient(id=1, first_name="A", last_name="Patient")
    patient_b = Patient(id=2, first_name="B", last_name="Patient")
    chunk_a = PatientDocumentChunk(patient_id=patient_a.id, document_id="a", chunk_index=0, content="blood pressure 120", embedding=None)
    chunk_b = PatientDocumentChunk(patient_id=patient_b.id, document_id="b", chunk_index=0, content="blood pressure 180", embedding=None)

    db = _fake_db([chunk_a])
    results = search_patient_document_chunks(db, patient_a, "blood pressure")

    assert len(results) == 1
    assert results[0]["content"] == "blood pressure 120"
    assert all(result["content"] != chunk_b.content for result in results)


def test_document_search_does_not_return_zero_match_chunks() -> None:
    patient = Patient(id=1, first_name="A", last_name="Patient")
    chunk = PatientDocumentChunk(
        patient_id=patient.id,
        document_id="unrelated",
        chunk_index=0,
        content="medication refill instructions",
        embedding=None,
    )

    results = search_patient_document_chunks(_fake_db([chunk]), patient, "cardiology")

    assert results == []


def test_document_search_is_deterministic_for_equal_scores() -> None:
    patient = Patient(id=1, first_name="A", last_name="Patient")
    first = PatientDocumentChunk(
        patient_id=patient.id,
        document_id="b-document",
        chunk_index=1,
        content="blood pressure",
        embedding=None,
    )
    second = PatientDocumentChunk(
        patient_id=patient.id,
        document_id="a-document",
        chunk_index=0,
        content="blood pressure",
        embedding=None,
    )

    results = search_patient_document_chunks(_fake_db([first, second]), patient, "blood pressure")

    assert [result["document_id"] for result in results] == ["a-document", "b-document"]


def test_document_search_returns_source_provenance() -> None:
    patient = Patient(id=1, first_name="A", last_name="Patient")
    document = PatientDocument(
        id="doc-1",
        patient_id=patient.id,
        object_key="patients/doc-1/report.pdf",
        original_filename="blood-report.pdf",
        content_type="application/pdf",
        size_bytes=100,
        category="lab",
    )
    chunk = PatientDocumentChunk(
        patient_id=patient.id,
        document_id=document.id,
        chunk_index=2,
        content="hemoglobin 13.2",
        embedding=None,
    )
    chunk.document = document

    results = search_patient_document_chunks(_fake_db([chunk]), patient, "hemoglobin")

    assert results[0]["document_id"] == "doc-1"
    assert results[0]["document_name"] == "blood-report.pdf"
    assert results[0]["document_category"] == "lab"
    assert results[0]["chunk_index"] == 2
