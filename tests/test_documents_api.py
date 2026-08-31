import io
import fitz
import docx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from app.core.db import Base
from app.models.document import Document  # noqa: F401
from app.api.main import app
from app.api.v1.endpoints.documents import get_db

# Configure shared in-memory SQLite for API tests across threads
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()


client = TestClient(app)


def test_upload_pdf_success():
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Sample PDF content for API test")
    pdf_bytes = doc.tobytes()
    doc.close()

    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("test_sample.pdf", pdf_bytes, "application/pdf")}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "test_sample.pdf"
    assert data["file_type"] == "pdf"
    assert data["status"] == "READY"
    assert "id" in data

    doc_id = data["id"]

    # Test GET Detail
    detail_res = client.get(f"/api/v1/documents/{doc_id}")
    assert detail_res.status_code == 200
    detail_data = detail_res.json()
    assert detail_data["id"] == doc_id
    assert detail_data["page_count"] == 1

    # Test GET List
    list_res = client.get("/api/v1/documents")
    assert list_res.status_code == 200
    assert list_res.json()["total"] >= 1

    # Test DELETE
    del_res = client.delete(f"/api/v1/documents/{doc_id}")
    assert del_res.status_code == 200
    assert del_res.json()["id"] == doc_id

    # Verify 404 after delete
    detail_404 = client.get(f"/api/v1/documents/{doc_id}")
    assert detail_404.status_code == 404


def test_upload_docx_success():
    doc = docx.Document()
    doc.add_paragraph("API testing paragraph for DOCX format.")
    stream = io.BytesIO()
    doc.save(stream)
    docx_bytes = stream.getvalue()

    mime_docx = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("test_sample.docx", docx_bytes, mime_docx)}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "test_sample.docx"
    assert data["file_type"] == "docx"
    assert data["status"] == "READY"

    # Cleanup
    doc_id = data["id"]
    client.delete(f"/api/v1/documents/{doc_id}")


def test_upload_txt_success():
    txt_bytes = b"Sample plain text content for API verification."
    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("notes.txt", txt_bytes, "text/plain")}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "notes.txt"
    assert data["file_type"] == "txt"
    assert data["status"] == "READY"

    # Cleanup
    doc_id = data["id"]
    client.delete(f"/api/v1/documents/{doc_id}")


def test_upload_unsupported_extension():
    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("image.png", b"fake png data", "image/png")}
    )
    assert response.status_code == 400
    assert "Unsupported file extension" in response.json()["detail"]


def test_upload_empty_file():
    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("empty.txt", b"", "text/plain")}
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"]


def test_upload_oversized_file():
    # 21 MB dummy buffer
    oversized_bytes = b"0" * (21 * 1024 * 1024)
    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("large.txt", oversized_bytes, "text/plain")}
    )
    assert response.status_code == 413
    assert "exceeds maximum limit" in response.json()["detail"]


def test_get_nonexistent_document():
    response = client.get("/api/v1/documents/non-existent-uuid")
    assert response.status_code == 404


def test_delete_nonexistent_document():
    response = client.delete("/api/v1/documents/non-existent-uuid")
    assert response.status_code == 404
