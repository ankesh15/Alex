from typing import List, Dict, Any, Optional
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.config import settings


class ChunkingService:
    """
    Document text chunking service.
    Uses RecursiveCharacterTextSplitter while preserving source page metadata.
    """

    @classmethod
    def split_pages(
        cls,
        pages: List[Dict[str, Optional[Any]]],
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        c_size = chunk_size if chunk_size is not None else settings.CHUNK_SIZE
        c_overlap = chunk_overlap if chunk_overlap is not None else settings.CHUNK_OVERLAP

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=c_size,
            chunk_overlap=c_overlap,
            separators=["\n\n", "\n", " ", ""]
        )

        chunks: List[Dict[str, Any]] = []
        global_chunk_index = 0

        for page in pages:
            page_text = page.get("text", "") or ""
            page_num = page.get("page_number")

            if not page_text.strip():
                continue

            sub_chunks = splitter.split_text(page_text)
            for sub_text in sub_chunks:
                if sub_text and sub_text.strip():
                    chunks.append({
                        "chunk_index": global_chunk_index,
                        "content": sub_text.strip(),
                        "page_number": page_num
                    })
                    global_chunk_index += 1

        return chunks
