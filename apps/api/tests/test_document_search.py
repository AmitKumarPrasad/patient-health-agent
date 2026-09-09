from app.models.document_chunk import PatientDocumentChunk
from app.models.patient import Patient
from app.services.document_search import search_patient_document_chunks


def test_document_search_is_patient_scoped() -> None:
    class FakeScalarResult:
        def __init__(self, values):
            self.values = values

        def all(self):
            return self.values

    class FakeDB:
        def scalars(self, query):
            return FakeScalarResult(self.chunks)

        chunks = []

    patient_a = Patient(id=1, first_name="A", last_name="Patient")
    patient_b = Patient(id=2, first_name="B", last_name="Patient")
    chunk_a = PatientDocumentChunk(patient_id=patient_a.id, document_id="a", chunk_index=0, content="blood pressure 120", embedding=None)
    chunk_b = PatientDocumentChunk(patient_id=patient_b.id, document_id="b", chunk_index=0, content="blood pressure 180", embedding=None)

    db = FakeDB()
    db.chunks = [chunk_a]
    results = search_patient_document_chunks(db, patient_a, "blood pressure")

    assert len(results) == 1
    assert results[0]["content"] == "blood pressure 120"
    assert all(result["content"] != chunk_b.content for result in results)
