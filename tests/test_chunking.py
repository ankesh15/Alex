from app.services.chunking_service import ChunkingService


def test_chunking_normal_text():
    pages = [
        {"text": "FastAPI is a modern, fast web framework for building APIs with Python.", "page_number": 1}
    ]
    chunks = ChunkingService.split_pages(pages, chunk_size=100, chunk_overlap=20)
    assert len(chunks) == 1
    assert chunks[0]["chunk_index"] == 0
    assert chunks[0]["page_number"] == 1
    assert "FastAPI" in chunks[0]["content"]


def test_chunking_large_text_multi_chunks():
    paragraph = "Machine learning and artificial intelligence are transforming modern research. " * 20
    pages = [{"text": paragraph, "page_number": 2}]

    chunks = ChunkingService.split_pages(pages, chunk_size=200, chunk_overlap=30)
    assert len(chunks) > 1
    for idx, c in enumerate(chunks):
        assert c["chunk_index"] == idx
        assert c["page_number"] == 2
        assert len(c["content"]) <= 200 + 50  # Allowance for word boundary splits


def test_chunking_preserves_page_numbers_for_pdf():
    pages = [
        {"text": "Content of page 1 about quantum computing.", "page_number": 1},
        {"text": "Content of page 2 about neural networks.", "page_number": 2}
    ]
    chunks = ChunkingService.split_pages(pages, chunk_size=100, chunk_overlap=10)
    assert len(chunks) == 2
    assert chunks[0]["page_number"] == 1
    assert chunks[1]["page_number"] == 2


def test_chunking_docx_txt_none_page_number():
    pages = [
        {"text": "Plain text document line one.\nPlain text document line two.", "page_number": None}
    ]
    chunks = ChunkingService.split_pages(pages, chunk_size=100, chunk_overlap=10)
    assert len(chunks) >= 1
    assert chunks[0]["page_number"] is None


def test_chunking_empty_or_whitespace_text():
    pages = [
        {"text": "   \n\n\t  ", "page_number": 1},
        {"text": "", "page_number": 2}
    ]
    chunks = ChunkingService.split_pages(pages)
    assert len(chunks) == 0
